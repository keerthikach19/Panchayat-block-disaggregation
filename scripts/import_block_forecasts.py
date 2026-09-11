"""Operator-only CSV validation/import. Does not activate data."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ingestion.block_csv import import_collection

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir", type=Path, default=Path("Block-level data"))
    p.add_argument("--district", default="Nashik", choices=["Nashik"])
    a = p.parse_args()
    manifest, report = import_collection(a.input_dir, district=a.district)
    print(json.dumps({"manifest": manifest, "report": report}, indent=2))
    raise SystemExit(0 if manifest["valid"] else 1)
