"""Forecast-only feature extraction and frozen temporal/spatial split contracts."""
import numpy as np
import pandas as pd
from src.ingestion.nwp_archive import integrate_window

FEATURE_NAMES = ['gfs_rain_mm', 'gfs_max_step_rate_mmh', 'gfs_rain_hours_fraction',
                 'gfs_pwat_mean', 'gfs_rh_mean', 'gfs_rh_max',
                 'gfs_neighbor_rain_mean', 'gfs_neighbor_rain_max',
                 'latitude', 'longitude', 'season_sin', 'season_cos']


def window_times(initialization, lead, config):
    if lead not in config['lead_days']: raise ValueError('Unsupported lead')
    init = pd.Timestamp(initialization)
    if init.tzinfo is None: init = init.tz_localize('UTC')
    if init.utcoffset().total_seconds() != 0 or init.hour != config['init_hour_utc'] or init.minute or init.second:
        raise ValueError('Expected the configured UTC initialization cycle')
    decision = init + pd.Timedelta(hours=config['decision_delay_hours'])
    start = init + pd.Timedelta(hours=config['first_window_start_hour']+24*(lead-1))
    end = start + pd.Timedelta(hours=config['window_hours'])
    if decision > start or end.hour != 3 or (end-start).total_seconds() != 86400:
        raise ValueError('Invalid forecast/observation time alignment')
    return init, decision, start, end


def forecast_features(payload, initialization, lead, cells, config):
    init, _, start, end = window_times(initialization, lead, config)
    a, b = (start-init).total_seconds()/3600, (end-init).total_seconds()/3600
    hours = np.asarray(payload['lead_hours'])
    rain = integrate_window(hours, payload['precipitation_surface'], a, b)
    idx = np.flatnonzero((hours > a) & (hours <= b))
    widths = hours[idx]-hours[idx-1]
    rate = np.asarray(payload['precipitation_surface'])[idx]
    pwat = np.asarray(payload['precipitable_water_atmosphere'])[idx]
    rh = np.asarray(payload['relative_humidity_2m'])[idx]
    if rate.shape[1] != len(cells) or pwat.shape != rate.shape or rh.shape != rate.shape:
        raise ValueError('Forecast grid/variable shape mismatch')
    complete = np.isfinite(rate).all(axis=0) & np.isfinite(pwat).all(axis=0) & np.isfinite(rh).all(axis=0)
    if np.any((rh[np.isfinite(rh)] < 0) | (rh[np.isfinite(rh)] > 100)) or np.any(pwat[np.isfinite(pwat)] < 0):
        raise ValueError('Unphysical forecast moisture')
    lat, lon = np.array([[c['lat'],c['lon']] for c in cells]).T
    distances = (lat[:,None]-lat)**2 + ((lon[:,None]-lon)*np.cos(np.deg2rad(lat[:,None])))**2
    np.fill_diagonal(distances, np.inf)
    neighbors = np.argsort(distances, axis=1)[:,:min(8,len(cells)-1)]
    # Neighbors are same-run forecasts, never future observations.
    nbr = rain[neighbors]
    values = [rain, np.max(rate*3600,axis=0), np.sum((rate*3600 >= 1)*widths[:,None],axis=0)/24,
              np.average(pwat,axis=0,weights=widths), np.average(rh,axis=0,weights=widths), np.max(rh,axis=0),
              np.mean(nbr,axis=1), np.max(nbr,axis=1), lat, lon,
              np.full(len(cells), np.sin(2*np.pi*end.dayofyear/365.25)),
              np.full(len(cells), np.cos(2*np.pi*end.dayofyear/365.25))]
    X = np.stack(values,axis=1).astype(np.float32)
    complete &= np.isfinite(X).all(axis=1)
    return X, complete, end.strftime('%Y-%m-%d')


def development_masks(years, excluded, config):
    years, excluded = np.asarray(years), np.asarray(excluded, dtype=bool)
    if years.shape != excluded.shape: raise ValueError('Split shape mismatch')
    masks = {name: np.isin(years,config[f'{name}_years']) & ~excluded for name in ['train','calibration','selection']}
    if np.any(sum(m.astype(int) for m in masks.values()) > 1):
        raise ValueError('Overlapping development years')
    return masks
