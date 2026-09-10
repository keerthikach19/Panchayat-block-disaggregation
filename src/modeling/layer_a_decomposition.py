#!/usr/bin/env python3
"""
Layer A: Bias / Anomaly Spatial Decomposition Engine.

Disaggregates raw spatial fields by decomposing observations and forecasts into:
  local_value = block_value + local_deviation

Applies across the whole training footprint:
  - Computes enclosing block/grid cell spatial mean.
  - Formulates the target variable as the local sub-block deviation.

Block granularity is configurable via block_col:
  - "district"  → legacy district-level grouping
  - "taluka"    → block/taluka-level grouping (SIH PS 26074 compliant)
"""

import numpy as np
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def decompose_station_observations(stations_df, obs_df, block_col: str = "taluka"):
    """
    Decompose station observations into block-mean and local station deviation.

    Parameters
    ----------
    stations_df : pd.DataFrame
        Station metadata containing at minimum: station_id, district, taluka.
    obs_df : pd.DataFrame
        Daily station observations with columns: station_id, date,
        rainfall_mm, temp_mean_c, temp_max_c, temp_min_c.
    block_col : str
        Column to use for spatial grouping. Defaults to 'taluka' (block-level).
        Use 'district' to reproduce legacy district-level behaviour.

    Returns
    -------
    pd.DataFrame
        Observation records augmented with block-level means and local deviations:
          block_rainfall_mean, block_temp_mean,
          rainfall_deviation, temp_deviation.

    Notes
    -----
    Talukas with only 1 station: the station IS the block mean → deviation = 0.
    Talukas with 0 stations    : handled gracefully — cannot arise here because
                                 merge() only keeps rows that have an obs record.
    """
    # Resolve the block column — fall back to district if taluka not present
    if block_col not in obs_df.columns:
        # Try joining from station metadata
        id_col = "station_id" if "station_id" in stations_df.columns else "id"
        merge_cols = [id_col, block_col] if block_col in stations_df.columns else [id_col, "district"]
        actual_block_col = block_col if block_col in stations_df.columns else "district"
        obs_df = obs_df.merge(
            stations_df[merge_cols].rename(columns={id_col: "station_id"}),
            on="station_id",
            how="left"
        )
        if actual_block_col not in obs_df.columns:
            raise ValueError(
                f"block_col='{block_col}' not found in obs_df or stations_df columns. "
                f"Available: {list(obs_df.columns)}"
            )
        effective_col = actual_block_col
    else:
        effective_col = block_col

    merged = obs_df.copy()

    # Compute daily block spatial mean across all stations in the same block
    obs_cols = ["rainfall_mm", "temp_mean_c", "temp_max_c", "temp_min_c"]
    available_obs_cols = [c for c in obs_cols if c in merged.columns]

    block_means = (
        merged.groupby([effective_col, "date"])[available_obs_cols]
        .transform("mean")
    )

    merged["block_rainfall_mean"] = block_means["rainfall_mm"].round(2)
    merged["block_temp_mean"] = block_means["temp_mean_c"].round(1)

    # Define the modeling targets: local deviations from block mean
    merged["rainfall_deviation"] = (merged["rainfall_mm"] - merged["block_rainfall_mean"]).round(2)
    merged["temp_deviation"] = (merged["temp_mean_c"] - merged["block_temp_mean"]).round(2)

    # Propagate block_col value onto every row for downstream grouping
    merged["block_col_used"] = effective_col
    merged["block_id"] = merged[effective_col]

    n_blocks = merged[effective_col].nunique()
    n_records = len(merged)
    logger.info(
        "Decomposed %d station observation records into %d %s-level block-means "
        "and local deviations (block_col='%s').",
        n_records, n_blocks, effective_col, effective_col,
    )
    return merged


def apply_taluka_climatology(district_value: float, taluka: str, ratios_dict: dict) -> float:
    """
    Scale a district-level forecast value to a taluka-level estimate using
    a precomputed climatological ratio.

    Parameters
    ----------
    district_value : float
        The coarse district-level rainfall or temperature value.
    taluka : str
        Name of the target taluka (must match a key in ratios_dict).
    ratios_dict : dict
        Mapping {taluka_name: ratio} where ratio = taluka_normal / district_normal.
        Values typically range from ~0.5 (rain-shadow) to ~2.5 (windward Sahyadri).

    Returns
    -------
    float
        Taluka-adjusted value, rounded to 2 decimal places.
        Falls back to district_value if taluka not found in ratios_dict.
    """
    ratio = ratios_dict.get(taluka)
    if ratio is None:
        logger.warning(
            "Taluka '%s' not found in ratios_dict (keys: %s). "
            "Returning district value unchanged.",
            taluka, list(ratios_dict.keys())[:5],
        )
        return round(float(district_value), 2)
    return round(float(district_value) * float(ratio), 2)


def reconstruct_panchayat_prediction(block_value, predicted_deviation, residual_correction=0.0):
    """
    Reconstruct the final local panchayat value:
      local_pred = max(0, block_value + predicted_deviation + residual_correction)
    """
    raw_val = block_value + predicted_deviation + residual_correction
    return max(0.0, round(raw_val, 2))
