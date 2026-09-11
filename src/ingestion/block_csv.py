"""Strict manually exported IMD block table importer. Never accesses the network."""
import csv
import io
import math
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from src.geography.registry import Registry
from src.ingestion.forecast_schema import ROOT, WEATHER_FIELDS, digest, file_hash, immutable_json, read_json

FILENAME = re.compile(r"^(?P<district>Nashik)_(?P<block>.+)_(?P<issue>\d{4}-\d{2}-\d{2})(?: - Sheet1)?\.csv$", re.I)
TITLE = re.compile(r"^(.+?)\s*:\s*Block Forecast issued on\s+(\d{2}-\d{2}-\d{4})$", re.I)
def label(value):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value).replace("º", "°")).casefold()

LABELS = dict(zip(map(label, ["Rainfall (mm)", "Max. Temp. (℃)", "Min. Temp. (℃)",
    "Cloud Cover (octa)", "RH Max. (%)", "RH Min. (%)", "Windspeed(kmph)", "Wind Dir.(Deg)"]), WEATHER_FIELDS))
LABELS.update({label("Max. Temp. (?)"): "temp_max_c", label("Min. Temp. (?)"): "temp_min_c"})

def parse_file(path, registry=None):
    registry = registry or Registry()
    path = Path(path)
    match = FILENAME.fullmatch(path.name.strip())
    if not match:
        raise ValueError("Unsupported filename")
    district = registry.district(match["district"])
    block = registry.block(district["name"], match["block"])
    issue = datetime.strptime(match["issue"], "%Y-%m-%d").date().isoformat()
    rows = list(csv.reader(io.StringIO(path.read_bytes().decode("utf-8-sig"))))
    titles = [TITLE.fullmatch(r[0].strip()) for r in rows if r]
    titles = [t for t in titles if t]
    if len(titles) != 1:
        raise ValueError("Missing or duplicate title")
    title = titles[0]
    if registry.block(district["name"], title[1]) != block:
        raise ValueError("Filename/title block disagreement")
    if datetime.strptime(title[2], "%d-%m-%Y").date().isoformat() != issue:
        raise ValueError("Filename/title issue-date disagreement")
    date_rows = [r for r in rows if r and label(r[0]) == "date"]
    if len(date_rows) != 1 or len(date_rows[0]) != 7 or label(date_rows[0][-1]) != "total/average":
        raise ValueError("Expected five dates and a separate Total / Average column")
    dates = [datetime.strptime(v.strip(), "%d-%m-%Y").date().isoformat() for v in date_rows[0][1:6]]
    if len(set(dates)) != 5 or dates != sorted(dates):
        raise ValueError("Missing, duplicate or unordered dates")
    values, warnings = {}, []
    for row in rows:
        key = LABELS.get(label(row[0])) if row else None
        if not key:
            continue
        if key in values or len(row) != 7:
            raise ValueError(f"Duplicate or incomplete variable row: {key}")
        if "(?)" in label(row[0]):
            warnings.append(f"{key}: unreadable source unit '?'; interpreted as Celsius from the IMD table schema, pending owner verification")
        try:
            daily = [float(v.strip()) for v in row[1:6]]
        except ValueError:
            raise ValueError(f"Non-numeric daily values: {key}")
        if not all(math.isfinite(v) for v in daily):
            raise ValueError(f"Non-finite values: {key}")
        values[key] = daily
        if key != "wind_direction_deg":
            expected = sum(daily) if key == "rainfall_mm" else sum(daily)/5
            try:
                reported = float(row[6])
                tolerance = 0.55 if key in ("rainfall_mm", "relative_humidity_max_pct", "relative_humidity_min_pct", "cloud_cover_oktas") else 0.11
                if not math.isfinite(reported) or abs(expected - reported) > tolerance:
                    warnings.append(f"{key}: summary {row[6]} differs from calculated {expected:.2f}")
            except ValueError:
                if key != "cloud_cover_oktas":
                    warnings.append(f"{key}: summary not numeric")
    if set(values) != set(WEATHER_FIELDS):
        raise ValueError(f"Missing required rows: {sorted(set(WEATHER_FIELDS)-set(values))}")
    records = []
    for i, valid in enumerate(dates):
        v = {key: values[key][i] for key in WEATHER_FIELDS}
        if v["rainfall_mm"] < 0 or v["wind_speed_kmph"] < 0:
            raise ValueError("Negative rainfall or wind speed")
        if not 0 <= v["cloud_cover_oktas"] <= 8 or not 0 <= v["wind_direction_deg"] <= 360:
            raise ValueError("Cloud cover or wind direction out of range")
        if not 0 <= v["relative_humidity_min_pct"] <= v["relative_humidity_max_pct"] <= 100:
            raise ValueError("Humidity out of range or min above max")
        if v["temp_min_c"] > v["temp_max_c"]:
            raise ValueError("Minimum temperature above maximum")
        if v["rainfall_mm"] > 500 or v["temp_min_c"] < -20 or v["temp_max_c"] > 55 or v["wind_speed_kmph"] > 150:
            warnings.append(f"{valid}: unusual physical values require review")
        if valid <= issue:
            warnings.append(f"{valid}: valid date is on or before issue date")
        records.append({"district_id": district["id"], "district_name": district["name"],
                        "block_id": block["id"], "block_name": block["name"],
                        "source_block_name": title[1], "issue_date": issue, "valid_date": valid,
                        "timezone": "Asia/Kolkata", **v, "provider": "IMD", "input_level": "block",
                        "ingestion_method": "manual_csv_import", "source_filename": path.name,
                        "source_sha256": file_hash(path)})
    return records, warnings

def import_collection(input_dir, root=ROOT, district="Nashik"):
    registry = Registry(root)
    d = registry.district(district)
    paths = sorted(p for p in Path(input_dir).iterdir() if p.is_file() and p.suffix.lower() == ".csv")
    if not paths:
        raise ValueError("No CSV inputs found")
    sources = [{"filename": p.name, "sha256": file_hash(p)} for p in paths]
    version = "imd-" + digest({"sources": sources, "registry": registry.version, "schema": "block-csv-v2"})[:20]
    folder = root / "data/imported/block_forecasts/nashik" / version
    if (folder / "manifest.json").exists():
        return read_json(folder / "manifest.json"), read_json(folder / "import_report.json")
    report = {"accepted_files": [], "rejected_files": [], "duplicate_files": [], "conflicts": [],
              "warnings": [], "alias_resolutions": [], "dataset_version": version}
    groups = {}
    now = datetime.now(timezone.utc).isoformat()
    for path in paths:
        try:
            records, warnings = parse_file(path, registry)
            key = (records[0]["block_id"], records[0]["issue_date"])
            comparison = [{k: r[k] for k in (*WEATHER_FIELDS, "valid_date")} for r in records]
            if key in groups:
                previous, data = groups[key]
                if comparison != data:
                    report["conflicts"].append({"files": [previous[0]["source_filename"], path.name]})
                else:
                    report["duplicate_files"].append(path.name)
                    for r in previous:
                        r["sources"].append({"filename": path.name, "sha256": file_hash(path)})
            else:
                for r in records:
                    r.update(dataset_version=version, imported_at=now, sources=[{"filename": path.name, "sha256": r["source_sha256"]}])
                groups[key] = (records, comparison)
            report["accepted_files"].append(path.name)
            report["warnings"].extend({"file": path.name, "message": w} for w in warnings)
            report["alias_resolutions"].append({"filename": path.name, "source_name": records[0]["source_block_name"], "canonical": records[0]["block_name"]})
        except (ValueError, UnicodeError) as exc:
            report["rejected_files"].append({"file": path.name, "error": str(exc)})
    records = [r for key in sorted(groups) for r in groups[key][0]]
    issues = sorted({r["issue_date"] for r in records})
    report["issue_dates"] = issues
    report["blocks"] = sorted({r["block_name"] for r in records})
    report["missing_blocks_by_issue"] = {issue: sorted({b["name"] for b in d["blocks"]} - {r["block_name"] for r in records if r["issue_date"] == issue}) for issue in issues}
    manifest = {"dataset_version": version, "schema_version": "block-csv-v2", "registry_version": registry.version,
                "district": d["name"], "imported_at": now, "sources": sources, "issue_dates": issues,
                "valid_dates": sorted({r["valid_date"] for r in records}), "record_count": len(records),
                "records_checksum": digest(records), "valid": bool(records) and not report["rejected_files"] and not report["conflicts"],
                "unresolved_semantics": ["Issue time unavailable; date only.", "Rainfall accumulation interval undocumented.",
                    "Published block forecast spatial interpretation unverified; no area-mean assumption or redistribution.",
                    "Manual export provenance is retained; provider authenticity is not cryptographically verified."]}
    for name, value in (("forecasts.json", records), ("import_report.json", report), ("manifest.json", manifest)):
        immutable_json(folder / name, value)
    return manifest, report
