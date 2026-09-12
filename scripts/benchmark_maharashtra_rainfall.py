"""Historical grid predictability only; does not activate a serving model."""
import sys
import argparse
import json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from src.ingestion.forecast_schema import ROOT, read_json, file_hash, digest, immutable_json

def metrics(y,p):
    err=p-y
    wet=y>=20
    predicted=p>=20
    hits=int((wet&predicted).sum());misses=int((wet&~predicted).sum());false=int((~wet&predicted).sum())
    return {'n':len(y),'mae_mm':float(abs(err).mean()),'rmse_mm':float(np.sqrt((err**2).mean())),
            'bias_mm':float(err.mean()),'observed_mean_mm':float(y.mean()),
            'heavy_20mm_n':int(wet.sum()),'heavy_20mm_mae':float(abs(err[wet]).mean()) if wet.any() else None,
            'heavy_20mm_csi':hits/(hits+misses+false) if hits+misses+false else None,
            'heavy_20mm_hits':hits,'heavy_20mm_misses':misses,'heavy_20mm_false_alarms':false}

def run(version):
    config=read_json(ROOT/'config/calibration_experiment.json')
    policy=config['historical_grid_benchmark']
    meta=read_json(ROOT/f'data/research/manifests/{version}.json')
    file=ROOT/f'data/research/arrays/{version}/rainfall.npy'
    if file_hash(file)!=meta['array_sha256']:raise ValueError('Dataset array changed')
    dates=pd.DatetimeIndex(meta['dates']);rain=np.load(file)
    if not np.all(np.diff(dates.values)==np.timedelta64(1,'D')):raise ValueError('Daily series is not continuous')
    cells=meta['cells'];n=len(cells)
    lat=np.array([c['lat'] for c in cells]);lon=np.array([c['lon'] for c in cells])
    held=np.array([c['nashik'] for c in cells]);halo=np.array([c['excluded_from_training'] for c in cells])
    identity='rain-benchmark-'+digest([meta['array_sha256'],config,'lag-lightgbm-v1'])[:20]
    out=ROOT/'data/research/benchmarks'/identity;out.mkdir(parents=True,exist_ok=True)
    if (out/'report.json').exists():
        print('Existing frozen benchmark: '+str(out/'report.json'));return
    records=[]
    for lead in policy['lead_days']:
        # Target t, issue t-lead, latest usable retrospective observation t-lead-lag.
        # All lag/rolling features stop at that cutoff. Provider real-time availability is unverified.
        times=np.arange(lead+policy['observation_lag_days']+14,len(dates))
        times=times[np.isin(dates.month[times],policy['months'])]
        available=times-lead-policy['observation_lag_days']
        values=[rain[available-k] for k in (0,1,2,6,13)]
        values += [np.mean(np.stack([rain[available-k] for k in range(length)]),axis=0) for length in (3,7,14)]
        names=['rain_last','rain_previous','rain_two_before','rain_six_before','rain_thirteen_before','mean3','mean7','mean14','latitude','longitude','season_sin','season_cos']
        values += [np.broadcast_to(lat,(len(times),n)),np.broadcast_to(lon,(len(times),n)),
                   np.broadcast_to(np.sin(2*np.pi*dates.dayofyear[times].to_numpy()/365.25)[:,None],(len(times),n)),
                   np.broadcast_to(np.cos(2*np.pi*dates.dayofyear[times].to_numpy()/365.25)[:,None],(len(times),n))]
        X=np.stack(values,axis=2).reshape(-1,len(names)).astype(np.float32)
        y=rain[times].reshape(-1)
        years=np.repeat(dates.year[times],n);months=np.repeat(dates.month[times],n)
        ok=np.isfinite(y)&np.isfinite(X).all(axis=1)
        def period(pair):return (years>=pair[0])&(years<=pair[1])
        train=ok&period(policy['train_years'])&np.tile(~halo,len(times))
        validation=ok&period(policy['validation_years'])&np.tile(~halo,len(times))
        test=ok&period(policy['test_years'])&np.tile(held,len(times))
        if min(train.sum(),validation.sum(),test.sum())<100:raise ValueError('Insufficient locked split data')
        monthly={m:float(y[train&(months==m)].mean()) for m in policy['months']}
        candidates={'persistence':X[:,0], 'regional_monthly_mean':np.array([monthly[m] for m in months])}
        estimators={}
        for name,objective in [('lightgbm_absolute','regression_l1'),('lightgbm_tweedie','tweedie')]:
            model=LGBMRegressor(objective=objective,n_estimators=120,num_leaves=15,min_child_samples=200,
                learning_rate=.06,reg_lambda=10.,verbosity=-1,n_jobs=4,random_state=42,deterministic=True,force_col_wise=True)
            model.fit(pd.DataFrame(X[train],columns=names),y[train])
            estimators[name]=model
            candidates[name]=np.maximum(0,model.predict(pd.DataFrame(X,columns=names)))
        validation_scores={name:metrics(y[validation],p[validation]) for name,p in candidates.items()}
        # Choose solely by development data, before inspecting Nashik held-out results.
        winner=min(candidates,key=lambda name:validation_scores[name]['mae_mm'])
        test_scores={name:metrics(y[test],p[test]) for name,p in candidates.items()}
        if winner in estimators:estimators[winner].booster_.save_model(str(out/f'lead-{lead}.txt'))
        record={'lead_days':lead,'train_n':int(train.sum()),'validation_n':int(validation.sum()),'test_n':int(test.sum()),
            'selected':winner,'validation':validation_scores,'nashik_test':test_scores,
            'monthly_baseline':monthly,'feature_names':names,'eligible_for_production':False}
        records.append(record)
        immutable_json(out/f'lead-{lead}.json',record)
        print(f'lead {lead}: selected {winner}; Nashik MAE {test_scores[winner]["mae_mm"]:.3f}; persistence {test_scores["persistence"]["mae_mm"]:.3f}',flush=True)
    report={'experiment_id':identity,'dataset_version':version,'policy':config,'by_lead':records,
        'nashik_cells':int(held.sum()),'state_cells':n,'excluded_halo_cells':int(halo.sum()),
        'status':'RESEARCH_ONLY_NOT_PROMOTED','target_kind':'IMD gauge-based gridded analysis; not village observations',
        'limitations':['No archived NWP or IMD issued forecasts used; this is not forecast bias calibration.',
          'Two-day observation availability lag is assumed retrospectively, not operationally verified.',
          'IMD daily accumulation hours and vintage availability must be established before deployment.',
          'Nashik plus a 0.25 degree halo excluded from training/validation; temporal test 2022–2024.',
          'Heavy-rain event skill must be reviewed; low MAE can favor systematically low rainfall.',
          'No fine-scale downscaling or calibrated uncertainty is established.']}
    immutable_json(out/'report.json',report)
    print(out/'report.json',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dataset-version',required=True)
    run(p.parse_args().dataset_version)
