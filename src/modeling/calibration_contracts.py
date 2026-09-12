"""Exact forecast/observation pairing and non-destructive shared-field aggregation."""
from datetime import datetime
import math

def timestamp(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:raise ValueError('Timezone-aware timestamps required')
    return result

def align_pairs(forecasts, observations):
    """Never infer issue times or accumulation windows from date-only CSV exports."""
    index={}
    for obs in observations:
        if obs['target_kind'] not in ('independent_gauge','gauge_based_gridded_analysis'):
            raise ValueError('Unverified/proxy observations cannot be relabeled as gauge targets')
        key=(obs['location_id'],obs['support_id'],timestamp(obs['valid_start']),timestamp(obs['valid_end']))
        if key[3]<=key[2]:raise ValueError('Invalid observation interval')
        if key in index:raise ValueError('Duplicate/conflicting observation interval')
        if not obs.get('source_sha256') or len(obs['source_sha256'])!=64:raise ValueError('Observation source hash required')
        if not math.isfinite(obs['rainfall_mm']) or obs['rainfall_mm']<0:raise ValueError('Invalid observed rain')
        index[key]=obs
    pairs=[];unmatched=[];seen=set()
    for fc in forecasts:
        issue=timestamp(fc['issued_at']);available=timestamp(fc['available_at'])
        start,end=timestamp(fc['valid_start']),timestamp(fc['valid_end'])
        if end<=start or issue>start or available>start:raise ValueError('Forecast not available before accumulation starts')
        if available<issue:raise ValueError('Availability predates issue')
        if not fc.get('source_sha256') or len(fc['source_sha256'])!=64:raise ValueError('Forecast source hash required')
        if not math.isfinite(fc['rainfall_mm']) or fc['rainfall_mm']<0:raise ValueError('Invalid forecast rain')
        for feature in fc.get('features',[]):
            if timestamp(feature['available_at'])>available:raise ValueError('Future feature leakage')
        identity=(fc['source'],fc['location_id'],fc['support_id'],issue,start,end)
        if identity in seen:raise ValueError('Duplicate/conflicting forecast')
        seen.add(identity)
        key=(fc['location_id'],fc['support_id'],start,end)
        if key not in index:unmatched.append(fc);continue
        pairs.append({'forecast':fc,'observation':index[key],'lead_hours':(start-issue).total_seconds()/3600})
    return {'pairs':pairs,'unmatched_forecasts':unmatched}

def reconcile(block_estimates, district_estimate, weights, district_weight):
    """Soft nonnegative reconciliation. Weights must come from development errors.

    Minimize sum_i w_i (x_i-b_i)^2 + w_d (sum_i area_i*x_i-d)^2.
    Does not force either original parent input or impose a cosmetic gap cap.
    """
    import numpy as np
    from scipy.optimize import lsq_linear
    if len(block_estimates)!=len(weights) or not block_estimates:raise ValueError('Weight dimensions mismatch')
    b=np.array([r['rainfall_mm'] for r in block_estimates],dtype=float)
    area=np.array([r['area_m2'] for r in block_estimates],dtype=float)
    w=np.array(weights,dtype=float)
    if not np.isfinite(b).all() or (b<0).any() or not np.isfinite(area).all() or (area<=0).any():raise ValueError('Invalid block values/areas')
    if not np.isfinite(w).all() or (w<=0).any() or not math.isfinite(district_weight) or district_weight<=0:raise ValueError('Positive finite error weights required')
    if not math.isfinite(district_estimate) or district_estimate<0:raise ValueError('Invalid district estimate')
    area=area/area.sum()
    design=np.vstack([np.diag(np.sqrt(w)),np.sqrt(district_weight)*area])
    target=np.r_[np.sqrt(w)*b,np.sqrt(district_weight)*district_estimate]
    fit=lsq_linear(design,target,bounds=(0,np.inf),tol=1e-12)
    if not fit.success:raise ValueError('Reconciliation failed')
    return {'block_values':fit.x.tolist(),'district_value':float(area@fit.x),
            'original_block_values':b.tolist(),'original_district_value':district_estimate,
            'weights':w.tolist(),'district_weight':district_weight,
            'status':'research reconciliation; observation-calibrated weights required before use'}
