"""Train rainfall amounts and >=20 mm alerts independently; freeze before audit.

Usage: --stage train, then --stage evaluate [--fresh-dataset VERSION].
Training never evaluates 2022 onward. Old test years are explicitly reused.
"""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import lightgbm as lgb
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss
from src.ingestion.forecast_schema import ROOT, read_json, file_hash, digest, immutable_json, atomic_json, safe_id
from src.modeling.rainfall_events import build_features, amount_metrics, event_metrics, choose_threshold


def context(experiment_id=None):
    config = read_json(ROOT/'config/rainfall_event_experiment.json')
    meta = read_json(ROOT/f'data/research/manifests/{config["dataset_version"]}.json')
    path = ROOT/f'data/research/arrays/{config["dataset_version"]}/rainfall.npy'
    if file_hash(path) != meta['array_sha256']:
        raise ValueError('Dataset checksum mismatch')
    code_hashes = {p: file_hash(ROOT/p) for p in ['scripts/train_rainfall_events.py', 'src/modeling/rainfall_events.py']}
    runtime = dict(numpy=np.__version__, pandas=pd.__version__, lightgbm=lgb.__version__, sklearn=sklearn.__version__)
    identity = 'rain-events-' + digest([config, meta['array_sha256'], code_hashes, runtime])[:20]
    out = ROOT/'data/research/benchmarks'/safe_id(experiment_id or identity)
    out.mkdir(parents=True, exist_ok=True)
    return config, meta, np.load(path), out, code_hashes, runtime


def frame(X, names):
    return pd.DataFrame(X, columns=names)


def sigmoid(raw, calibration):
    z = np.clip(calibration['slope'] * raw + calibration['intercept'], -40, 40)
    return 1 / (1 + np.exp(-z))


def train():
    config, meta, rain, out, code_hashes, runtime = context()
    if (out/'selection.json').exists():
        print(f'Already frozen: {out}', flush=True); return
    # Remove all test years BEFORE feature construction or fitting.
    dates = pd.DatetimeIndex(meta['dates'])
    mask = dates.year <= config['selection_years'][1]
    dates, rain = dates[mask], rain[mask]
    cells = meta['cells']; n = len(cells)
    spatial = np.array([not c['excluded_from_training'] for c in cells])
    records = []
    for lead in config['lead_days']:
        X, y, times, names = build_features(rain, dates, cells, lead, config['observation_lag_days'])
        years = np.repeat(dates.year[times], n)
        ok = np.isfinite(y) & np.isfinite(X).all(axis=1) & np.tile(spatial, len(times))
        def split(key):
            lo, hi = config[key]
            return ok & (years >= lo) & (years <= hi)
        fit, cal, select = [split(k) for k in ['train_years', 'probability_calibration_years', 'selection_years']]
        if min(fit.sum(), cal.sum(), select.sum()) < 100:
            raise ValueError('Insufficient split data')
        print(f'Day {lead}: training amount models and event classifier', flush=True)
        amounts = {'persistence': amount_metrics(y[select], X[select, 0])}
        hashes = {}
        for label, objective in [('tweedie_context', 'tweedie'), ('squared_context', 'regression')]:
            model = lgb.LGBMRegressor(objective=objective, **config['model_parameters'])
            model.fit(frame(X[fit], names), y[fit])
            prediction = np.maximum(0, model.predict(frame(X[select], names)))
            amounts[label] = amount_metrics(y[select], prediction)
            path = out/f'lead-{lead}-{label}.txt'; model.booster_.save_model(str(path)); hashes[path.name] = file_hash(path)
        eligible = [k for k, v in amounts.items() if abs(v['bias_mm']) <= .2*v['observed_mean_mm'] and v['mae_mm'] <= amounts['persistence']['mae_mm']]
        chosen = min(eligible or list(amounts), key=lambda k: amounts[k]['rmse_mm'])
        classifier = lgb.LGBMClassifier(objective='binary', **config['model_parameters'])
        classifier.fit(frame(X[fit], names), (y[fit] >= config['event_threshold_mm']).astype(int))
        # Unweighted binary model; logistic calibration on a separate earlier year.
        calibrator = LogisticRegression(C=1.0, solver='lbfgs')
        calibrator.fit(classifier.predict(frame(X[cal], names), raw_score=True).reshape(-1, 1), y[cal] >= 20)
        calibration = dict(slope=float(calibrator.coef_[0, 0]), intercept=float(calibrator.intercept_[0]))
        prob = sigmoid(classifier.predict(frame(X[select], names), raw_score=True), calibration)
        threshold, sweep = choose_threshold(y[select] >= 20, prob, config['alert_selection'])
        path = out/f'lead-{lead}-event.txt'; classifier.booster_.save_model(str(path)); hashes[path.name] = file_hash(path)
        record = dict(lead_days=lead, selected_amount=chosen, amount_constraints_met=bool(eligible),
                      amount_validation=amounts, event_selection=threshold, threshold_sweep=sweep,
                      calibration=calibration, feature_names=names, artifact_hashes=hashes,
                      train_n=int(fit.sum()), calibration_n=int(cal.sum()), selection_n=int(select.sum()),
                      validation_brier=float(brier_score_loss(y[select] >= 20, prob)),
                      validation_average_precision=float(average_precision_score(y[select] >= 20, prob)),
                      training_event_frequency=float(np.mean(y[fit] >= 20)))
        immutable_json(out/f'lead-{lead}-selection.json', record)
        records.append(record)
        print(f'Day {lead}: amount={chosen}, event threshold={threshold["threshold"]}, validation recall={threshold["recall"]:.3f}, precision={threshold["precision"]:.3f}, CSI={threshold["csi"]:.3f}', flush=True)
    immutable_json(out/'selection.json', dict(experiment_id=out.name, config=config, by_lead=records,
                   code_hashes=code_hashes, runtime=runtime, dataset_hash=meta['array_sha256']))
    print(f'FROZEN before test evaluation: {out}', flush=True)


def evaluate(fresh_dataset=None, experiment_id=None):
    config, meta, rain, out, current_hashes, runtime = context(experiment_id)
    locked = read_json(out/'selection.json')
    if locked['config'] != config or locked['runtime'] != runtime or locked['dataset_hash'] != meta['array_sha256']:
        raise ValueError('Frozen training configuration, runtime or dataset mismatch')
    if locked['code_hashes']['src/modeling/rainfall_events.py'] != current_hashes['src/modeling/rainfall_events.py']:
        raise ValueError('Frozen feature implementation mismatch')
    evaluation_id = 'evaluation-' + digest([current_hashes, fresh_dataset])[:16]
    evaluation_out = out/evaluation_id
    evaluation_out.mkdir(parents=True, exist_ok=True)
    datasets = [('reused_2022_2024', meta, rain, config['reused_test_years'])]
    if fresh_dataset:
        fresh_meta = read_json(ROOT/f'data/research/manifests/{fresh_dataset}.json')
        path = ROOT/f'data/research/arrays/{fresh_dataset}/rainfall.npy'
        if file_hash(path) != fresh_meta['array_sha256'] or fresh_meta['cells'] != meta['cells']:
            raise ValueError('Fresh data checksum/geography mismatch')
        datasets.append(('fresh_2025', fresh_meta, np.load(path), [config['fresh_test_year']]*2))
    evaluations = {}
    old_dir = ROOT/'data/research/benchmarks'/config['original_experiment']
    old_report = read_json(old_dir/'report.json')
    for label, dataset, values, years in datasets:
        dates = pd.DatetimeIndex(dataset['dates']); cells = dataset['cells']; n = len(cells)
        rows = []
        for record in locked['by_lead']:
            lead = record['lead_days']
            for name, expected in record['artifact_hashes'].items():
                if file_hash(out/name) != expected: raise ValueError('Frozen model was modified')
            X, y, times, names = build_features(values, dates, cells, lead, config['observation_lag_days'])
            if names != record['feature_names']: raise ValueError('Feature schema mismatch')
            sample_year = np.repeat(dates.year[times], n)
            test = ((sample_year >= years[0]) & (sample_year <= years[1]) &
                    np.tile([c['nashik'] for c in cells], len(times)) & np.isfinite(y) & np.isfinite(X).all(axis=1))
            X, y = X[test], y[test]
            if not len(y): raise ValueError('Empty evaluation set')
            # Original benchmark clamps negative regression predictions to zero.
            old = np.maximum(0, lgb.Booster(model_file=str(old_dir/f'lead-{lead}.txt')).predict(X[:, :12], num_threads=4))
            selected = record['selected_amount']
            prediction = X[:, 0] if selected == 'persistence' else np.maximum(0, lgb.Booster(model_file=str(out/f'lead-{lead}-{selected}.txt')).predict(X, num_threads=4))
            raw = lgb.Booster(model_file=str(out/f'lead-{lead}-event.txt')).predict(X, raw_score=True, num_threads=4)
            probability = sigmoid(raw, record['calibration'])
            alert = probability >= record['event_selection']['threshold']
            scores = dict(lead_days=lead, n=len(y), selected_amount=selected,
                          original=amount_metrics(y, old), revised=amount_metrics(y, prediction),
                          persistence=amount_metrics(y, X[:, 0]), event=event_metrics(y >= 20, alert),
                          brier=float(brier_score_loss(y >= 20, probability)),
                          average_precision=float(average_precision_score(y >= 20, probability)),
                          event_prevalence=float(np.mean(y >= 20)),
                          climatology_brier=float(brier_score_loss(y >= 20, np.full(len(y), record['training_event_frequency']))),
                          alert_threshold=record['event_selection']['threshold'])
            if label == 'reused_2022_2024':
                prior = next(r for r in old_report['by_lead'] if r['lead_days'] == lead)
                if abs(scores['original']['mae_mm'] - prior['nashik_test'][prior['selected']]['mae_mm']) > 1e-5:
                    raise ValueError('Original benchmark replay mismatch')
            np.savez_compressed(evaluation_out/f'{label}-day-{lead}.npz', observed=y, original=old, amount=prediction,
                                event_probability=probability, event_alert=alert,
                                date=np.repeat(dates[times].strftime('%Y-%m-%d').to_numpy(dtype='U10'), n)[test],
                                grid_id=np.tile([c['grid_id'] for c in cells], len(times))[test])
            rows.append(scores)
            print(f'{label} day {lead}: MAE={scores["revised"]["mae_mm"]:.2f}, RMSE={scores["revised"]["rmse_mm"]:.2f}, recall={scores["event"]["recall"]:.3f}, precision={scores["event"]["precision"]:.3f}, CSI={scores["event"]["csi"]:.3f}', flush=True)
        evaluations[label] = dict(dataset_version=dataset['dataset_version'], array_sha256=dataset['array_sha256'],
                                  years=years, by_lead=rows)
    report = dict(experiment_id=out.name, status='RESEARCH_ONLY_NOT_PROMOTED', selection=locked,
                  selection_sha256=file_hash(out/'selection.json'), evaluations=evaluations,
                  evaluation_id=evaluation_id,
                  evaluation_code_hashes=current_hashes,
                  limitations=['2022–2024 results are a reused comparison, not a fresh holdout.',
                    'Event alerts and rainfall amounts are separate outputs; alert recall is not amount accuracy.',
                    'Predictors use historical rain, location and season; no issued weather forecast inputs.',
                    'Two-day observation availability lag is assumed, not operationally verified.',
                    '2025 is a single-year grid-scale audit, not village or station validation.',
                    'No village forecast replacement or production activation.'])
    immutable_json(evaluation_out/'report.json', report)
    # This pointer changes the evidence page only, never a weather-serving model.
    atomic_json(ROOT/'data/research/benchmarks/event_evidence.json', dict(experiment_id=out.name, evaluation_id=evaluation_id))
    print(evaluation_out/'report.json', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['train', 'evaluate'], required=True)
    parser.add_argument('--fresh-dataset')
    parser.add_argument('--experiment-id', help='Evaluate a previously frozen experiment without retraining')
    args = parser.parse_args()
    train() if args.stage == 'train' else evaluate(args.fresh_dataset, args.experiment_id)
