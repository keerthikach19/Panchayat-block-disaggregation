import json
import shutil
from unittest.mock import Mock
from src.ingestion.forecast_schema import ROOT
from src.services.forecast_service import ForecastService, local_record
from src.modeling.terrain_model import load_terrain_model

def test_terrain_outputs_vary_and_preserve_parent_mass():
    s=ForecastService()
    meta, adjustments, report=load_terrain_model()
    assert report["source_audit"]["nashik_profile_groups"]==5
    assert report["selected_candidate"]=="ridge"
    assert report["test"]["selected_rmse_mm_per_day"]<report["test"]["unchanged_regional_mean_rmse_mm_per_day"]
    for date in ["2026-09-11","2026-09-12","2026-09-13","2026-09-14","2026-09-15"]:
        data=s.forecast(valid_date=date)["data"]
        for block in {r["block_id"] for r in data}:
            rows=[r for r in data if r["block_id"]==block]
            weights=[adjustments[r["panchayat_id"]]["area_m2"] for r in rows]
            source=rows[0]["source_rainfall_mm"]
            weighted=sum(r["local_rainfall_mm"]*w for r,w in zip(rows,weights))/sum(weights)
            assert abs(weighted-source)<0.0001
            assert all(r["temp_min_c"]<=r["temp_max_c"] for r in rows)
            if source>0:
                assert len({r["local_rainfall_mm"] for r in rows})>1
        for r in data:
            assert r["source"]["input_level"]=="block"
            assert r["rainfall_mm"]==r["local_rainfall_mm"]
            for key in ("relative_humidity_max_pct","relative_humidity_min_pct","cloud_cover_oktas","wind_speed_kmph","wind_direction_deg"):
                assert r[key]==r["source"][key]
    assert any(r["temp_max_c"]!=r["source"]["temp_max_c"] for r in data)

def test_zero_input_does_not_create_rain_and_records_independent():
    meta,adjustments,_=load_terrain_model()
    row=ForecastService().forecast()["data"][0]
    place={k:row[k] for k in ("panchayat_id","block_id","block_name")}
    zero={**row["source"],"rainfall_mm":0}
    result=local_record(place,zero,"block",meta,adjustments[row["panchayat_id"]])
    assert result["local_rainfall_mm"]==0
    assert result["source"]["rainfall_mm"]==0
    doubled={**row["source"],"rainfall_mm":row["source_rainfall_mm"]*2}
    result2=local_record(place,doubled,"block",meta,adjustments[row["panchayat_id"]])
    assert abs(result2["local_rainfall_mm"]-2*row["local_rainfall_mm"])<0.0002
    assert row["source"]["rainfall_mm"]!=doubled["rainfall_mm"] or row["source_rainfall_mm"]==0


def test_model_activation_refreshes_new_runs_and_preserves_existing_run(tmp_path):
    shutil.copytree(ROOT/"config", tmp_path/"config")
    shutil.copytree(ROOT/"data/models/terrain_proxy", tmp_path/"data/models/terrain_proxy")
    (tmp_path/"data/boundaries").mkdir()
    shutil.copy(ROOT/"data/panchayat_covariates.csv", tmp_path/"data/panchayat_covariates.csv")
    shutil.copy(ROOT/"data/boundaries/nashik_panchayats_covariates.geojson", tmp_path/"data/boundaries/nashik_panchayats_covariates.geojson")
    old_model=load_terrain_model(tmp_path)[0]["model_version"]
    other_model=next(p.name for p in (tmp_path/"data/models/terrain_proxy").iterdir() if p.is_dir() and p.name!=old_model)
    live=Mock()
    live.fetch_forecast.return_value={"issued_date":"2026-09-10", "source_url":"https://imdagrimet.gov.in/example.pdf",
        "forecast_days":[{"date":"2026-09-11", "rainfall_mm":12.0}, {"date":"2026-09-12", "rainfall_mm":6.0}]}
    service=ForecastService(tmp_path, live)
    original=service.forecast(mode="district", valid_date="2026-09-11")
    (tmp_path/"data/models/terrain_proxy/active.json").write_text(json.dumps({"model_version":other_model}))
    assert load_terrain_model(tmp_path)[0]["model_version"]==other_model
    retained=service.forecast(mode="district", run_id=original["run_id"], valid_date="2026-09-12")
    assert retained["model_version"]==old_model
    assert retained["run_id"]==original["run_id"]
    current=service.forecast(mode="district", valid_date="2026-09-11")
    assert current["model_version"]==other_model
    assert current["run_id"]!=original["run_id"]
