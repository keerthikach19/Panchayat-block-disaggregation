"""Public IMD daily rainfall archive; native grid is never relabeled as stations."""
import calendar
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import numpy as np
from shapely.geometry import Point, shape
from shapely.ops import unary_union
from src.ingestion.forecast_schema import ROOT, file_hash, immutable_json, read_json, digest

PAGE='https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html'
ENDPOINT='https://imdpune.gov.in/cmpg/Griddata/rainfall.php'

def decode(data, year):
    days=366 if calendar.isleap(year) else 365
    if len(data)!=days*129*135*4:
        raise ValueError(f'Invalid IMD binary length for {year}: {len(data)}')
    candidates=[]
    for endian in ('<f4','>f4'):
        a=np.frombuffer(data,dtype=endian).reshape(days,129,135)
        missing=a == -999
        valid=np.isfinite(a)&(a>=0)&(a<=5000)
        if (missing|valid).all() and missing.mean()>.01 and valid.mean()>.1 and np.max(a[valid])>1:
            candidates.append(a.astype(np.float32))
    if len(candidates)!=1:
        raise ValueError('Ambiguous or invalid IMD byte order/range/missing-value layout')
    result=candidates[0];result[result == -999]=np.nan
    return result

def acquire_year(year, root=ROOT):
    if not 1901<=year<=2025: raise ValueError('Year outside inspected provider range')
    raw=root/'data/research/raw/imd';raw.mkdir(parents=True,exist_ok=True)
    path=raw/f'rainfall-{year}.grd'
    manifest=root/f'data/research/manifests/imd-{year}.json'
    if path.exists():
        if not manifest.exists() or file_hash(path)!=read_json(manifest)['sha256']:
            raise ValueError('Existing download has no matching provenance; refusing overwrite')
        decode(path.read_bytes(),year)
        return path
    request=Request(ENDPOINT,data=urlencode({'rain':str(year)}).encode(),
                    headers={'User-Agent':'Maharashtra-rainfall-research/1.0','Referer':PAGE})
    with urlopen(request,timeout=180) as response:
        data=response.read(26_000_001)
        content_type=response.headers.get('Content-Type','')
        final_url=response.url
    array=decode(data,year)
    metadata={'provider':'IMD','source_page':PAGE,'request_url':ENDPOINT,'request_form':{'rain':str(year)},
        'final_url':final_url,'year':year,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
        'downloaded_at':datetime.now(timezone.utc).isoformat(),'content_type':content_type,
        'target_kind':'gauge_based_gridded_analysis','not_independent_station_observations':True,
        'grid':{'latitude_start':6.5,'longitude_start':66.5,'spacing_degrees':.25,'shape':list(array.shape)},
        'finite_values':int(np.isfinite(array).sum()),'missing_values':int(np.isnan(array).sum()),
        'max_rainfall_mm':float(np.nanmax(array)),
        'accumulation_hours':'Not established from download page; do not assume alignment with forecast valid dates',
        'citation':'Pai et al. (2014), MAUSAM 65(1), 1-18'}
    # A new checkout has tracked manifests but no ignored raw files. Reuse the
    # original provenance only when the re-downloaded bytes match exactly.
    if manifest.exists():
        if read_json(manifest)['sha256']!=metadata['sha256']:
            raise ValueError('Provider data revision differs from frozen source hash')
    else:
        immutable_json(manifest,metadata)
    with path.open('xb') as f: f.write(data)
    return path

def extract(years, root=ROOT):
    def geometry(name):
        raw=read_json(root/'data/boundaries'/name)
        return unary_union([shape(f['geometry']) for f in raw['features']])
    state=geometry('maharashtra_state.geojson')
    nashik=geometry('nashik_district.geojson')
    halo=nashik.buffer(.25)
    cells=[]
    for iy in range(129):
        for ix in range(135):
            lat,lon=6.5+.25*iy,66.5+.25*ix
            p=Point(lon,lat)
            if state.covers(p):
                cells.append({'grid_id':f'IMD025_{iy}_{ix}','iy':iy,'ix':ix,'lat':lat,'lon':lon,
                              'nashik':bool(nashik.covers(p)),'excluded_from_training':bool(halo.covers(p))})
    if not cells or not any(c['nashik'] for c in cells):raise ValueError('Invalid state/Nashik extraction')
    arrays=[]; dates=[];sources=[]
    for year in sorted(years):
        path=root/f'data/research/raw/imd/rainfall-{year}.grd'
        manifest=read_json(root/f'data/research/manifests/imd-{year}.json')
        if file_hash(path)!=manifest['sha256']:raise ValueError('Raw source checksum mismatch')
        arrays.append(decode(path.read_bytes(),year)[:,[c['iy'] for c in cells],[c['ix'] for c in cells]])
        dates.extend(np.arange(np.datetime64(f'{year}-01-01'),np.datetime64(f'{year+1}-01-01')).astype(str).tolist())
        sources.append({'year':year,'sha256':manifest['sha256']})
    metadata={'schema':'imd-mh-grid-v1','cells':cells,'dates':dates,'sources':sources,
        'state_boundary_sha256':file_hash(root/'data/boundaries/maharashtra_state.geojson'),
        'nashik_boundary_sha256':file_hash(root/'data/boundaries/nashik_district.geojson'),
        'coverage':'Grid centers inside supplied state polygon; boundary cells and geographic labels are approximate',
        'spatial_holdout':'Nashik centers withheld; additional 0.25 degree halo excluded from training'}
    version='imd-mh-'+digest(metadata)[:20]
    out=root/'data/research/arrays'/version;out.mkdir(parents=True,exist_ok=True)
    values=np.concatenate(arrays)
    file=out/'rainfall.npy'
    if file.exists():
        if not np.array_equal(np.load(file),values,equal_nan=True):raise ValueError('Existing array differs')
    else:
        with file.open('xb') as f:np.save(f,values)
    metadata.update(dataset_version=version,array_sha256=file_hash(file),rows=values.shape[0],
        cell_count=len(cells),nashik_cells=sum(c['nashik'] for c in cells),missing_values=int(np.isnan(values).sum()))
    immutable_json(root/'data/research/manifests'/f'{version}.json',metadata)
    return metadata
