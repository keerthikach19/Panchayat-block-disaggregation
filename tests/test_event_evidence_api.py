from fastapi.testclient import TestClient
from src.api import main
from src.ingestion.forecast_schema import atomic_json


def test_evidence_pointer_adds_research_report_without_changing_original(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'ROOT', tmp_path)
    base = tmp_path/'data/research/benchmarks'
    original = {'experiment_id': 'original', 'by_lead': []}
    atomic_json(base/'rain-benchmark-ad798db16fc9a58f9dc1/report.json', original)
    client = TestClient(main.app)
    assert client.get('/api/model-evidence').json() == original
    revised = {'experiment_id': 'rain-events-fixture', 'status': 'RESEARCH_ONLY_NOT_PROMOTED'}
    atomic_json(base/'rain-events-fixture/report.json', revised)
    atomic_json(base/'event_evidence.json', {'experiment_id': 'rain-events-fixture'})
    assert client.get('/api/model-evidence').json() == {**original, 'revised_benchmark': revised}
    atomic_json(base/'rain-events-fixture/evaluation-fixture/report.json', {**revised, 'evaluation_id': 'evaluation-fixture'})
    atomic_json(base/'event_evidence.json', {'experiment_id': 'rain-events-fixture', 'evaluation_id': 'evaluation-fixture'})
    assert client.get('/api/model-evidence').json()['revised_benchmark']['evaluation_id'] == 'evaluation-fixture'
    atomic_json(base/'event_evidence.json', {'experiment_id': 'rain-events-fixture', 'evaluation_id': '../../outside'})
    assert client.get('/api/model-evidence').status_code == 422
    atomic_json(base/'event_evidence.json', {'experiment_id': '../../outside'})
    assert client.get('/api/model-evidence').status_code == 422


def test_nwp_evidence_is_optional_and_identity_checked(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'ROOT', tmp_path)
    base = tmp_path/'data/research/benchmarks'
    original = {'experiment_id': 'original', 'by_lead': []}
    atomic_json(base/'rain-benchmark-ad798db16fc9a58f9dc1/report.json', original)
    pointer = {'experiment_id': 'nwp-fixture', 'evaluation_id': 'evaluation-fixture'}
    report = {**pointer, 'status': 'RESEARCH_ONLY_NOT_PROMOTED', 'by_lead': []}
    atomic_json(base/'nwp_evidence.json', pointer)
    atomic_json(base/'nwp-fixture/evaluation-fixture/report.json', report)
    client = TestClient(main.app)
    assert client.get('/api/model-evidence').json() == {**original, 'nwp_benchmark': report}
    atomic_json(base/'nwp-fixture/evaluation-fixture/report.json', {**report, 'evaluation_id': 'wrong'})
    assert client.get('/api/model-evidence').status_code == 422
    atomic_json(base/'nwp_evidence.json', {**pointer, 'evaluation_id': '../../outside'})
    assert client.get('/api/model-evidence').status_code == 422
    atomic_json(base/'nwp_evidence.json', {'experiment_id': '../../outside'})
    assert client.get('/api/model-evidence').status_code == 422
