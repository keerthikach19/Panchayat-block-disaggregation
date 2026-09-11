"""Operator-only refresh of the independent district source cache."""
import argparse
import os
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ingestion.forecast_schema import ROOT
from src.ingestion.imd_live import IMDLiveData
if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--district",choices=["Nashik"],default="Nashik")
    a=p.parse_args()
    cache=Path(os.environ.get("DISTRICT_CACHE_DIR",str(ROOT/"data/cache/district_forecasts")))
    print(json.dumps(IMDLiveData(cache_dir=cache).fetch_forecast(a.district,force_refresh=True),indent=2))
