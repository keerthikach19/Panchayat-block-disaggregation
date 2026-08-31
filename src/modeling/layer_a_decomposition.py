#!/usr/bin/env python3
"""
Layer A: Bias / Anomaly Spatial Decomposition Engine.

Disaggregates raw spatial fields by decomposing observations and forecasts into:
  local_value = block_value + local_deviation

Applies across the whole training footprint:
  - Computes enclosing block/grid cell spatial mean.
  - Formulates the target variable as the local sub-block deviation.
"""

import numpy as np
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def decompose_station_observations(stations_df, obs_df):
    """
    Decompose station observations into block-mean and local station deviation.
    Groups stations by enclosing district/block.
    """
    merged = obs_df.copy()

    # Compute daily block/district spatial mean
    dist_col = "district" if "district" in merged.columns else "district_name"
    block_means = merged.groupby([dist_col, "date"])[["rainfall_mm", "temp_mean_c", "temp_max_c", "temp_min_c"]].transform("mean")
    
    merged["block_rainfall_mean"] = block_means["rainfall_mm"].round(2)
    merged["block_temp_mean"] = block_means["temp_mean_c"].round(1)

    # Define the modeling targets: local deviations from block mean
    merged["rainfall_deviation"] = (merged["rainfall_mm"] - merged["block_rainfall_mean"]).round(2)
    merged["temp_deviation"] = (merged["temp_mean_c"] - merged["block_temp_mean"]).round(2)

    logger.info(f"Decomposed {len(merged)} station observation records into block-means and local deviations.")
    return merged


def reconstruct_panchayat_prediction(block_value, predicted_deviation, residual_correction=0.0):
    """
    Reconstruct the final local panchayat value:
      local_pred = max(0, block_value + predicted_deviation + residual_correction)
    """
    raw_val = block_value + predicted_deviation + residual_correction
    return max(0.0, round(raw_val, 2))
