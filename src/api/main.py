"""Nashik hybrid API. Primary GETs read packaged, validated data only."""
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from src.ingestion.forecast_schema import ROOT
from src.ingestion.imd_live import LiveDataUnavailable
from src.services.forecast_service import ForecastService, MODEL, advisory
from src.modeling.terrain_model import load_terrain_model
from src.services.comparison import ComparisonService
from src.services.bulletin import render_bulletin
from src.ingestion.forecast_schema import read_json, safe_id

app = FastAPI(title="Nashik hybrid weather forecasts", version="3.0.0")
service = ForecastService()
comparison_service = ComparisonService(service)

def selection(mode: Literal["block", "district"] = "block", district: str = "Nashik",
              run_id: str | None = None, valid_date: str | None = None, block: str | None = None):
    return dict(mode=mode, district=district, run_id=run_id, valid_date=valid_date, block=block)

def call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except LiveDataUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except (ValueError, FileNotFoundError, KeyError) as exc:
        raise HTTPException(422, str(exc)) from exc

@app.get("/api/health")
def health():
    try:
        active = service.block.active()
        service.block.load(active["default_run_id"])
        ready, error = True, None
    except Exception as exc:
        ready, error = False, str(exc)
    cached = service.district.live._read_cache("agromet", "Nashik")
    source = "not_checked"
    if cached:
        try:
            source = service.district.live.select_forecast(cached, cached=True)["freshness"]
        except (ValueError, KeyError):
            source = "unavailable"
    return {"application": "running", "block_demo_ready": ready, "block_error": error,
            "district_source_cache": source}

@app.get("/api/districts")
def districts():
    return {"districts": [service.registry.district("Nashik")]}

@app.get("/api/forecast/modes")
def modes():
    return {"default": "block", "modes": [{"id": "block", "label": "Official block forecasts"},
                                        {"id": "district", "label": "Live district forecast"}]}

@app.get("/api/forecast/runs")
def runs(mode: Literal["block", "district"] = "block", district: str = "Nashik"):
    call(service.registry.district, district)
    if mode == "block":
        result = call(service.block.list_runs, district)
        return {"runs": result, "default_run_id": service.block.active()["default_run_id"]}
    result = call(service.forecast, mode="district", district=district)
    return {"runs": [{k: v for k, v in result.items() if k != "data"}], "default_run_id": result["run_id"]}

@app.get("/api/blocks")
def blocks(district: str = "Nashik"):
    return {"blocks": call(service.registry.district, district)["blocks"]}

@app.get("/api/forecast")
def forecast(params=Depends(selection)):
    return call(service.forecast, **params)

@app.get("/api/comparison")
def compare(valid_date: str | None = None, block: str | None = None,
            block_run_id: str | None = None, district_run_id: str | None = None):
    return call(comparison_service.compare, valid_date, block, block_run_id, district_run_id)

@app.get("/api/panchayats/geojson")
def geojson(params=Depends(selection)):
    return call(service.geojson, **params)

@app.get("/api/panchayat/{panchayat_id}/explainability")
def explain(panchayat_id: str, params=Depends(selection)):
    return call(service.explanation, panchayat_id, **params)

@app.get("/api/advisories")
def advisories(params=Depends(selection), limit: int = Query(50, ge=1, le=2000)):
    result = call(service.forecast, **params)
    return {"mode": result["mode"], "run_id": result["run_id"], "valid_date": result["valid_date"],
            "advisories": [advisory(row, result["freshness"]) for row in result["data"][:limit]]}

@app.get("/api/validation-metrics")
def validation(model_version: str = MODEL["model_version"]):
    if model_version.startswith("terrain-"):
        meta, _, report = call(load_terrain_model, ROOT, model_version)
        return {"model_version": model_version, "status": "experimental_proxy_evaluation",
                "forecast_accuracy_metrics": None, "proxy_report": report, "model": meta,
                "message": "This is a gridded-climatology diagnostic, not independent local forecast validation."}
    if model_version != MODEL["model_version"]:
        raise HTTPException(422, "Unknown or incompatible model version")
    return {"model_version": model_version, "status": "insufficient_evidence",
            "metrics": None, "uncertainty": "not calibrated; omitted",
            "message": "Unchanged parent forecast baseline. No independent evaluation of local predictive skill. Old district metrics do not evaluate this pipeline."}

@app.get("/api/bulletin/{panchayat_id}", response_class=HTMLResponse)
def bulletin(panchayat_id: str, mode: Literal["block", "district"] = "block", run_id: str | None = None):
    return call(render_bulletin, service, panchayat_id, mode, run_id)

@app.get("/api/model-evidence")
def model_evidence():
    report = call(read_json, ROOT / "data/research/benchmarks/rain-benchmark-ad798db16fc9a58f9dc1/report.json")
    for filename, key in [('event_evidence.json', 'revised_benchmark'), ('nwp_evidence.json', 'nwp_benchmark')]:
        pointer = ROOT / 'data/research/benchmarks' / filename
        if pointer.exists():
            selected = call(read_json, pointer)
            experiment = call(safe_id, selected.get('experiment_id', ''))
            directory = ROOT / 'data/research/benchmarks' / experiment
            if selected.get('evaluation_id'):
                directory = directory / call(safe_id, selected['evaluation_id'])
            evidence = call(read_json, directory / 'report.json')
            if evidence.get('experiment_id') != experiment or evidence.get('evaluation_id') != selected.get('evaluation_id'):
                raise HTTPException(422, 'Research evidence identity mismatch')
            report[key] = evidence
    return report

class DisseminationPreviewPayload(BaseModel):
    panchayat_id: str
    mode: Literal["block", "district"]
    run_id: str
    valid_date: str
    channel: Literal["SMS", "WhatsApp", "mKisan"] = "WhatsApp"

@app.post("/api/disseminate/preview")
def preview_dissemination(payload: DisseminationPreviewPayload):
    result = call(service.explanation, payload.panchayat_id, mode=payload.mode,
                  run_id=payload.run_id, valid_date=payload.valid_date)
    adv = result["advisory"]
    prefix = "Historical forecast advisory" if adv["historical"] else "Forecast advisory preview"
    return {**adv, "channel": payload.channel, "sent": False,
            "rendered_preview": f"{prefix} | {result['panchayat_name']} | {payload.valid_date}\n{adv['text']}"}

# Explicit compatibility wrappers. Source mode remains district and date selection is exact.
@app.get("/api/forecast/{district_name}")
def get_downscaled_forecast(district_name: str, forecast_date: str | None = None):
    return call(service.forecast, mode="district", district=district_name, valid_date=forecast_date)

@app.get("/api/panchayats/geojson/{district_name}")
def legacy_geojson(district_name: str, run_id: str | None = None, forecast_date: str | None = None):
    return call(service.geojson, mode="district", district=district_name, run_id=run_id, valid_date=forecast_date)

@app.get("/api/advisories/{district_name}")
def legacy_advisories(district_name: str, run_id: str | None = None, forecast_date: str | None = None):
    result = call(service.forecast, mode="district", district=district_name, run_id=run_id, valid_date=forecast_date)
    return {"mode": "district", "run_id": result["run_id"], "valid_date": result["valid_date"],
            "advisories": [advisory(r, result["freshness"]) for r in result["data"][:50]]}

dist = ROOT / "frontend/dist"
if (dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

@app.get("/")
def index():
    if not (dist / "index.html").exists():
        raise HTTPException(503, "Frontend build is missing")
    return FileResponse(dist / "index.html")
