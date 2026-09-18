"""Verify the packaged model and evaluation against saved predictions, not rounded UI text."""
import numpy as np
from src.ingestion.forecast_schema import ROOT, read_json, file_hash
from src.modeling.rainfall_events import event_metrics, amount_metrics


def test_frozen_nwp_evidence_replays_metrics_and_decisions():
    base=ROOT/'data/research/benchmarks'
    pointer=read_json(base/'nwp_evidence.json')
    model_dir=base/pointer['experiment_id'];out=model_dir/pointer['evaluation_id']
    report=read_json(out/'report.json');selection=read_json(model_dir/'selection.json')
    assert report['selection']==selection
    assert report['selection_sha256']==file_hash(model_dir/'selection.json')
    assert report['status']=='RESEARCH_ONLY_NOT_PROMOTED'
    assert selection['config']['production_activation_allowed'] is False
    assert selection['config']['event_threshold_mm']==20
    assert selection['config']['train_years']==[2021,2022,2023]
    assert selection['config']['calibration_years']==[2024]
    assert selection['config']['selection_years']==[2025]
    for filename,checksum in read_json(out/'artifact_hashes.json').items():
        assert file_hash(out/filename)==checksum
    assert [r['lead_days'] for r in report['by_lead']]==[1,2,3,4,5]
    for row,choice in zip(report['by_lead'],selection['by_lead']):
        for filename,checksum in choice['artifact_hashes'].items():
            assert file_hash(model_dir/filename)==checksum
        scores=choice['event_validation'];eligible=[k for k,v in scores.items() if v['constraints_met']]
        winner=max(eligible or list(scores),key=lambda k:(scores[k]['csi'] or 0,scores[k]['precision'] or 0))
        assert winner==row['selected_event']==choice['selected_event']
        assert choice['event_joint_target_met']==bool(eligible)
        with np.load(out/f'lead-{row["lead_days"]}-predictions.npz',allow_pickle=False) as data:
            y=data['observed'];alert=data['alert'];raw=data['raw_amount']
            assert np.isfinite(y).all() and np.isfinite(raw).all() and (y>=0).all()
            assert len(y)==row['n'] and all(d.startswith('2026-') for d in data['date'])
            assert len(set(zip(data['date'],data['grid_id'])))==len(y)
            assert len(np.unique(data['grid_id']))==22
            assert len(np.unique(data['init']))==row['initializations']
            assert event_metrics(y>=20,alert)==row['event']
            assert event_metrics(y>=20,raw>=20)==row['raw_event']
            assert amount_metrics(y,data['corrected_amount'])==row['amount']
            assert amount_metrics(y,raw)==row['raw_amount']
            assert (data['corrected_amount']>=0).all()
            if winner=='raw_gfs': expected=raw>=20
            else:
                probability=data['weather_probability' if winner=='weather_classifier' else 'rain_only_probability']
                assert np.isfinite(probability).all() and ((probability>=0)&(probability<=1)).all()
                expected=probability>=choice['event_candidates'][winner]['selection']['threshold']
            np.testing.assert_array_equal(alert,expected)
            assert row['joint_50_50_met']==(row['event']['recall']>=.5 and row['event']['precision']>=.5)
            for interval in row['event_intervals_95'].values():
                assert 0<=interval[0]<=interval[1]<=1
