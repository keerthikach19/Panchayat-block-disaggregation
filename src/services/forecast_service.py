"""Versioned providers, offline preprocessing and provenance-preserving reads."""
import copy
import os
from functools import lru_cache
from pathlib import Path
from src.geography.registry import Registry
from src.ingestion.forecast_schema import (
    ROOT, WEATHER_FIELDS, digest, file_hash, read_json, immutable_json, atomic_json,
    safe_id, select_date, freshness,
)
from src.ingestion.imd_live import IMDLiveData, LiveDataUnavailable
from src.modeling.terrain_model import load_terrain_model

MODEL = {"model_version": "parent-inheritance-v1", "training_input_level": "not_trained",
         "compatible_input_levels": ["block", "district"], "target_definition": "unchanged parent forecast",
         "feature_schema_version": "weather-v1", "training_data_version": None,
         "training_period": None, "validation_report_id": None,
         "status": "Baseline only; no supported local adjustment or independent skill evaluation",
         "uncertainty": "omitted; not calibrated"}

def compatible(model, level, root=ROOT):
    expected = MODEL if model.get("model_version") == MODEL["model_version"] else load_terrain_model(root, model.get("model_version"))[0]
    if model != expected or level not in model["compatible_input_levels"]:
        raise ValueError("Incompatible model metadata/artifact")
    return model

def local_record(place, source, mode, model=MODEL, terrain=None):
    values = {k: source.get(k) for k in WEATHER_FIELDS}
    status = {k: ("inherited " + mode + " forecast" if values[k] is not None else "unavailable") for k in WEATHER_FIELDS}
    details = None
    if source.get("cloud_description"):
        values["cloud_description"] = source["cloud_description"]
        status["cloud_description"] = "inherited " + mode + " forecast"
    if terrain is not None:
        factor = terrain["rainfall_factor" if mode == "block" else "district_rainfall_factor"]
        delta = terrain["temperature_adjustment_c" if mode == "block" else "district_temperature_adjustment_c"]
        values["rainfall_mm"] = round(source["rainfall_mm"] * factor, 4)
        for key in ("temp_max_c", "temp_min_c"):
            if values[key] is not None:
                values[key] = round(values[key] + delta, 2)
                status[key] = "experimental DEM lapse-rate adjustment"
        status["rainfall_mm"] = "experimental proxy-climatology transfer; local skill unverified"
        details = {"rainfall_factor": factor, "temperature_adjustment_c": delta,
                   "village_elevation_m": terrain["elevation_m"], "area_m2": terrain["area_m2"],
                   "block_reference_elevation_m": terrain["block_reference_elevation_m"],
                   "dem_pixel_count": terrain["dem_pixel_count"]}
        if mode == "district":
            details["parent_reference_elevation_m"] = terrain["elevation_m"] + delta / 0.0065
    return {**place, "mode": mode, "input_level": mode, "source": source,
            "source_rainfall_mm": source["rainfall_mm"], **values,
            "local_rainfall_mm": values["rainfall_mm"], "adjustment_mm": round(values["rainfall_mm"] - source["rainfall_mm"],4),
            "variable_status": status, "adjustment_details": details,
            "method": model["model_version"]}

def build_demo(root=ROOT, dataset_version=None, activate=False, accept_warnings=False, method="baseline"):
    registry = Registry(root)
    folder = root / "data/imported/block_forecasts/nashik" / safe_id(dataset_version)
    source_manifest = read_json(folder / "manifest.json")
    report = read_json(folder / "import_report.json")
    sources = read_json(folder / "forecasts.json")
    if not source_manifest["valid"] or source_manifest["dataset_version"] != dataset_version:
        raise ValueError("Rejected/conflicting dataset cannot be built or activated")
    if digest(sources) != source_manifest["records_checksum"] or source_manifest["registry_version"] != registry.version:
        raise ValueError("Dataset checksum or registry mismatch")
    if activate and report["warnings"] and not accept_warnings:
        raise ValueError("Review import warnings, then activate with --accept-warnings")
    geojson, places, geography_report = registry.geography()
    geography_version = digest(geojson)
    model, adjustments = MODEL, None
    if method == "terrain":
        model, adjustments, _ = load_terrain_model(root)
    elif method != "baseline":
        raise ValueError("Unknown method")
    compatible(model, "block", root)
    manifests = []
    for issue in source_manifest["issue_dates"]:
        issue_sources = [s for s in sources if s["issue_date"] == issue]
        dates = sorted({s["valid_date"] for s in issue_sources})
        outputs = [local_record(p, s, "block", model, adjustments[p["panchayat_id"]] if adjustments else None)
                   for s in issue_sources for p in places if p["block_id"] == s["block_id"]]
        run_id = "block-" + digest([dataset_version, issue, model, geography_version])[:24]
        for output in outputs:
            output.update(run_id=run_id, dataset_version=dataset_version, model_version=model["model_version"],
                          issue_date=issue, valid_date=output["source"]["valid_date"])
        blocks = registry.district("Nashik")["blocks"]
        available = {s["block_id"] for s in issue_sources}
        coverage = {"available_blocks": len(available), "expected_blocks": len(blocks),
                    "missing_blocks": [b["name"] for b in blocks if b["id"] not in available],
                    "linked_villages": len({o["panchayat_id"] for o in outputs}),
                    "excluded_features": geography_report["excluded_features"],
                    "by_block": geography_report["by_block"]}
        summary = [{"block_id": s["block_id"], "block_name": s["block_name"], "valid_date": s["valid_date"],
                    "source_rainfall_mm": s["rainfall_mm"], "linked_villages": geography_report["by_block"][s["block_name"]]} for s in issue_sources]
        manifest = {"run_id": run_id, "dataset_version": dataset_version, "model_version": model["model_version"],
                    "model": model, "mode": "block", "input_level": "block", "provider": "IMD",
                    "ingestion_method": "manual_csv_import", "district": "Nashik", "issue_date": issue,
                    "valid_dates": dates, "coverage": coverage, "geography_version": geography_version,
                    "geographic_limitation": geography_report["limitation"],
                    "source_semantics": source_manifest["unresolved_semantics"],
                    "import_warnings": report["warnings"],
                    "outputs_checksum": digest(outputs), "geometry_checksum": digest(geojson)}
        out = root / "data/derived/forecasts" / run_id
        for name, value in (("panchayat_forecasts.json", outputs), ("geometry.json", geojson),
                            ("block_summary.json", summary), ("geography_report.json", geography_report), ("manifest.json", manifest)):
            immutable_json(out / name, value)
        manifests.append(manifest)
    if activate:
        active_path = root / "data/imported/block_forecasts/nashik/active.json"
        old = read_json(active_path) if active_path.exists() else {}
        history = list(dict.fromkeys(old.get("run_ids", []) + [m["run_id"] for m in manifests]))
        latest = max(manifests, key=lambda m: m["issue_date"])
        # Results are complete before the single atomic activation; prior runs stay selectable.
        atomic_json(active_path, {"dataset_version": dataset_version, "default_run_id": latest["run_id"],
                                  "run_ids": history, "previous_default_run_id": old.get("default_run_id")})
    return manifests

class ImportedBlockForecastProvider:
    def __init__(self, root=ROOT):
        self.root = root

    def active(self):
        try:
            return read_json(self.root / "data/imported/block_forecasts/nashik/active.json")
        except FileNotFoundError as exc:
            raise LiveDataUnavailable("No activated block demonstration dataset") from exc

    def list_runs(self, district="Nashik"):
        Registry(self.root).district(district)
        active = self.active()
        # Listing choices must not deserialize every archived 5-day village output.
        # The selected run still receives full checksum validation in load().
        runs = []
        for run_id in active["run_ids"]:
            meta = read_json(self.root / "data/derived/forecasts" / safe_id(run_id) / "manifest.json")
            if meta["run_id"] != run_id or meta["mode"] != "block":
                raise ValueError("Run identity mismatch")
            runs.append(meta)
        return runs

    @lru_cache(maxsize=12)
    def load(self, run_id):
        out = self.root / "data/derived/forecasts" / safe_id(run_id)
        manifest = read_json(out / "manifest.json")
        records = read_json(out / "panchayat_forecasts.json")
        geo = read_json(out / "geometry.json")
        compatible(manifest["model"], "block", self.root)
        source_folder = self.root / "data/imported/block_forecasts/nashik" / safe_id(manifest["dataset_version"])
        source_manifest = read_json(source_folder / "manifest.json")
        sources = read_json(source_folder / "forecasts.json")
        if (not source_manifest["valid"] or source_manifest["dataset_version"] != manifest["dataset_version"]
                or source_manifest["registry_version"] != Registry(self.root).version
                or digest(sources) != source_manifest["records_checksum"]):
            raise ValueError("Imported dataset/registry checksum or version mismatch")
        if manifest["mode"] != "block" or manifest["run_id"] != run_id:
            raise ValueError("Run identity mismatch")
        if digest(records) != manifest["outputs_checksum"] or digest(geo) != manifest["geometry_checksum"]:
            raise ValueError("Precomputed output/geometry checksum mismatch")
        if any(r["run_id"] != run_id or r["dataset_version"] != manifest["dataset_version"] or
               r["model_version"] != manifest["model_version"] for r in records):
            raise ValueError("Record version mismatch")
        return manifest, records, geo

    def get_forecasts(self, district="Nashik", run_id=None, valid_date=None, today=None):
        Registry(self.root).district(district)
        active = self.active()
        run_id = run_id or active["default_run_id"]
        if run_id not in active["run_ids"]:
            raise ValueError("Unknown block run")
        meta, records, geo = self.load(run_id)
        if run_id == active["default_run_id"] and meta["dataset_version"] != active["dataset_version"]:
            raise ValueError("Active pointer and default run dataset mismatch")
        selected = select_date(meta["valid_dates"], valid_date, today)
        selected_records = [r for r in records if r["valid_date"] == selected]
        available = {r["block_id"] for r in selected_records}
        blocks = Registry(self.root).district(district)["blocks"]
        coverage = {**meta["coverage"], "available_blocks": len(available),
                    "missing_blocks": [b["name"] for b in blocks if b["id"] not in available],
                    "linked_villages": len(selected_records)}
        return {**meta, "valid_date": selected, "freshness": freshness(meta["valid_dates"], today),
                "cache_status": "packaged", "coverage": coverage, "data": selected_records}, geo

class LiveDistrictForecastProvider:
    def __init__(self, root=ROOT, live=None):
        self.root = root
        cache = Path(os.environ.get("DISTRICT_CACHE_DIR", str(root / "data/cache/district_forecasts")))
        self.live = live or IMDLiveData(cache_dir=cache)
        self.runs = {}

    def get_forecasts(self, district="Nashik", run_id=None, valid_date=None, today=None):
        registry = Registry(self.root)
        d = registry.district(district)
        if run_id:
            if run_id not in self.runs:
                raise ValueError("District run expired from process memory; fetch the district again")
            forecast, model_version = self.runs[run_id]
        else:
            forecast = self.live.fetch_forecast(d["name"])
            model_version = None
        days = forecast["forecast_days"]
        dates = [day["date"] for day in days]
        selected = select_date(dates, valid_date, today)
        # Independent of block data: a missing experimental artifact explicitly
        # selects the untrained parent baseline, never a district-trained pickle.
        if model_version == MODEL["model_version"]:
            model, adjustments = MODEL, None
        elif model_version or (self.root / "data/models/terrain_proxy/active.json").exists():
            model, adjustments, _ = load_terrain_model(self.root, model_version)
        else:
            model, adjustments = MODEL, None
        compatible(model, "district", self.root)
        geo, places, geo_report = registry.geography(district)
        dataset_version = "district-" + digest([forecast.get("issued_date"), forecast.get("source_url"), days])[:20]
        actual_id = "district-" + digest([dataset_version, model, digest(geo)])[:24]
        if run_id and actual_id != run_id:
            raise ValueError("District run identity changed")
        self.runs[actual_id] = (forecast, model["model_version"])
        if len(self.runs) > 24:
            self.runs.pop(next(iter(self.runs)))
        day = next(x for x in days if x["date"] == selected)
        source = {**{k: day.get(k) for k in WEATHER_FIELDS}, "issue_date": forecast.get("issued_date"),
                  "cloud_description": day.get("cloud_description"),
                  "valid_date": selected, "source_url": forecast.get("source_url"),
                  "provider": "IMD", "input_level": "district", "ingestion_method": "live_district_bulletin",
                  "district_id": d["id"], "dataset_version": dataset_version}
        records = [{**local_record(p, source, "district", model, adjustments[p["panchayat_id"]] if adjustments else None), "run_id": actual_id, "dataset_version": dataset_version,
                    "model_version": model["model_version"], "issue_date": forecast.get("issued_date"), "valid_date": selected} for p in places]
        return {"mode": "district", "input_level": "district", "provider": "IMD",
                "ingestion_method": "live_district_bulletin", "district": d["name"], "run_id": actual_id,
                "dataset_version": dataset_version, "model_version": model["model_version"], "model": model,
                "issue_date": forecast.get("issued_date"), "valid_date": selected, "valid_dates": dates,
                "freshness": freshness(dates, today), "cache_status": forecast.get("cache_status"),
                "downloaded_at": forecast.get("fetched_at"), "last_retrieval_error": forecast.get("live_error"),
                "source_url": forecast.get("source_url"), "geographic_limitation": geo_report["limitation"],
                "coverage": {"available_blocks": len(d["blocks"]), "expected_blocks": len(d["blocks"]),
                             "missing_blocks": [], "linked_villages": len(places), "excluded_features": geo_report["excluded_features"]},
                "data": records}, geo

class ForecastService:
    def __init__(self, root=ROOT, live=None):
        self.registry = Registry(root)
        self.block = ImportedBlockForecastProvider(root)
        self.district = LiveDistrictForecastProvider(root, live)

    def forecast(self, mode="block", district="Nashik", run_id=None, valid_date=None, block=None, today=None):
        self.registry.district(district)
        if mode not in ("block", "district"):
            raise ValueError("Mode must be block or district")
        provider = self.block if mode == "block" else self.district
        response, _ = provider.get_forecasts(district, run_id, valid_date, today)
        if not response["data"]:
            raise ValueError("No linked forecasts for the selected source and date")
        if block:
            b = self.registry.block(district, block)
            response["data"] = [r for r in response["data"] if r["block_id"] == b["id"]]
            if not response["data"]:
                raise ValueError(f"No forecasts available for {b['name']}")
        return response

    def geojson(self, **params):
        forecast = self.forecast(**params)
        provider = self.block if forecast["mode"] == "block" else self.district
        _, geo = provider.get_forecasts(forecast["district"], forecast["run_id"], forecast["valid_date"])
        geo = copy.deepcopy(geo)
        by_id = {r["panchayat_id"]: r for r in forecast["data"]}
        requested_block = self.registry.block(params.get("district", "Nashik"), params["block"])["id"] if params.get("block") else None
        features = []
        for f in geo["features"]:
            p = f["properties"]
            if requested_block and p["block_id"] != requested_block:
                continue
            row = by_id.get(p["panchayat_id"]) if p["available"] else None
            if row:
                for field in (*WEATHER_FIELDS, "cloud_description"):
                    p["source_" + field] = row["source"].get(field)
                    p["local_" + field] = row.get(field)
            else:
                p.update(available=False, source_rainfall_mm=None, local_rainfall_mm=None,
                         unavailable_reason=p.get("unavailable_reason") or "Parent block forecast missing")
            features.append(f)
        return {"type": "FeatureCollection", "features": features,
                "metadata": {k: v for k, v in forecast.items() if k != "data"}}

    def explanation(self, panchayat_id, **params):
        forecast = self.forecast(**params)
        row = next((r for r in forecast["data"] if r["panchayat_id"] == panchayat_id), None)
        if row is None:
            raise ValueError("Village is unavailable for this run/date/filter")
        return {**row, "freshness": forecast["freshness"], "model": forecast["model"],
                "advisory": advisory(row, forecast["freshness"])}

def advisory(row, status):
    """Transparent weather-triggered preview, no unsupported crop/pest certainty."""
    rain = row["rainfall_mm"]
    humidity = row.get("relative_humidity_max_pct")
    messages = []
    if rain >= 20:
        messages.append("Forecast rain may interrupt spraying; review field drainage and the spray window.")
    elif rain > 0:
        messages.append("Check local rainfall and soil moisture before irrigation or spraying.")
    else:
        messages.append("No rain is forecast by the parent source; check soil moisture before deciding irrigation.")
    if humidity is not None and humidity >= 90:
        messages.append("High source humidity: inspect crops for moisture-related disease symptoms.")
    if humidity is None:
        messages.append("Humidity is unavailable; no humidity-dependent advisory was generated.")
    data = {"mode": row["mode"], "run_id": row["run_id"], "panchayat_id": row["panchayat_id"],
            "valid_date": row["valid_date"], "text": " ".join(messages), "historical": status == "archived",
            "status": "preview_only", "variables": row["variable_status"], "rule_version": "weather-preview-v1",
            "method_status": "experimental" if row.get("adjustment_details") else "parent_baseline"}
    return {**data, "advisory_id": digest(data)[:24]}
