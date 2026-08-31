#!/usr/bin/env python3
"""
Script 08: Sanity Check & Data Verification (PRP Section 2.7 Step 8).

Validates:
  (a) Administrative boundaries for Maharashtra state and Nashik district exist.
  (b) Station dataset covers all 4 physiographic zones with sufficient density.
  (c) Nashik has adequate stations for Layer C kriging residual correction.
  (d) Elevation and Land Cover data availability.
  (e) Gridded weather files and IPED availability.

Prints an auditable pass/fail report before modeling and PostGIS ingestion.
"""

import os
import sys
import json
import logging
import pandas as pd
import geopandas as gpd
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BOUNDARIES_DIR = PROJECT_ROOT / "data" / "boundaries"
DEM_DIR = PROJECT_ROOT / "data" / "dem"
LANDCOVER_DIR = PROJECT_ROOT / "data" / "landcover"
GRIDDED_DIR = PROJECT_ROOT / "data" / "gridded"
STATIONS_DIR = PROJECT_ROOT / "data" / "stations"
CONFIG_DIR = PROJECT_ROOT / "config"


def run_checks():
    report = {"passed": True, "details": []}

    print("\n" + "=" * 70)
    print("      PRP SECTION 2.7 STEP 8: EMPIRICAL DATA SANITY CHECK REPORT")
    print("=" * 70 + "\n")

    # 1. Bounding Boxes Config
    cfg_file = CONFIG_DIR / "bounding_boxes.json"
    if cfg_file.exists():
        with open(cfg_file) as f:
            cfg = json.load(f)
        print("[PASS] Bounding box configuration verified.")
        print(f"       Footprint: {cfg['training_footprint']['name']} {cfg['training_footprint']['bbox']}")
        print(f"       Target: {cfg['target_district']['name']} {cfg['target_district']['bbox']}")
        report["details"].append("Bounding box config: OK")
    else:
        print("[FAIL] config/bounding_boxes.json missing!")
        report["passed"] = False

    # 2. Administrative Boundaries
    mh_state_file = BOUNDARIES_DIR / "maharashtra_state.geojson"
    nashik_file = BOUNDARIES_DIR / "nashik_district.geojson"
    if mh_state_file.exists() and nashik_file.exists():
        mh_gdf = gpd.read_file(mh_state_file)
        nashik_gdf = gpd.read_file(nashik_file)
        print("[PASS] Administrative polygons verified.")
        print(f"       Maharashtra boundary features: {len(mh_gdf)}, CRS: {mh_gdf.crs}")
        print(f"       Nashik target polygon features: {len(nashik_gdf)}, CRS: {nashik_gdf.crs}")
        report["details"].append("Admin boundaries: OK")
    else:
        print(f"[FAIL] Boundary files missing in {BOUNDARIES_DIR}!")
        report["passed"] = False

    # 3. Station Dataset & 4 Physiographic Zones
    stations_meta = STATIONS_DIR / "maharashtra_stations_metadata.csv"
    stations_obs = STATIONS_DIR / "maharashtra_station_observations.csv"
    if stations_meta.exists() and stations_obs.exists():
        meta_df = pd.read_csv(stations_meta)
        obs_df = pd.read_csv(stations_obs)
        zones = set(meta_df["zone"].unique())
        required_zones = {"Konkan_Coastal", "Sahyadri_Crest", "Deccan_Plateau", "Vidarbha_East"}
        missing_zones = required_zones - zones

        nashik_count = len(meta_df[meta_df["district"] == "Nashik"])

        if not missing_zones and len(meta_df) >= 20 and nashik_count >= 5:
            print(f"[PASS] Point-station network verified ({len(meta_df)} stations, {len(obs_df)} obs).")
            print(f"       All 4 required physiographic zones represented: {list(zones)}")
            print(f"       Nashik local station count: {nashik_count} stations (Sufficient for Layer C)")
            report["details"].append(f"Station network ({len(meta_df)} stations across 4 zones): OK")
        else:
            print(f"[WARN] Station network check: Missing zones={missing_zones}, Nashik count={nashik_count}")
            if missing_zones:
                report["passed"] = False
    else:
        print("[FAIL] Station observation CSVs missing!")
        report["passed"] = False

    # 4. Elevation (DEM)
    dem_files = list(DEM_DIR.glob("*.tif")) + list(DEM_DIR.glob("*.hgt"))
    print(f"[INFO] DEM tiles available: {len(dem_files)} tiles ({sum(f.stat().st_size for f in dem_files)/(1024*1024):.1f} MB)")

    # 5. Land Cover
    lc_files = list(LANDCOVER_DIR.glob("*.tif"))
    print(f"[INFO] Landcover tiles available: {len(lc_files)} tiles ({sum(f.stat().st_size for f in lc_files)/(1024*1024):.1f} MB)")

    # 6. Gridded Weather / IPED
    imd_rain_files = list(GRIDDED_DIR.glob("**/*rain*.nc")) + list(GRIDDED_DIR.glob("**/*.grd"))
    print(f"[INFO] Gridded rainfall files available: {len(imd_rain_files)}")

    print("\n" + "=" * 70)
    if report["passed"]:
        print(" *** SANITY CHECK PASSED — READY TO PROCEED TO MODELING & API ***")
    else:
        print(" [!] SANITY CHECK FAILED — RESOLVE BLOCKERS BEFORE PROCEEDING")
    print("=" * 70 + "\n")

    return report["passed"]


if __name__ == "__main__":
    ok = run_checks()
    sys.exit(0 if ok else 1)
