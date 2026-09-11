from datetime import date
from pathlib import Path
from unittest.mock import Mock
import shutil
import pytest
from src.ingestion.forecast_schema import ROOT, read_json, file_hash, atomic_json
from src.ingestion.block_csv import import_collection
from src.services.forecast_service import ForecastService, ImportedBlockForecastProvider, build_demo, compatible, MODEL
from src.geography.registry import Registry

def test_packaged_offline_parent_date_and_filters(monkeypatch):
    monkeypatch.setattr("src.ingestion.imd_live.IMDLiveData.fetch_forecast", Mock(side_effect=AssertionError("External source called")))
    s=ForecastService()
    baseline = next(r["run_id"] for r in s.block.list_runs() if r["model_version"] == MODEL["model_version"])
    before=s.forecast(run_id=baseline,valid_date="2026-09-11",today=date(2026,9,20))
    assert before["freshness"]=="archived"
    assert len(before["data"])==1916
    assert len({r["panchayat_id"] for r in before["data"]})==1916
    ig=s.forecast(run_id=baseline,block="Igatpuri",valid_date="2026-09-13")
    ni=s.forecast(run_id=baseline,block="Niphad",valid_date="2026-09-13")
    assert {r["rainfall_mm"] for r in ig["data"]}=={38.2}
    assert {r["rainfall_mm"] for r in ni["data"]}!={38.2}
    assert all(r["rainfall_mm"]==r["source"]["rainfall_mm"]==r["local_rainfall_mm"] for r in before["data"])
    assert s.forecast(run_id=baseline,valid_date="2026-09-11",today=date(2026,9,20))==before
    for kwargs in [{"district":"Unknown"},{"district":"Pune"},{"block":"Central"},{"block":"Unknown"},{"mode":"x"},{"valid_date":"2030-01-01"},{"run_id":"../invalid"}]:
        with pytest.raises(ValueError):
            s.forecast(**kwargs)

def test_injected_clock_default():
    s=ForecastService()
    assert s.forecast(today=date(2026,9,13))["valid_date"]=="2026-09-13"
    assert s.forecast(today=date(2026,9,20))["valid_date"]=="2026-09-11"
    assert s.forecast(today=date(2026,9,10))["freshness"]=="upcoming"

def test_geography_missing_and_explanation():
    s=ForecastService()
    g=s.geojson()
    missing=[f for f in g["features"] if not f["properties"]["available"]]
    assert len(missing)==37
    assert all(f["properties"]["local_rainfall_mm"] is None for f in missing)
    r=s.forecast()["data"][0]
    e=s.explanation(r["panchayat_id"],run_id=r["run_id"],valid_date=r["valid_date"])
    assert e["advisory"]["run_id"]==e["run_id"]
    assert e["advisory"]["valid_date"]==e["valid_date"]
    assert e["advisory"]["status"]=="preview_only"

def test_model_metadata_rejected():
    with pytest.raises(ValueError):
        compatible({**MODEL,"training_input_level":"district"},"block")

def test_partial_inputs_and_isolation(tmp_path):
    shutil.copytree(ROOT/"config",tmp_path/"config")
    (tmp_path/"data/boundaries").mkdir(parents=True)
    shutil.copy(ROOT/"data/panchayat_covariates.csv",tmp_path/"data/panchayat_covariates.csv")
    shutil.copy(ROOT/"data/boundaries/nashik_panchayats_covariates.geojson",tmp_path/"data/boundaries/nashik_panchayats_covariates.geojson")
    folder=tmp_path/"inputs"; folder.mkdir()
    for name in ["Nashik_Igatpuri_2026-09-10.csv","Nashik_Niphad_2026-09-10 - Sheet1.csv"]:
        shutil.copy(ROOT/"Block-level data"/name,folder/name)
    m,_=import_collection(folder,tmp_path)
    first=build_demo(tmp_path,m["dataset_version"],activate=True,accept_warnings=True)[0]
    s=ForecastService(tmp_path)
    f=s.forecast(valid_date="2026-09-11")
    assert f["coverage"]["available_blocks"]==2
    assert len(f["coverage"]["missing_blocks"])==13
    ig=[r for r in f["data"] if r["block_name"]=="Igatpuri"]
    file=folder/"Nashik_Niphad_2026-09-10 - Sheet1.csv"
    file.write_text(file.read_text(encoding="utf-8-sig").replace("Rainfall (mm),","Rainfall (mm),",1).replace("RH Max. (%)","RH Max. (%)"),encoding="utf-8-sig")
    # Change only Niphad rainfall while retaining valid row shape.
    import csv,io
    rows=list(csv.reader(file.read_text(encoding="utf-8-sig").splitlines()))
    rows[2][1]="77"
    out=io.StringIO();csv.writer(out).writerows(rows);file.write_text(out.getvalue(),encoding="utf-8")
    m2,_=import_collection(folder,tmp_path)
    second=build_demo(tmp_path,m2["dataset_version"],activate=True,accept_warnings=True)[0]
    after=ForecastService(tmp_path).forecast(valid_date="2026-09-11")
    assert [r["rainfall_mm"] for r in after["data"] if r["block_name"]=="Igatpuri"]==[r["rainfall_mm"] for r in ig]
    assert first["run_id"]!=second["run_id"]
    assert len(ForecastService(tmp_path).block.list_runs())==2
    assert ForecastService(tmp_path).forecast(run_id=first["run_id"],valid_date="2026-09-11")==f

def test_corrupt_packaged_run_rejected(tmp_path):
    shutil.copytree(ROOT/"config", tmp_path/"config")
    shutil.copytree(ROOT/"data/imported", tmp_path/"data/imported")
    if (ROOT/"data/models/terrain_proxy").exists():
        shutil.copytree(ROOT/"data/models/terrain_proxy", tmp_path/"data/models/terrain_proxy")
    s=ForecastService()
    run=s.block.active()["default_run_id"]
    source=ROOT/"data/derived/forecasts"/run
    target=tmp_path/"data/derived/forecasts"/run
    shutil.copytree(source,target)
    manifest=read_json(target/"manifest.json")
    manifest["outputs_checksum"]="wrong"
    atomic_json(target/"manifest.json",manifest)
    with pytest.raises(ValueError,match="checksum"):
        ImportedBlockForecastProvider(tmp_path).load(run)
