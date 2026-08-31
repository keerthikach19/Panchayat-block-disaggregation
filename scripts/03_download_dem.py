#!/usr/bin/env python3
"""
Script 03: Download Copernicus DEM GLO-30 tiles for Maharashtra training footprint.

Downloads 30m resolution DEM tiles from the public S3 bucket.
Fallback: SRTM GL1 from OpenTopography.
"""

import os
import json
import math
import logging
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEM_DIR = PROJECT_ROOT / "data" / "dem"
CONFIG_DIR = PROJECT_ROOT / "config"

# S3 config
COPERNICUS_BUCKET = "copernicus-dem-30m"
COPERNICUS_REGION = "eu-central-1"

# Create unsigned S3 client
s3_client = boto3.client(
    's3',
    region_name=COPERNICUS_REGION,
    config=Config(signature_version=UNSIGNED)
)


def load_bbox():
    """Load bounding box from config."""
    config_path = CONFIG_DIR / "bounding_boxes.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        return config["training_footprint"]["bbox"]
    else:
        # Fallback: known Maharashtra bounding box
        logger.warning("Config not found, using known Maharashtra bbox")
        return {
            "lon_min": 72.45, "lat_min": 15.45,
            "lon_max": 81.05, "lat_max": 22.25
        }


def get_copernicus_tile_name(lat, lon):
    """
    Generate Copernicus DEM tile name for a given integer lat/lon.
    Tiles are named by their SW corner: Copernicus_DSM_COG_10_N{lat}_00_E{lon}_00_DEM
    """
    lat_prefix = "N" if lat >= 0 else "S"
    lon_prefix = "E" if lon >= 0 else "W"
    lat_abs = abs(lat)
    lon_abs = abs(lon)
    
    tile_name = f"Copernicus_DSM_COG_10_{lat_prefix}{lat_abs:02d}_00_{lon_prefix}{lon_abs:03d}_00_DEM"
    return tile_name


def list_tiles_for_bbox(bbox):
    """Compute all 1°×1° tiles needed to cover the bounding box."""
    lat_min = math.floor(bbox["lat_min"])
    lat_max = math.ceil(bbox["lat_max"])
    lon_min = math.floor(bbox["lon_min"])
    lon_max = math.ceil(bbox["lon_max"])
    
    tiles = []
    for lat in range(lat_min, lat_max):
        for lon in range(lon_min, lon_max):
            tile_name = get_copernicus_tile_name(lat, lon)
            tiles.append((lat, lon, tile_name))
    
    logger.info(f"Need {len(tiles)} tiles for bbox: "
                f"lat [{lat_min}, {lat_max}), lon [{lon_min}, {lon_max})")
    return tiles


def download_copernicus_tile(tile_name, dest_dir):
    """Download a single Copernicus DEM tile from S3."""
    s3_key = f"{tile_name}/{tile_name}.tif"
    dest_path = dest_dir / f"{tile_name}.tif"
    
    if dest_path.exists() and dest_path.stat().st_size > 1000:
        logger.debug(f"  Already exists: {tile_name}")
        return True, tile_name
    
    try:
        s3_client.download_file(COPERNICUS_BUCKET, s3_key, str(dest_path))
        size_mb = dest_path.stat().st_size / (1024 * 1024)
        logger.info(f"  ✓ {tile_name} ({size_mb:.1f} MB)")
        return True, tile_name
    except Exception as e:
        logger.warning(f"  ✗ {tile_name}: {e}")
        return False, tile_name


def download_srtm_fallback(lat, lon, dest_dir):
    """Download SRTM GL1 tile as fallback."""
    lat_prefix = "N" if lat >= 0 else "S"
    lon_prefix = "E" if lon >= 0 else "W"
    tile_name = f"{lat_prefix}{abs(lat):02d}{lon_prefix}{abs(lon):03d}"
    s3_key = f"SRTM_GL1/SRTM_GL1_srtm/{tile_name}.hgt"
    dest_path = dest_dir / f"SRTM_{tile_name}.hgt"
    
    if dest_path.exists() and dest_path.stat().st_size > 1000:
        return True, tile_name
    
    try:
        srtm_client = boto3.client(
            's3',
            endpoint_url='https://opentopography.s3.sdsc.edu',
            config=Config(signature_version=UNSIGNED)
        )
        srtm_client.download_file('raster', s3_key, str(dest_path))
        logger.info(f"  ✓ SRTM fallback: {tile_name}")
        return True, tile_name
    except Exception as e:
        logger.debug(f"  ✗ SRTM fallback failed for {tile_name}: {e}")
        return False, tile_name


def main():
    logger.info("=" * 60)
    logger.info("SCRIPT 03: Download Copernicus DEM GLO-30 for Maharashtra")
    logger.info("=" * 60)
    
    DEM_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load bounding box
    bbox = load_bbox()
    logger.info(f"Bounding box: lat [{bbox['lat_min']:.2f}, {bbox['lat_max']:.2f}], "
                f"lon [{bbox['lon_min']:.2f}, {bbox['lon_max']:.2f}]")
    
    # Compute tile list
    tiles = list_tiles_for_bbox(bbox)
    
    # Download tiles with parallel threads
    logger.info(f"Downloading {len(tiles)} Copernicus DEM tiles...")
    logger.info("(This may take a while — each tile is ~40-60 MB)")
    
    success_count = 0
    fail_count = 0
    failed_tiles = []
    
    # Use ThreadPoolExecutor for parallel downloads
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for lat, lon, tile_name in tiles:
            future = executor.submit(download_copernicus_tile, tile_name, DEM_DIR)
            futures[future] = (lat, lon, tile_name)
        
        for future in as_completed(futures):
            success, name = future.result()
            if success:
                success_count += 1
            else:
                fail_count += 1
                lat, lon, tile_name = futures[future]
                failed_tiles.append((lat, lon, tile_name))
    
    # Try SRTM fallback for failed tiles
    if failed_tiles:
        logger.info(f"\nAttempting SRTM fallback for {len(failed_tiles)} failed tiles...")
        srtm_success = 0
        for lat, lon, tile_name in failed_tiles:
            ok, _ = download_srtm_fallback(lat, lon, DEM_DIR)
            if ok:
                srtm_success += 1
        logger.info(f"SRTM fallback: {srtm_success}/{len(failed_tiles)} recovered")
    
    # Summary
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    
    tif_files = list(DEM_DIR.glob("*.tif"))
    hgt_files = list(DEM_DIR.glob("*.hgt"))
    total_size = sum(f.stat().st_size for f in tif_files + hgt_files) / (1024 * 1024)
    
    logger.info(f"Copernicus DEM tiles downloaded: {len(tif_files)}")
    logger.info(f"SRTM fallback tiles: {len(hgt_files)}")
    logger.info(f"Total DEM data: {total_size:.1f} MB")
    logger.info(f"Target tiles needed: {len(tiles)}")
    logger.info(f"Coverage: {len(tif_files) + len(hgt_files)}/{len(tiles)} "
                f"({100*(len(tif_files)+len(hgt_files))/max(len(tiles),1):.0f}%)")


if __name__ == "__main__":
    main()
