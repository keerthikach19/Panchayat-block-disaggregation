#!/usr/bin/env python3
"""
scripts/10_generate_taluka_geojson.py

Generates taluka/block-level administrative boundary polygons by dissolving
panchayat polygons from official NWIC/LGD GeoJSON layers.
Outputs:
  - data/boundaries/maharashtra_talukas.geojson (FeatureCollection of talukas)
  - updates config/bounding_boxes.json with per-taluka bounding boxes & centroids
"""

import json
from pathlib import Path
import shapely.geometry
from shapely.ops import unary_union

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BOUNDARIES_DIR = PROJECT_ROOT / "data" / "boundaries"
LGD_FILE = PROJECT_ROOT / "data" / "lgd_codes" / "maharashtra_hierarchy_reference.csv"
CONFIG_FILE = PROJECT_ROOT / "config" / "bounding_boxes.json"

# Normalization mapping between polygon block property and LGD standard name
NAME_NORMALIZATION = {
    "yevla": "Yeola",
    "yeola": "Yeola",
    "peint": "Peth",
    "peth": "Peth",
    "chandvad": "Chandwad",
    "chandwad": "Chandwad",
    "central": "Nashik",
    "nashik": "Nashik",
    "pune": "Pune City",
    "pune city": "Pune City",
    "purandhar": "Purandar",
    "purandar": "Purandar",
    "mawal": "Maval",
    "maval": "Maval",
}

def load_lgd_codes():
    import pandas as pd
    if not LGD_FILE.exists():
        return {}
    df = pd.read_csv(LGD_FILE)
    mapping = {}
    for _, row in df.iterrows():
        b_name = str(row["block_name"]).strip()
        mapping[b_name.lower()] = {
            "block_code": int(row["block_code"]),
            "block_name": b_name,
            "district_name": str(row["district_name"]).strip(),
            "district_code": int(row["district_code"])
        }
    return mapping

def generate_talukas():
    lgd_meta = load_lgd_codes()
    district_files = [
        ("Nashik", BOUNDARIES_DIR / "nashik_panchayats_covariates.geojson"),
        ("Pune", BOUNDARIES_DIR / "pune_panchayats_covariates.geojson"),
    ]

    talukas_features = []
    taluka_bboxes = {}

    for district_name, geo_path in district_files:
        if not geo_path.exists():
            print(f"Warning: {geo_path} not found, skipping.")
            continue

        print(f"Loading panchayat boundaries from {geo_path.name}...")
        with open(geo_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Group polygons by normalized taluka name
        by_taluka = {}
        for feat in data.get("features", []):
            props = feat.get("properties", {})
            raw_b = str(props.get("block_name") or props.get("block") or "Central").strip()
            norm_b = NAME_NORMALIZATION.get(raw_b.lower(), raw_b.capitalize())
            geom_raw = feat.get("geometry")
            if not geom_raw:
                continue
            try:
                geom = shapely.geometry.shape(geom_raw)
                if not geom.is_valid:
                    geom = geom.buffer(0)
                if norm_b not in by_taluka:
                    by_taluka[norm_b] = []
                by_taluka[norm_b].append(geom)
            except Exception as e:
                continue

        print(f"Dissolving {len(by_taluka)} talukas in {district_name}...")
        for t_name, geom_list in by_taluka.items():
            merged_geom = unary_union(geom_list)
            if not merged_geom.is_valid:
                merged_geom = merged_geom.buffer(0)

            centroid = merged_geom.centroid
            minx, miny, maxx, maxy = merged_geom.bounds

            # Lookup LGD code if present
            lgd_info = lgd_meta.get(t_name.lower(), {})
            block_code = lgd_info.get("block_code", 0)

            feature = {
                "type": "Feature",
                "properties": {
                    "taluka_name": t_name,
                    "district_name": district_name,
                    "taluka_code": block_code,
                    "panchayats_count": len(geom_list),
                    "centroid_lat": round(centroid.y, 5),
                    "centroid_lon": round(centroid.x, 5),
                    "bbox": [round(minx, 5), round(miny, 5), round(maxx, 5), round(maxy, 5)]
                },
                "geometry": shapely.geometry.mapping(merged_geom)
            }
            talukas_features.append(feature)

            taluka_bboxes[t_name] = {
                "district": district_name,
                "taluka_code": block_code,
                "centroid": {"lat": round(centroid.y, 5), "lon": round(centroid.x, 5)},
                "bbox": {
                    "lon_min": round(minx, 5),
                    "lat_min": round(miny, 5),
                    "lon_max": round(maxx, 5),
                    "lat_max": round(maxy, 5)
                }
            }

    out_geojson = BOUNDARIES_DIR / "maharashtra_talukas.geojson"
    fc = {
        "type": "FeatureCollection",
        "features": talukas_features
    }
    with open(out_geojson, "w", encoding="utf-8") as f:
        json.dump(fc, f)

    print(f"✓ Created {out_geojson} with {len(talukas_features)} talukas.")

    # Update config/bounding_boxes.json
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["talukas"] = taluka_bboxes
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        print(f"✓ Updated {CONFIG_FILE} with {len(taluka_bboxes)} taluka bounding boxes.")

if __name__ == "__main__":
    generate_talukas()
