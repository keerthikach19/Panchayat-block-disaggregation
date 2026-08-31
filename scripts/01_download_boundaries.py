#!/usr/bin/env python3
"""
Script 01: Download Maharashtra administrative boundaries & compute bounding boxes.

Sources:
  - india-geodata (github.com/yashveeeeeeer/india-geodata) — districts, blocks, sub-districts
  - DataMeet / NWIC — village/panchayat boundaries
  - Computes training footprint (Maharashtra state) and target district (Nashik) bounding boxes.
"""

import os
import sys
import json
import logging
import requests
import geopandas as gpd
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BOUNDARIES_DIR = PROJECT_ROOT / "data" / "boundaries"
CONFIG_DIR = PROJECT_ROOT / "config"

# india-geodata GitHub raw URLs
INDIA_GEODATA_BASE = "https://raw.githubusercontent.com/yashveeeeeeer/india-geodata/main"

# Known URLs for boundary data — these are typical paths in the repo
# We'll try multiple URL patterns since the repo structure may vary
BOUNDARY_URLS = {
    "states": [
        f"{INDIA_GEODATA_BASE}/geojson/states.geojson",
        f"{INDIA_GEODATA_BASE}/india/states.geojson",
        f"{INDIA_GEODATA_BASE}/states/states.geojson",
    ],
    "districts": [
        f"{INDIA_GEODATA_BASE}/geojson/districts.geojson",
        f"{INDIA_GEODATA_BASE}/india/districts.geojson",
        f"{INDIA_GEODATA_BASE}/districts/districts.geojson",
    ],
    "sub_districts": [
        f"{INDIA_GEODATA_BASE}/geojson/sub_districts.geojson",
        f"{INDIA_GEODATA_BASE}/india/sub_districts.geojson",
        f"{INDIA_GEODATA_BASE}/sub-districts/sub_districts.geojson",
    ],
    "blocks": [
        f"{INDIA_GEODATA_BASE}/geojson/blocks.geojson",
        f"{INDIA_GEODATA_BASE}/india/blocks.geojson",
        f"{INDIA_GEODATA_BASE}/blocks/blocks.geojson",
    ],
}

# DataMeet village boundaries for Maharashtra
DATAMEET_MAHARASHTRA_URL = "https://github.com/datameet/indian_village_boundaries/raw/master/maharashtra/maharashtra.geojson"

# NWIC village boundaries for Maharashtra (GeoJSON zip)
NWIC_MAHARASHTRA_URL = "https://nwdp.nwic.gov.in/dataset/9bad17f2-9d88-428d-98ad-831ef01ae2e4/resource/41bc7681-d90c-4338-8fdc-35f5f98bc417/download/vb_soi_mh_geojson.zip"

# Bounding box buffer in degrees
BBOX_BUFFER = 0.15

# Maharashtra and Nashik identifiers (case-insensitive matching)
MAHARASHTRA_NAMES = ["maharashtra"]
NASHIK_NAMES = ["nashik", "nasik", "naashik"]


def download_file(url, dest_path, description="file"):
    """Download a file from URL to dest_path. Returns True on success."""
    try:
        logger.info(f"Downloading {description} from {url}")
        response = requests.get(url, timeout=120, stream=True)
        response.raise_for_status()
        
        dest_path = Path(dest_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        size_mb = dest_path.stat().st_size / (1024 * 1024)
        logger.info(f"  → Saved to {dest_path} ({size_mb:.1f} MB)")
        return True
    except requests.exceptions.RequestException as e:
        logger.warning(f"  → Failed to download from {url}: {e}")
        return False


def try_download_from_urls(urls, dest_path, description):
    """Try downloading from a list of fallback URLs. Returns True on first success."""
    for url in urls:
        if download_file(url, dest_path, description):
            return True
    return False


def download_india_geodata_boundaries():
    """Download boundary files from india-geodata GitHub repo."""
    logger.info("=" * 60)
    logger.info("Step 1: Downloading boundary data from india-geodata")
    logger.info("=" * 60)
    
    results = {}
    for layer_name, urls in BOUNDARY_URLS.items():
        dest = BOUNDARIES_DIR / f"{layer_name}_india.geojson"
        success = try_download_from_urls(urls, dest, f"{layer_name} boundaries")
        results[layer_name] = success
        if not success:
            logger.warning(f"Could not download {layer_name} from any URL. Will try alternative sources.")
    
    return results


def download_alternative_boundaries():
    """Try alternative sources: GitHub API to discover actual repo structure."""
    logger.info("Trying GitHub API to discover india-geodata repo structure...")
    
    api_url = "https://api.github.com/repos/yashveeeeeeer/india-geodata/contents"
    try:
        resp = requests.get(api_url, timeout=30)
        resp.raise_for_status()
        contents = resp.json()
        logger.info(f"Repo root contents: {[c['name'] for c in contents]}")
        
        # Try to find GeoJSON directories
        for item in contents:
            if item['type'] == 'dir':
                dir_resp = requests.get(item['url'], timeout=30)
                if dir_resp.ok:
                    dir_contents = dir_resp.json()
                    geojson_files = [f for f in dir_contents if f['name'].endswith('.geojson')]
                    if geojson_files:
                        logger.info(f"  Found GeoJSON in {item['name']}/: {[f['name'] for f in geojson_files]}")
                        for gf in geojson_files:
                            # Download the relevant ones
                            base_name = gf['name'].replace('.geojson', '')
                            dest = BOUNDARIES_DIR / f"{base_name}_india.geojson"
                            if not dest.exists():
                                download_file(gf['download_url'], dest, f"{base_name} boundaries")
        return True
    except Exception as e:
        logger.warning(f"GitHub API fallback failed: {e}")
        return False


def download_village_boundaries():
    """Download village/panchayat boundaries from DataMeet or NWIC."""
    logger.info("=" * 60)
    logger.info("Step 2: Downloading village/panchayat boundaries")
    logger.info("=" * 60)
    
    # Try DataMeet first
    dest_datameet = BOUNDARIES_DIR / "maharashtra_villages_datameet.geojson"
    if download_file(DATAMEET_MAHARASHTRA_URL, dest_datameet, "DataMeet Maharashtra villages"):
        return dest_datameet
    
    # Try NWIC
    dest_nwic = BOUNDARIES_DIR / "maharashtra_villages_nwic.zip"
    if download_file(NWIC_MAHARASHTRA_URL, dest_nwic, "NWIC Maharashtra villages"):
        # Unzip
        import zipfile
        extract_dir = BOUNDARIES_DIR / "nwic_maharashtra"
        extract_dir.mkdir(exist_ok=True)
        try:
            with zipfile.ZipFile(dest_nwic, 'r') as zf:
                zf.extractall(extract_dir)
            logger.info(f"  → Extracted NWIC data to {extract_dir}")
            # Find the GeoJSON file
            for f in extract_dir.rglob("*.geojson"):
                return f
            for f in extract_dir.rglob("*.shp"):
                return f
        except Exception as e:
            logger.warning(f"  → Failed to extract NWIC zip: {e}")
    
    logger.warning("Could not download village boundaries from either DataMeet or NWIC.")
    return None


def filter_maharashtra(gdf, name_columns=None):
    """Filter a GeoDataFrame to Maharashtra rows."""
    if name_columns is None:
        # Try common column names
        name_columns = ['state_name', 'STATE_NAME', 'State_Name', 'st_nm', 'ST_NM',
                        'state', 'STATE', 'State', 'NAME_1', 'name', 'NAME']
    
    for col in name_columns:
        if col in gdf.columns:
            mask = gdf[col].str.lower().str.strip().isin(MAHARASHTRA_NAMES)
            if mask.any():
                logger.info(f"  → Found Maharashtra using column '{col}' ({mask.sum()} features)")
                return gdf[mask].copy()
    
    logger.warning(f"  → Could not find Maharashtra. Columns available: {list(gdf.columns)}")
    return None


def filter_nashik(gdf, name_columns=None):
    """Filter a GeoDataFrame to Nashik district rows."""
    if name_columns is None:
        name_columns = ['district_name', 'DISTRICT_NAME', 'District_Name', 'dt_name', 'DT_NAME',
                        'district', 'DISTRICT', 'District', 'NAME_2', 'name', 'NAME',
                        'dtname', 'DTNAME']
    
    for col in name_columns:
        if col in gdf.columns:
            mask = gdf[col].str.lower().str.strip().isin(NASHIK_NAMES)
            if mask.any():
                logger.info(f"  → Found Nashik using column '{col}' ({mask.sum()} features)")
                return gdf[mask].copy()
    
    logger.warning(f"  → Could not find Nashik. Columns available: {list(gdf.columns)}")
    return None


def compute_bounding_box(gdf, name, buffer=BBOX_BUFFER):
    """Compute bounding box with buffer for a GeoDataFrame."""
    bounds = gdf.total_bounds  # [minx, miny, maxx, maxy] = [lon_min, lat_min, lon_max, lat_max]
    bbox = {
        "lon_min": float(bounds[0] - buffer),
        "lat_min": float(bounds[1] - buffer),
        "lon_max": float(bounds[2] + buffer),
        "lat_max": float(bounds[3] + buffer),
    }
    logger.info(f"  → {name} bounding box (with {buffer}° buffer):")
    logger.info(f"    Lat: {bbox['lat_min']:.4f} to {bbox['lat_max']:.4f}")
    logger.info(f"    Lon: {bbox['lon_min']:.4f} to {bbox['lon_max']:.4f}")
    return bbox


def save_config(footprint_bbox, target_bbox):
    """Save bounding box config for all subsequent scripts."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    config = {
        "training_footprint": {
            "name": "Maharashtra",
            "bbox": footprint_bbox,
        },
        "target_district": {
            "name": "Nashik",
            "bbox": target_bbox,
        },
        "second_district": {
            "name": "Pune",
        },
        "bbox_buffer_degrees": BBOX_BUFFER,
        "crs": "EPSG:4326",
    }
    
    config_path = CONFIG_DIR / "bounding_boxes.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    logger.info(f"  → Saved bounding box config to {config_path}")
    return config


def main():
    logger.info("=" * 60)
    logger.info("SCRIPT 01: Download boundaries & compute bounding boxes")
    logger.info("=" * 60)
    
    BOUNDARIES_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Download boundary data
    download_results = download_india_geodata_boundaries()
    
    # If primary downloads failed, try alternative discovery
    if not any(download_results.values()):
        download_alternative_boundaries()
    
    # Step 2: Download village/panchayat boundaries
    village_path = download_village_boundaries()
    
    # Step 3: Load and filter boundaries
    logger.info("=" * 60)
    logger.info("Step 3: Loading and filtering boundaries for Maharashtra/Nashik")
    logger.info("=" * 60)
    
    maharashtra_gdf = None
    nashik_gdf = None
    
    # Try loading district boundaries first (most reliable for state/district filtering)
    for pattern in ["districts_india.geojson", "*district*india*.geojson", "*districts*.geojson"]:
        matches = list(BOUNDARIES_DIR.glob(pattern))
        if matches:
            try:
                gdf = gpd.read_file(matches[0])
                logger.info(f"Loaded {matches[0].name}: {len(gdf)} features, columns: {list(gdf.columns)}")
                
                mh = filter_maharashtra(gdf)
                if mh is not None and len(mh) > 0:
                    maharashtra_gdf = mh
                    # Save Maharashtra districts
                    mh.to_file(BOUNDARIES_DIR / "maharashtra_districts.geojson", driver="GeoJSON")
                    logger.info(f"  → Saved {len(mh)} Maharashtra district features")
                    
                    # Filter Nashik
                    nashik = filter_nashik(mh)
                    if nashik is not None and len(nashik) > 0:
                        nashik_gdf = nashik
                        nashik.to_file(BOUNDARIES_DIR / "nashik_district.geojson", driver="GeoJSON")
                        logger.info(f"  → Saved Nashik district features")
                    break
            except Exception as e:
                logger.warning(f"Failed to load {matches[0]}: {e}")
    
    # Try states file for Maharashtra boundary if districts didn't work
    if maharashtra_gdf is None:
        for pattern in ["states_india.geojson", "*state*india*.geojson", "*states*.geojson"]:
            matches = list(BOUNDARIES_DIR.glob(pattern))
            if matches:
                try:
                    gdf = gpd.read_file(matches[0])
                    logger.info(f"Loaded {matches[0].name}: {len(gdf)} features")
                    mh = filter_maharashtra(gdf)
                    if mh is not None and len(mh) > 0:
                        maharashtra_gdf = mh
                        mh.to_file(BOUNDARIES_DIR / "maharashtra_state.geojson", driver="GeoJSON")
                        break
                except Exception as e:
                    logger.warning(f"Failed to load {matches[0]}: {e}")
    
    # If we still don't have Maharashtra, use known approximate bounding box
    if maharashtra_gdf is None:
        logger.warning("Could not filter Maharashtra from downloaded data.")
        logger.info("Using known approximate Maharashtra bounding box from geographic data.")
        footprint_bbox = {
            "lon_min": 72.60 - BBOX_BUFFER,
            "lat_min": 15.60 - BBOX_BUFFER,
            "lon_max": 80.90 + BBOX_BUFFER,
            "lat_max": 22.10 + BBOX_BUFFER,
        }
    else:
        footprint_bbox = compute_bounding_box(maharashtra_gdf, "Maharashtra (training footprint)")
    
    # Nashik bounding box
    if nashik_gdf is None:
        logger.warning("Could not filter Nashik from downloaded data.")
        logger.info("Using known approximate Nashik bounding box.")
        target_bbox = {
            "lon_min": 73.40 - BBOX_BUFFER,
            "lat_min": 19.55 - BBOX_BUFFER,
            "lon_max": 74.75 + BBOX_BUFFER,
            "lat_max": 20.92 + BBOX_BUFFER,
        }
    else:
        target_bbox = compute_bounding_box(nashik_gdf, "Nashik (target district)")
    
    # Step 4: Save config
    logger.info("=" * 60)
    logger.info("Step 4: Saving bounding box config")
    logger.info("=" * 60)
    config = save_config(footprint_bbox, target_bbox)
    
    # Summary
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Training footprint (Maharashtra):")
    logger.info(f"  Lat: {footprint_bbox['lat_min']:.4f} to {footprint_bbox['lat_max']:.4f}")
    logger.info(f"  Lon: {footprint_bbox['lon_min']:.4f} to {footprint_bbox['lon_max']:.4f}")
    logger.info(f"Target district (Nashik):")
    logger.info(f"  Lat: {target_bbox['lat_min']:.4f} to {target_bbox['lat_max']:.4f}")
    logger.info(f"  Lon: {target_bbox['lon_min']:.4f} to {target_bbox['lon_max']:.4f}")
    
    boundary_files = list(BOUNDARIES_DIR.glob("*.geojson"))
    logger.info(f"Boundary files saved: {len(boundary_files)}")
    for f in boundary_files:
        logger.info(f"  → {f.name} ({f.stat().st_size / 1024:.1f} KB)")
    
    if village_path:
        logger.info(f"Village/panchayat boundary file: {village_path}")
    else:
        logger.info("Village/panchayat boundaries: NOT YET DOWNLOADED (will retry with alternative sources)")


if __name__ == "__main__":
    main()
