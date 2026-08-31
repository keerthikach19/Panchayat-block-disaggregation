#!/usr/bin/env python3
"""
Script 05: Download IMD gridded rainfall (0.25°) and temperature (1.0°) datasets.

Uses imdlib to download daily gridded historical records over the Maharashtra footprint.
Saves raw .grd and converted NetCDF files in data/gridded/.
"""

import os
import sys
import json
import logging
from pathlib import Path
import imdlib as imd
import xarray as xr
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GRIDDED_DIR = PROJECT_ROOT / "data" / "gridded"
RAIN_DIR = GRIDDED_DIR / "imd_rainfall"
TEMP_DIR = GRIDDED_DIR / "imd_temperature"
CONFIG_DIR = PROJECT_ROOT / "config"


def load_bbox():
    config_path = CONFIG_DIR / "bounding_boxes.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        return config["training_footprint"]["bbox"]
    return {"lon_min": 72.45, "lat_min": 15.45, "lon_max": 81.05, "lat_max": 22.25}


def download_imd_data(var_type, start_yr, end_yr, output_dir):
    """
    Download IMD gridded data using imdlib.
    var_type: 'rain', 'tmin', 'tmax'
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Downloading IMD {var_type} for years {start_yr}-{end_yr} to {output_dir}...")
    try:
        data = imd.get_data(var_type, start_yr, end_yr, fn_format='yearwise', file_dir=str(output_dir))
        nc_path = output_dir / f"imd_{var_type}_{start_yr}_{end_yr}.nc"
        # Convert to xarray / netcdf
        ds = data.get_xarray()
        ds.to_netcdf(str(nc_path))
        logger.info(f"  ✓ Saved IMD {var_type} NetCDF to {nc_path} ({nc_path.stat().st_size / (1024*1024):.1f} MB)")
        return str(nc_path)
    except Exception as e:
        logger.error(f"Failed downloading IMD {var_type}: {e}")
        return None


def main():
    logger.info("=" * 60)
    logger.info("SCRIPT 05: Download IMD Gridded Rainfall and Temperature")
    logger.info("=" * 60)

    # Let's pull 2020-2024 (5 representative years for fast robust pipeline execution)
    start_year = 2020
    end_year = 2024

    rain_nc = download_imd_data('rain', start_year, end_year, RAIN_DIR)
    tmin_nc = download_imd_data('tmin', start_year, end_year, TEMP_DIR)
    tmax_nc = download_imd_data('tmax', start_year, end_year, TEMP_DIR)

    logger.info("=" * 60)
    logger.info("IMD Gridded Downloads Summary")
    logger.info(f"Rainfall: {rain_nc}")
    logger.info(f"Tmin: {tmin_nc}")
    logger.info(f"Tmax: {tmax_nc}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
