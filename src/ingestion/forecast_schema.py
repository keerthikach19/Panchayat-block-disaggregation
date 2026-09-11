"""Shared date, identity and immutable storage contracts."""
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
WEATHER_FIELDS = (
    "rainfall_mm", "temp_max_c", "temp_min_c", "cloud_cover_oktas",
    "relative_humidity_max_pct", "relative_humidity_min_pct",
    "wind_speed_kmph", "wind_direction_deg",
)
def today_ist():
    return datetime.now(ZoneInfo("Asia/Kolkata")).date()

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False, separators=(",", ":")).encode()).hexdigest()

def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     suffix=".tmp", delete=False) as out:
        out.write(raw)
        temp = out.name
    os.replace(temp, path)

def immutable_json(path, value):
    path = Path(path)
    if path.exists():
        if read_json(path) != value:
            raise ValueError(f"Refusing to overwrite immutable artifact: {path}")
    else:
        atomic_json(path, value)

def safe_id(value):
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", value or ""):
        raise ValueError("Invalid dataset/run identifier")
    return value

def select_date(dates, requested=None, today=None):
    if not dates:
        raise ValueError("No forecast dates available")
    if requested:
        if requested not in dates:
            raise ValueError(f"Date {requested} unavailable; choose from {dates}")
        return requested
    current = (today or today_ist()).isoformat()
    return current if current in dates else dates[0]

def freshness(dates, today=None):
    current = (today or today_ist()).isoformat()
    return "archived" if max(dates) < current else ("upcoming" if min(dates) > current else "current")

