"""Frozen GFS archive acquisition and explicit IMD rainfall-window integration."""
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import numpy as np
import pandas as pd
from src.ingestion.forecast_schema import ROOT, read_json, file_hash, immutable_json, digest

CONFIG = ROOT/'config/nwp_experiment.json'
REALTIME_PAGE = 'https://imdpune.gov.in/cmpg/Realtimedata/Rainfall/Rain_Download.html'
REALTIME_ENDPOINT = 'https://imdpune.gov.in/cmpg/Realtimedata/Rainfall/rain.php'


def verify_daily_receipt(info, day):
    day = pd.Timestamp(day)
    headers = {k.lower():v for k,v in info['response_headers'].items()}
    expected = day.strftime('rain_ind0.25_%y_%m_%d.grd')
    if expected not in headers.get('content-disposition','') or info['date'] != day.strftime('%Y-%m-%d'):
        raise ValueError('IMD response date does not match requested observation date')


def experiment_context():
    config = read_json(CONFIG)
    meta = read_json(ROOT/f'data/research/manifests/{config["historical_dataset"]}.json')
    version = 'gfs-imd-' + digest([config, meta['cells']])[:20]
    return config, meta, version


def initialization_dates(config, fresh=False):
    if fresh:
        return pd.date_range(config['fresh_init_start'], config['fresh_init_end'], freq=f'{config["fresh_init_stride_days"]}D')
    years = config['train_years'] + config['calibration_years'] + config['selection_years']
    return pd.DatetimeIndex([d for year in years for d in pd.date_range(
        f'{year}-{config["historical_init_month_day_start"]}', f'{year}-{config["historical_init_month_day_end"]}',
        freq=f'{config["historical_init_stride_days"]}D')])


def integrate_window(lead_hours, rate, start, end):
    """Rate at step t covers (previous_step, t]; require exact complete coverage."""
    hours = np.asarray(lead_hours, dtype=float)
    rate = np.asarray(rate, dtype=float)
    if hours.ndim != 1 or len(hours) != len(rate) or len(hours) < 2 or np.any(np.diff(hours) <= 0):
        raise ValueError('Invalid forecast lead axis')
    if np.any(np.diff(hours) != np.where(hours[1:] <= 120, 1, 3)):
        raise ValueError('Missing native GFS forecast step')
    if start not in hours or end not in hours or end <= start:
        raise ValueError('Window endpoints must be native forecast steps')
    indices = np.flatnonzero((hours > start) & (hours <= end))
    widths = hours[indices] - hours[indices-1]
    if widths.sum() != end-start:
        raise ValueError('Incomplete accumulation window')
    values = rate[indices]
    if np.any(values < 0):
        raise ValueError('Negative forecast precipitation rate')
    return np.sum(values * (widths * 3600).reshape((-1,) + (1,)*(rate.ndim-1)), axis=0)


def decode_daily(data):
    if len(data) != 129*135*4:
        raise ValueError(f'Invalid IMD daily binary length: {len(data)}')
    valid = []
    for endian in ('<f4', '>f4'):
        a = np.frombuffer(data, dtype=endian).reshape(129, 135)
        missing = a == -999
        good = np.isfinite(a) & (a >= 0) & (a <= 5000)
        if (missing | good).all() and missing.mean() > .01 and good.mean() > .1 and np.max(a[good]) > 1:
            result = a.astype(np.float32); result[missing] = np.nan; valid.append(result)
    if len(valid) != 1: raise ValueError('Invalid/ambiguous daily rainfall grid')
    return valid[0]


def acquire_daily(day, root=ROOT):
    day = pd.Timestamp(day)
    key = day.strftime('%Y-%m-%d')
    directory = root/'data/research/raw/imd-realtime'
    directory.mkdir(parents=True, exist_ok=True)
    path, manifest = directory/f'{key}.grd', directory/f'{key}.json'
    if path.exists():
        if not manifest.exists() or file_hash(path) != read_json(manifest)['sha256']:
            raise ValueError('Daily observation checksum mismatch')
        verify_daily_receipt(read_json(manifest),day)
        return path
    request = Request(REALTIME_ENDPOINT, data=urlencode({'rain':day.strftime('%d%m%Y')}).encode(),
                      headers={'Referer':REALTIME_PAGE,'User-Agent':'Maharashtra-rainfall-research/2.0'})
    with urlopen(request, timeout=60) as response:
        data = response.read(100_001)
        headers = dict(response.headers)
    decode_daily(data)
    info = dict(date=key, url=REALTIME_ENDPOINT, request_form={'rain':day.strftime('%d%m%Y')},
                source_page=REALTIME_PAGE, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
                downloaded_at=datetime.now(timezone.utc).isoformat(), response_headers=headers,
                product='IMD real-time 0.25 degree gauge rainfall; provisional, distinct from finalized annual analysis')
    verify_daily_receipt(info,day)
    with path.open('xb') as f: f.write(data)
    immutable_json(manifest, info)
    return path


def open_gfs(config):
    import icechunk
    import xarray as xr
    repo = icechunk.Repository.open(icechunk.http_storage(config['gfs_asset_url']))
    session = repo.readonly_session(snapshot_id=config['gfs_snapshot_id'])
    ds = xr.open_zarr(session.store, chunks=None, consolidated=False)
    expected = {'precipitation_surface':'kg m-2 s-1', 'precipitable_water_atmosphere':'kg m-2', 'relative_humidity_2m':'percent'}
    for name, units in expected.items():
        if ds[name].attrs.get('units') != units: raise ValueError(f'Unexpected units for {name}')
    if 'previous forecast step' not in ds.precipitation_surface.attrs.get('comment', ''):
        raise ValueError('Unverified precipitation accumulation semantics')
    return ds


def acquire_gfs_run(ds, day, config, cells, directory):
    day = pd.Timestamp(day)
    key = day.strftime('%Y%m%dT00')
    path, manifest = directory/f'{key}.npz', directory/f'{key}.json'
    if path.exists():
        info = read_json(manifest)
        if info['sha256'] != file_hash(path) or info['snapshot_id'] != config['gfs_snapshot_id']:
            raise ValueError('GFS subset checksum/snapshot mismatch')
        return path
    start = time.monotonic()
    last = config['first_window_start_hour'] + 24*max(config['lead_days'])
    subset = ds[config['variables']].sel(init_time=day,
        latitude=slice(max(c['lat'] for c in cells), min(c['lat'] for c in cells)),
        longitude=slice(min(c['lon'] for c in cells), max(c['lon'] for c in cells)),
        lead_time=slice(np.timedelta64(0,'h'), np.timedelta64(last,'h'))).load()
    yi = [int(np.flatnonzero(subset.latitude.values == c['lat'])[0]) for c in cells]
    xi = [int(np.flatnonzero(subset.longitude.values == c['lon'])[0]) for c in cells]
    hours = (subset.lead_time.values / np.timedelta64(1, 'h')).astype(int)
    payload = {name:subset[name].transpose('lead_time','latitude','longitude').values[:, yi, xi] for name in config['variables']}
    directory.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, lead_hours=hours, **payload)
    info = dict(initialization_time=day.isoformat()+'Z', snapshot_id=config['gfs_snapshot_id'],
                asset_url=config['gfs_asset_url'], sha256=file_hash(path),
                variables={k:dict(subset[k].attrs) for k in config['variables']}, cells=cells,
                downloaded_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=round(time.monotonic()-start,2),
                initialization_is_not_publication_time=True)
    immutable_json(manifest, info)
    return path
