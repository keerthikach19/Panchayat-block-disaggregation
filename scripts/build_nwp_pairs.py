"""Build exact 03–03 UTC forecast/IMD grid-day pairs, keeping 2026 separate."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from src.ingestion.forecast_schema import ROOT, read_json, immutable_json, file_hash, digest
from src.ingestion.nwp_archive import experiment_context, initialization_dates, verify_daily_receipt, decode_daily
from src.modeling.nwp_calibration import forecast_features, FEATURE_NAMES, window_times


def build(fresh=False):
    config, meta, version = experiment_context()
    cells = meta['cells']; directory = ROOT/'data/research/raw/gfs'/version
    observations, observation_hashes = {}, []
    versions = [config['historical_dataset'], config['selection_dataset']] if not fresh else []
    for v in versions:
        m = read_json(ROOT/f'data/research/manifests/{v}.json'); path = ROOT/f'data/research/arrays/{v}/rainfall.npy'
        if m['cells'] != cells or file_hash(path) != m['array_sha256']: raise ValueError('Observation identity mismatch')
        a = np.load(path)
        observations.update(zip(m['dates'], a)); observation_hashes.append(m['array_sha256'])
    if fresh:
        m = read_json(ROOT/f'data/research/manifests/{version}-observations.json')
        path = ROOT/f'data/research/arrays/{version}/observations-2026.npz'
        if m['cells'] != cells or file_hash(path) != m['array_sha256']: raise ValueError('Fresh observation identity mismatch')
        with np.load(path,allow_pickle=False) as a: observations.update(zip(a['dates'].tolist(),a['rainfall']))
        for receipt in m['source_records']:
            day=receipt['date']; verify_daily_receipt(receipt,day)
            raw=ROOT/'data/research/raw/imd-realtime'/f'{day}.grd'
            if file_hash(raw)!=receipt['sha256']: raise ValueError('Daily observation checksum mismatch')
            grid=decode_daily(raw.read_bytes())
            expected=grid[[c['iy'] for c in cells],[c['ix'] for c in cells]]
            if not np.array_equal(observations[day],expected,equal_nan=True):
                raise ValueError('Daily observation extraction mismatch')
        observation_hashes.append(m['array_sha256'])
    dates = initialization_dates(config, fresh=fresh)
    records = {lead:dict(X=[],y=[],date=[],init=[],grid_id=[],excluded=[],nashik=[]) for lead in config['lead_days']}
    source_hashes, missing = {}, []
    for day in dates:
        key = day.strftime('%Y%m%dT00'); path = directory/f'{key}.npz'
        info = read_json(directory/f'{key}.json')
        if (info['sha256'] != file_hash(path) or info['snapshot_id'] != config['gfs_snapshot_id'] or info['cells'] != cells
            or info['initialization_time'] != day.isoformat()+'Z' or info['asset_url'] != config['gfs_asset_url']):
            raise ValueError('Forecast identity mismatch')
        source_hashes[key] = info['sha256']
        with np.load(path,allow_pickle=False) as payload:
            for lead in config['lead_days']:
                X, complete, target_date = forecast_features(payload,day,lead,cells,config)
                if target_date not in observations: raise ValueError(f'Missing observation date {target_date}')
                y = observations[target_date]
                complete &= np.isfinite(y) & (y >= 0)
                missing.append(dict(init=day.isoformat(),lead=lead,dropped=int((~complete).sum())))
                row = records[lead]
                row['X'].append(X[complete]); row['y'].append(y[complete])
                row['date'].append(np.full(complete.sum(),target_date,dtype='U10'))
                row['init'].append(np.full(complete.sum(),day.isoformat()+'Z',dtype='U20'))
                for name in ['grid_id','excluded','nashik']:
                    attr = 'excluded_from_training' if name == 'excluded' else name
                    row[name].append(np.array([c[attr] for c in cells])[complete])
    label = 'fresh' if fresh else 'development'
    code_hashes={name:file_hash(ROOT/name) for name in ['scripts/build_nwp_pairs.py','src/modeling/nwp_calibration.py','src/ingestion/nwp_archive.py']}
    identity = digest([config,source_hashes,observation_hashes,code_hashes])[:20]
    out = ROOT/'data/research/arrays'/version/f'{label}-{identity}'; out.mkdir(parents=True,exist_ok=True)
    files = {}
    for lead,row in records.items():
        data = {k:np.concatenate(v) for k,v in row.items()}
        path = out/f'lead-{lead}.npz'; np.savez_compressed(path,**data); files[path.name]=file_hash(path)
        print(label,lead,'rows',len(data['y']),'Nashik rows',int(data['nashik'].sum()),flush=True)
    manifest = dict(dataset_version=version,pair_id=out.name,kind=label,config=config,
        feature_names=FEATURE_NAMES,files=files,source_hashes=source_hashes,observation_hashes=observation_hashes,code_hashes=code_hashes,
        dropped=missing,initialization_dates=[d.isoformat()+'Z' for d in dates],
        support='Collocated native 0.25-degree forecast and analysis grid centers; not village observations',
        alignment='Forecast precipitation rate integrated over exactly 24 hours ending 03 UTC on the IMD label date',
        availability=config['availability_status'],fresh_observations_provisional=fresh)
    immutable_json(ROOT/'data/research/manifests'/f'{version}-{label}-pairs.json',manifest)
    print('PAIRED',version,out.name,flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fresh',action='store_true')
    build(p.parse_args().fresh)
