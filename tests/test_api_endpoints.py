from unittest.mock import Mock
from fastapi.testclient import TestClient
from src.api.main import app, service
from src.ingestion.forecast_schema import ROOT, read_json, file_hash

def test_offline_end_to_end(monkeypatch):
    monkeypatch.setattr(service.district.live,"fetch_forecast",Mock(side_effect=AssertionError("external request")))
    c=TestClient(app)
    assert c.get("/api/health").json()["block_demo_ready"]
    run=c.get("/api/forecast/runs").json()["default_run_id"]
    q=f"mode=block&run_id={run}&valid_date=2026-09-13&block=Igatpuri"
    result=c.get("/api/forecast?"+q)
    assert result.status_code==200
    data=result.json()
    assert len(data["data"])==117
    pid=data["data"][0]["panchayat_id"]
    geo=c.get("/api/panchayats/geojson?"+q).json()
    assert geo["metadata"]["run_id"]==run
    assert {f["properties"]["source_rainfall_mm"] for f in geo["features"]}=={38.2}
    exp=c.get(f"/api/panchayat/{pid}/explainability?"+q).json()
    assert exp["advisory"]["valid_date"]=="2026-09-13"
    adv=c.get("/api/advisories?"+q).json()
    assert adv["run_id"]==run
    preview=c.post("/api/disseminate/preview",json={"panchayat_id":pid,"mode":"block","run_id":run,"valid_date":"2026-09-13"}).json()
    assert preview["sent"] is False and preview["advisory_id"]==exp["advisory"]["advisory_id"]
    assert c.get("/api/validation-metrics").json()["metrics"] is None
    assert c.get("/api/forecast?district=Pune").status_code==422
    assert c.get("/api/forecast?valid_date=2028-01-01").status_code==422
    assert c.get("/api/forecast?block=Central").status_code==422
    assert c.post("/api/advisory/x/review",json={}).status_code==404

def test_input_and_artifact_preservation():
    hashes=read_json(ROOT/"docs/baseline-input-hashes.json")
    for filename,expected in hashes.items():
        assert file_hash(ROOT/filename)==expected

def test_zero_variance_training_rejected():
    import pandas as pd
    import pytest
    from src.modeling.layer_b_deviation import FootprintDeviationModel
    with pytest.raises(ValueError,match="zero-variance"):
        FootprintDeviationModel().train_footprint_models(pd.DataFrame({"rainfall_deviation":[0.,0.],"temp_deviation":[0.,0.]}))
