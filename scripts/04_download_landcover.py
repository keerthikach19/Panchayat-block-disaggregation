#!/usr/bin/env python3
"""
Script 04: Download ESA WorldCover v200 (2021) land cover tiles for Maharashtra.

10m resolution land cover with 11 classes.
Downloads from public S3 bucket s3://esa-worldcover/.
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
LANDCOVER_DIR = PROJECT_ROOT / "data" / "landcover"
CONFIG_DIR = PROJECT_ROOT / "config"

# ESA WorldCover S3 config
ESA_BUCKET = "esa-worldcover"
ESA_REGION = "eu-central-1"
ESA_PREFIX = "v200/2021/map/"

# Create unsigned S3 client
s3_client = boto3.client(
    's3',
    region_name=ESA_REGION,
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
        logger.warning("Config not found, using known Maharashtra bbox")
        return {
            "lon_min": 72.45, "lat_min": 15.45,
            "lon_max": 81.05, "lat_max": 22.25
        }


def get_worldcover_tile_name(lat, lon):
    """
    ESA WorldCover tiles are 3°×3°, named by their SW corner.
    Tile naming: ESA_WorldCover_10m_2021_v200_{N/S}{lat:02d}{E/W}{lon:03d}_Map.tif
    
    Tiles start at multiples of 3 degrees.
    """
    # Snap to nearest 3-degree grid
    tile_lat = (lat // 3) * 3
    tile_lon = (lon // 3) * 3
    
    lat_prefix = "N" if tile_lat >= 0 else "S"
    lon_prefix = "E" if tile_lon >= 0 else "W"
    
    tile_name = f"ESA_WorldCover_10m_2021_v200_{lat_prefix}{abs(int(tile_lat)):02d}{lon_prefix}{abs(int(tile_lon)):03d}_Map.tif"
    return tile_name


def list_tiles_for_bbox(bbox):
    """Compute all 3°×3° tiles needed to cover the bounding box."""
    lat_min = int(math.floor(bbox["lat_min"] / 3) * 3)
    lat_max = int(math.ceil(bbox["lat_max"] / 3) * 3)
    lon_min = int(math.floor(bbox["lon_min"] / 3) * 3)
    lon_max = int(math.ceil(bbox["lon_max"] / 3) * 3)
    
    tiles = set()
    for lat in range(lat_min, lat_max, 3):
        for lon in range(lon_min, lon_max, 3):
            tile_name = get_worldcover_tile_name(lat, lon)
            tiles.add((lat, lon, tile_name))
    
    tiles = sorted(tiles)
    logger.info(f"Need {len(tiles)} tiles for bbox: "
                f"lat [{lat_min}, {lat_max}), lon [{lon_min}, {lon_max})")
    for _, _, name in tiles:
        logger.info(f"  → {name}")
    return tiles


def download_worldcover_tile(tile_name, dest_dir):
    """Download a single ESA WorldCover tile from S3."""
    s3_key = f"{ESA_PREFIX}{tile_name}"
    dest_path = dest_dir / tile_name
    
    if dest_path.exists() and dest_path.stat().st_size > 1000:
        logger.debug(f"  Already exists: {tile_name}")
        return True, tile_name
    
    try:
        s3_client.download_file(ESA_BUCKET, s3_key, str(dest_path))
        size_mb = dest_path.stat().st_size / (1024 * 1024)
        logger.info(f"  ✓ {tile_name} ({size_mb:.1f} MB)")
        return True, tile_name
    except Exception as e:
        logger.warning(f"  ✗ {tile_name}: {e}")
        # Try alternative naming patterns
        alt_names = [
            tile_name.replace("_Map.tif", "_map.tif"),
            tile_name.replace("_v200_", "_v200_"),
        ]
        for alt_name in alt_names:
            try:
                alt_key = f"{ESA_PREFIX}{alt_name}"
                s3_client.download_file(ESA_BUCKET, alt_key, str(dest_path))
                size_mb = dest_path.stat().st_size / (1024 * 1024)
                logger.info(f"  ✓ {alt_name} (alt naming) ({size_mb:.1f} MB)")
                return True, tile_name
            except:
                pass
        return False, tile_name


def list_available_tiles():
    """List available tiles in the S3 bucket to discover the naming pattern."""
    logger.info("Discovering available tiles in ESA WorldCover S3 bucket...")
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        # List a sample to understand naming
        response = s3_client.list_objects_v2(
            Bucket=ESA_BUCKET,
            Prefix=ESA_PREFIX,
            MaxKeys=20
        )
        if 'Contents' in response:
            for obj in response['Contents'][:10]:
                logger.info(f"  Found: {obj['Key']} ({obj['Size']/1024/1024:.1f} MB)")
            return [obj['Key'] for obj in response['Contents']]
    except Exception as e:
        logger.warning(f"Could not list bucket contents: {e}")
    return []


def main():
    logger.info("=" * 60)
    logger.info("SCRIPT 04: Download ESA WorldCover v200 for Maharashtra")
    logger.info("=" * 60)
    
    LANDCOVER_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load bounding box
    bbox = load_bbox()
    logger.info(f"Bounding box: lat [{bbox['lat_min']:.2f}, {bbox['lat_max']:.2f}], "
                f"lon [{bbox['lon_min']:.2f}, {bbox['lon_max']:.2f}]")
    
    # First, discover naming pattern
    available = list_available_tiles()
    
    # Compute tile list
    tiles = list_tiles_for_bbox(bbox)
    
    # Download tiles
    logger.info(f"\nDownloading {len(tiles)} ESA WorldCover tiles...")
    logger.info("(Each tile is ~200-400 MB at 10m resolution)")
    
    success_count = 0
    fail_count = 0
    
    # Download sequentially for large files to avoid bandwidth issues
    for lat, lon, tile_name in tiles:
        ok, name = download_worldcover_tile(tile_name, LANDCOVER_DIR)
        if ok:
            success_count += 1
        else:
            fail_count += 1
    
    # Summary
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    
    tif_files = list(LANDCOVER_DIR.glob("*.tif"))
    total_size = sum(f.stat().st_size for f in tif_files) / (1024 * 1024)
    
    logger.info(f"WorldCover tiles downloaded: {len(tif_files)}")
    logger.info(f"Total land cover data: {total_size:.1f} MB")
    logger.info(f"Success: {success_count}/{len(tiles)}")
    if fail_count > 0:
        logger.warning(f"Failed: {fail_count} tiles — check naming pattern against bucket contents")


if __name__ == "__main__":
    main()
