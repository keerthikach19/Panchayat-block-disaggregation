"""Build immutable outputs, optionally activating after review."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.services.forecast_service import build_demo

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--district", choices=["Nashik"], default="Nashik")
    p.add_argument("--dataset-version", required=True)
    p.add_argument("--activate", action="store_true")
    p.add_argument("--accept-warnings", action="store_true")
    p.add_argument("--method", choices=["baseline", "terrain"], default="terrain")
    a = p.parse_args()
    print(json.dumps(build_demo(dataset_version=a.dataset_version, activate=a.activate, accept_warnings=a.accept_warnings, method=a.method), indent=2))
