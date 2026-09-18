"""Inspect a small development-period GFS subset before bulk acquisition."""
import json
import time
import urllib.request
from pathlib import Path
import numpy as np
import xarray as xr
import icechunk

url = 'https://stac.dynamical.org/noaa-gfs-forecast/collection.json'
with urllib.request.urlopen(url, timeout=30) as response:
    catalog = json.load(response)
repo = icechunk.Repository.open(icechunk.http_storage(catalog['assets']['icechunk-https']['href']))
session = repo.readonly_session('main')
print('Snapshot:', session.snapshot_id, flush=True)
ds = xr.open_zarr(session.store, chunks=None, consolidated=False)
print('Dimensions:', dict(ds.sizes), flush=True)
print('Leads:', ds.lead_time.values[:5], ds.lead_time.values[-5:], flush=True)
variables = ['precipitation_surface', 'precipitable_water_atmosphere', 'relative_humidity_2m']
for name in variables:
    print(name, ds[name].attrs, ds[name].encoding, flush=True)
sample = ds[variables].sel(init_time='2023-06-01T00:00', latitude=slice(23, 15), longitude=slice(72, 81), lead_time=slice(np.timedelta64(0, 'h'), np.timedelta64(147, 'h')))
start = time.monotonic()
sample.load()
print('Subset seconds:', time.monotonic()-start, 'sizes:', dict(sample.sizes), flush=True)
for name in variables:
    a = sample[name].values
    print(name, 'shape:', a.shape, 'finite:', int(np.isfinite(a).sum()), 'range:', float(np.nanmin(a)), float(np.nanmax(a)), flush=True)
