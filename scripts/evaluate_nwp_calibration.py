"""One-way audit of frozen GFS corrections on provisional Nashik 2026 observations."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import lightgbm as lgb
from sklearn.metrics import brier_score_loss,average_precision_score
from src.ingestion.forecast_schema import ROOT,read_json,file_hash,digest,immutable_json,atomic_json,safe_id
from src.ingestion.nwp_archive import experiment_context
from src.modeling.rainfall_events import event_metrics,amount_metrics
from scripts.train_nwp_calibration import probability


def uncertainty(y,alert,initializations):
    """Paired circular two-initialization blocks retain spatial/event correlation."""
    dates=np.unique(initializations)
    counts=np.array([[event_metrics(y[initializations==d]>=20,alert[initializations==d])[k] for k in ['hits','misses','false_alarms']] for d in dates])
    rng=np.random.default_rng(42);values=[]
    for _ in range(500):
        starts=rng.integers(len(dates),size=(len(dates)+1)//2)
        idx=np.column_stack([starts,(starts+1)%len(dates)]).ravel()[:len(dates)]
        h,m,f=counts[idx].sum(axis=0)
        values.append([h/(h+m) if h+m else np.nan,h/(h+f) if h+f else np.nan,h/(h+m+f) if h+m+f else np.nan])
    intervals=np.nanpercentile(values,[2.5,97.5],axis=0)
    return {k:intervals[:,i].tolist() for i,k in enumerate(['recall','precision','csi'])}


def evaluate(experiment):
    config,meta,version=experiment_context()
    root=ROOT/'data/research/benchmarks'/safe_id(experiment);selection=read_json(root/'selection.json')
    if selection['config']!=config:raise ValueError('Frozen configuration changed')
    for name,expected in selection['code_hashes'].items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Frozen training/feature code changed')
    manifest_path=ROOT/f'data/research/manifests/{version}-fresh-pairs.json';manifest=read_json(manifest_path)
    if manifest['config']!=config or manifest['feature_names']!=selection['feature_names']:raise ValueError('Fresh pair schema changed')
    evaluation_id='evaluation-'+digest([file_hash(root/'selection.json'),file_hash(manifest_path),file_hash(Path(__file__))])[:16]
    out=root/evaluation_id;out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for record in selection['by_lead']:
        lead=record['lead_days'];path=ROOT/'data/research/arrays'/version/manifest['pair_id']/f'lead-{lead}.npz'
        if file_hash(path)!=manifest['files'][path.name]:raise ValueError('Fresh pair checksum mismatch')
        for name,expected in record['artifact_hashes'].items():
            if file_hash(root/name)!=expected:raise ValueError('Frozen model changed')
        with np.load(path,allow_pickle=False) as d:
            mask=d['nashik'];X=d['X'][mask];y=d['y'][mask];dates=d['date'][mask];init=d['init'][mask];grid=d['grid_id'][mask]
        if not all(v.startswith('2026-') for v in dates):raise ValueError('Fresh audit contains development dates')
        amount_predictions={'raw_gfs':X[:,0],'scaled_gfs':X[:,0]*record['amount_scale'],
          'weather_tweedie':np.maximum(0,lgb.Booster(model_file=str(root/f'lead-{lead}-amount.txt')).predict(X,num_threads=4))}
        weather_score=lgb.Booster(model_file=str(root/f'lead-{lead}-event.txt')).predict(X,raw_score=True,num_threads=4)
        logistic_score=record['logistic_params']['slope']*np.log1p(X[:,0])+record['logistic_params']['intercept']
        alerts={'raw_gfs':X[:,0]>=20};probs={}
        for name,score in [('rain_only_logistic',logistic_score),('weather_classifier',weather_score)]:
            candidate=record['event_candidates'][name]
            probs[name]=probability(score,candidate['calibration'])
            alerts[name]=probs[name]>=candidate['selection']['threshold']
        selected=record['selected_event'];event_scores={name:event_metrics(y>=20,a) for name,a in alerts.items()}
        amount_scores={name:amount_metrics(y,p) for name,p in amount_predictions.items()}
        metrics=event_scores[selected]
        row=dict(lead_days=lead,n=len(y),initializations=len(np.unique(init)),date_start=str(min(dates)),date_end=str(max(dates)),
                 selected_event=selected,selected_amount=record['selected_amount'],event=metrics,
                 joint_50_50_met=metrics['recall']>=.5 and (metrics['precision'] or 0)>=.5,
                 raw_event=event_scores['raw_gfs'],event_candidates=event_scores,
                 amount=amount_scores[record['selected_amount']],raw_amount=amount_scores['raw_gfs'],amount_candidates=amount_scores,
                 event_intervals_95=uncertainty(y,alerts[selected],init),
                 probability_scores={k:dict(brier=float(brier_score_loss(y>=20,p)),average_precision=float(average_precision_score(y>=20,p))) for k,p in probs.items()})
        rows.append(row)
        np.savez_compressed(out/f'lead-{lead}-predictions.npz',observed=y,raw_amount=X[:,0],
            corrected_amount=amount_predictions[record['selected_amount']],alert=alerts[selected],raw_alert=alerts['raw_gfs'],
            weather_probability=probs['weather_classifier'],rain_only_probability=probs['rain_only_logistic'],date=dates,init=init,grid_id=grid)
        print(f'FRESH day {lead}: recall {metrics["recall"]:.3f}, precision {metrics["precision"]:.3f}, CSI {metrics["csi"]:.3f}; joint50={row["joint_50_50_met"]}; raw recall {row["raw_event"]["recall"]:.3f}',flush=True)
    report=dict(experiment_id=experiment,evaluation_id=evaluation_id,status='RESEARCH_ONLY_NOT_PROMOTED',
        selection=selection,selection_sha256=file_hash(root/'selection.json'),fresh_pair_sha256=file_hash(manifest_path),
        evaluation_source_sha256=file_hash(Path(__file__)),by_lead=rows,
        period='Previously unevaluated Nashik 2026 grid-days; regularly sampled forecast initializations',
        attribution='NOAA NWS NCEP GFS processed by dynamical.org (CC BY 4.0); IMD provisional daily gridded rainfall',
        limitations=['2026 IMD daily observations are provisional and may differ from finalized annual analyses.',
          'Native 0.25-degree grid centers, not independent village gauges.',
          config['availability_status'],
          'Lead 1 integrates initialization +27 to +51 hours; each later lead shifts the window by 24 hours.',
          'Development runs sampled every five days; fresh initializations every three days; scores are not all-day seasonal scores.',
          '95% intervals use 500 circular block bootstrap samples of two adjacent initialization dates, keeping all grid cells together.',
          'No village-serving model or official block forecast has been replaced.'])
    immutable_json(out/'report.json',report)
    immutable_json(out/'artifact_hashes.json',{p.name:file_hash(p) for p in sorted(out.iterdir()) if p.name!='artifact_hashes.json'})
    atomic_json(ROOT/'data/research/benchmarks/nwp_evidence.json',dict(experiment_id=experiment,evaluation_id=evaluation_id))
    print(out/'report.json',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--experiment-id',required=True);evaluate(p.parse_args().experiment_id)
