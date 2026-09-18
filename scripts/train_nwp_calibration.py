"""Fit forecast correction and event models; freeze decisions before the 2026 audit."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import lightgbm as lgb
import sklearn
from datetime import datetime, timezone
from sklearn.linear_model import LogisticRegression
from src.ingestion.forecast_schema import ROOT,read_json,immutable_json,file_hash,digest
from src.ingestion.nwp_archive import experiment_context
from src.modeling.nwp_calibration import development_masks
from src.modeling.rainfall_events import amount_metrics,event_metrics,choose_threshold


def probability(raw, calibration):
    return 1/(1+np.exp(-np.clip(calibration['slope']*raw+calibration['intercept'],-40,40)))


def train():
    config,meta,version=experiment_context()
    manifest_path=ROOT/f'data/research/manifests/{version}-development-pairs.json'
    manifest=read_json(manifest_path)
    if manifest['config'] != config: raise ValueError('Pair configuration mismatch')
    for name,expected in manifest['code_hashes'].items():
        if file_hash(ROOT/name)!=expected: raise ValueError('Pair construction code changed')
    code={name:file_hash(ROOT/name) for name in ['scripts/train_nwp_calibration.py','scripts/build_nwp_pairs.py','src/modeling/nwp_calibration.py','src/ingestion/nwp_archive.py','src/modeling/rainfall_events.py']}
    runtime=dict(numpy=np.__version__,pandas=pd.__version__,lightgbm=lgb.__version__,sklearn=sklearn.__version__)
    identity='nwp-model-'+digest([config,file_hash(manifest_path),code,runtime])[:20]
    out=ROOT/'data/research/benchmarks'/identity;out.mkdir(parents=True,exist_ok=True)
    if (out/'selection.json').exists(): print(f'FROZEN {out}',flush=True);return
    rows=[]
    for lead in config['lead_days']:
        path=ROOT/'data/research/arrays'/version/manifest['pair_id']/f'lead-{lead}.npz'
        if file_hash(path)!=manifest['files'][path.name]:raise ValueError('Training pair checksum mismatch')
        with np.load(path,allow_pickle=False) as d:
            # Exclude held-out locations before any model fitting or selection.
            keep=~d['excluded'];X=d['X'][keep];y=d['y'][keep];dates=d['date'][keep]
        years=np.array([int(d[:4]) for d in dates])
        masks=development_masks(years,np.zeros(len(y),bool),config)
        fit,cal,sel=[masks[k] for k in ['train','calibration','selection']]
        if min(fit.sum(),cal.sum(),sel.sum())<500 or np.any(years>=2026):raise ValueError('Invalid development split')
        feature_names=manifest['feature_names']
        frames={k:pd.DataFrame(X[v],columns=feature_names) for k,v in masks.items()}
        amounts={'raw_gfs':amount_metrics(y[sel],X[sel,0])}
        factor=float(y[fit].sum()/X[fit,0].sum())
        amounts['scaled_gfs']=amount_metrics(y[sel],factor*X[sel,0])
        amount=lgb.LGBMRegressor(objective='tweedie',**config['model_parameters'])
        amount.fit(frames['train'],y[fit])
        amount_path=out/f'lead-{lead}-amount.txt';amount.booster_.save_model(str(amount_path))
        amounts['weather_tweedie']=amount_metrics(y[sel],np.maximum(0,amount.predict(frames['selection'])))
        eligible=[k for k,v in amounts.items() if v['mae_mm']<=amounts['raw_gfs']['mae_mm'] and abs(v['bias_mm'])<=.2*v['observed_mean_mm']]
        selected_amount=min(eligible,key=lambda k:amounts[k]['rmse_mm']) if eligible else 'raw_gfs'
        # A one-feature classifier measures how much forecast amount alone supplies.
        logistic=LogisticRegression(C=1.,solver='lbfgs')
        logistic.fit(np.log1p(X[fit,:1]),y[fit]>=20)
        logistic_params=dict(slope=float(logistic.coef_[0,0]),intercept=float(logistic.intercept_[0]))
        classifier=lgb.LGBMClassifier(objective='binary',**config['model_parameters'])
        classifier.fit(frames['train'],y[fit]>=20)
        event_path=out/f'lead-{lead}-event.txt';classifier.booster_.save_model(str(event_path))
        candidate_records={}
        for name in ['rain_only_logistic','weather_classifier']:
            if name=='rain_only_logistic':
                raw_cal=logistic.decision_function(np.log1p(X[cal,:1]))
                raw_sel=logistic.decision_function(np.log1p(X[sel,:1]))
            else:
                raw_cal=classifier.predict(frames['calibration'],raw_score=True)
                raw_sel=classifier.predict(frames['selection'],raw_score=True)
            calibration_model=LogisticRegression(C=1.,solver='lbfgs')
            calibration_model.fit(raw_cal.reshape(-1,1),y[cal]>=20)
            calibration=dict(slope=float(calibration_model.coef_[0,0]),intercept=float(calibration_model.intercept_[0]))
            threshold,sweep=choose_threshold(y[sel]>=20,probability(raw_sel,calibration),config['alert_selection'])
            candidate_records[name]=dict(calibration=calibration,selection=threshold,threshold_sweep=sweep)
        raw_event=event_metrics(y[sel]>=20,X[sel,0]>=20)
        policy=config['alert_selection']
        raw_event['constraints_met']=(raw_event['recall']>=policy['minimum_recall'] and (raw_event['precision'] or 0)>=policy['minimum_precision'] and raw_event['false_positive_rate']<=policy['maximum_false_positive_rate'])
        scores={'raw_gfs':raw_event,**{k:v['selection'] for k,v in candidate_records.items()}}
        qualified=[k for k,v in scores.items() if v['constraints_met']]
        selected_event=max(qualified or list(scores),key=lambda k:(scores[k]['csi'] or 0,scores[k]['precision'] or 0))
        row=dict(lead_days=lead,train_n=int(fit.sum()),calibration_n=int(cal.sum()),selection_n=int(sel.sum()),
                 selected_amount=selected_amount,amount_constraints_met=bool(eligible),amount_validation=amounts,amount_scale=factor,
                 selected_event=selected_event,event_joint_target_met=bool(qualified),event_validation=scores,
                 event_candidates=candidate_records,logistic_params=logistic_params,
                 artifact_hashes={p.name:file_hash(p) for p in [amount_path,event_path]},
                 training_event_frequency=float(np.mean(y[fit]>=20)))
        immutable_json(out/f'lead-{lead}-selection.json',row);rows.append(row)
        s=scores[selected_event]
        print(f'Day {lead}: {selected_event}; selection recall={s["recall"]:.3f}, precision={s["precision"]:.3f}, CSI={s["csi"]:.3f}; joint50={bool(qualified)}; amount={selected_amount}',flush=True)
    immutable_json(out/'selection.json',dict(experiment_id=identity,config=config,runtime=runtime,code_hashes=code,
                   frozen_at=datetime.now(timezone.utc).isoformat(),
                   dataset_version=version,development_pair_manifest=manifest_path.name,development_pair_sha256=file_hash(manifest_path),
                   feature_names=manifest['feature_names'],by_lead=rows))
    print(f'FROZEN {out}',flush=True)


if __name__=='__main__':train()
