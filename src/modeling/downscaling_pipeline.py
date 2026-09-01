#!/usr/bin/env python3
"""
End-to-End Weather Downscaling Pipeline Orchestrator.

Integrates:
  Layer A: Bias / Anomaly Spatial Decomposition
  Layer B: Footprint-Trained Physical Deviation Model (LightGBM)
  Layer C: Local Geostatistical Residual Correction (Universal Kriging / IDW)
  Layer D: 30-Member Ensemble Uncertainty Propagation (IPED)

Executes for the Target District (Nashik) or any Scalability District (Pune).
Outputs comprehensive downscaled forecasts with confidence bounds and explainability tokens.
"""

import os
import sys
import json
import logging
import pickle
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path

# Add src to path
SRC_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC_DIR.parent))

from src.modeling.layer_a_decomposition import decompose_station_observations, reconstruct_panchayat_prediction
from src.modeling.layer_b_deviation import FootprintDeviationModel, FEATURE_COLS
from src.modeling.layer_c_kriging import LocalResidualCorrector
from src.modeling.layer_d_ensemble import EnsembleUncertaintyPropagator

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
STATIONS_DIR = DATA_DIR / "stations"
MODELS_DIR = DATA_DIR / "models"


class DownscalingPipeline:
    def __init__(self, footprint_name="Maharashtra", target_district="Nashik"):
        self.footprint_name = footprint_name
        self.target_district = target_district
        self.layer_b = None
        self.layer_c = None
        self.layer_d = EnsembleUncertaintyPropagator(num_members=30)
        self.is_trained = False

        # Auto-load pre-trained model from disk if available.
        # This enables live inference on a fresh GitHub clone without
        # needing the full 5 GB training dataset.
        self._try_load_pretrained_model()

    def _try_load_pretrained_model(self):
        """Load pre-trained Layer B models from disk if available."""
        model_path = MODELS_DIR / "layer_b_models.pkl"
        if not model_path.exists():
            logger.info("No pre-trained model found at %s — will train on first request.", model_path)
            return
        try:
            with open(model_path, "rb") as f:
                saved = pickle.load(f)
            self.layer_b = FootprintDeviationModel()
            self.layer_b.rain_model = saved["rain_model"]
            self.layer_b.temp_model = saved["temp_model"]
            self.layer_b.rain_feature_importance = saved.get("rain_feature_importance", {})
            self.layer_b.temp_feature_importance = saved.get("temp_feature_importance", {})
            self.is_trained = True
            logger.info("✓ Loaded pre-trained Layer B model from %s", model_path)
        except Exception as exc:
            logger.warning("Failed to load pre-trained model: %s — will retrain on first request.", exc)

    def train_footprint_pipeline(self):
        """
        Step 1: Train Layer B model ONCE across the full Maharashtra footprint.
        """
        logger.info("=" * 70)
        logger.info(f"TRAINING DOWNSCALING PIPELINE ON FOOTPRINT: {self.footprint_name}")
        logger.info("=" * 70)

        # Load station data & covariates
        meta_df = pd.read_csv(STATIONS_DIR / "maharashtra_stations_metadata.csv")
        obs_df = pd.read_csv(STATIONS_DIR / "maharashtra_station_observations.csv")
        cov_df = pd.read_csv(DATA_DIR / "panchayat_covariates.csv")

        # Layer A: Spatial Decomposition
        decomposed_obs = decompose_station_observations(meta_df, obs_df)

        # Layer B: Footprint Deviation Training
        self.layer_b = FootprintDeviationModel()
        train_features = self.layer_b.prepare_station_training_features(decomposed_obs, cov_df)
        self.layer_b.train_footprint_models(train_features)

        self.is_trained = True
        logger.info("Pipeline Footprint Training Complete.")
        return self

    def run_district_downscaling(self, district_name="Nashik", input_block_weather=None):
        """
        Step 2: Apply trained pipeline to downscale weather for a target district.
        input_block_weather: dict with block-level rainfall and temperature values.
        """
        if not self.is_trained:
            self.train_footprint_pipeline()

        logger.info("=" * 70)
        logger.info(f"DOWNSCALING DISTRICT FORECAST: {district_name}")
        logger.info("=" * 70)

        # Load district panchayat covariates
        cov_df = pd.read_csv(DATA_DIR / "panchayat_covariates.csv")
        district_covs = cov_df[cov_df["district_name"].str.strip().str.lower() == district_name.lower()].copy()

        if len(district_covs) == 0:
            logger.warning(f"District {district_name} not found, using all available records in dataset.")
            district_covs = cov_df.copy()

        logger.info(f"Target District {district_name}: {len(district_covs)} panchayats found.")

        # The serving layer supplies the current IMD forecast. These defaults
        # remain only for explicit local/demo execution without an input.
        block_rain_val = input_block_weather.get("rainfall_mm", 22.5) if input_block_weather else 22.5
        block_tmax_val = input_block_weather.get("temp_max_c", 29.5) if input_block_weather else 29.5
        block_tmin_val = input_block_weather.get("temp_min_c", 21.0) if input_block_weather else 21.0

        # Layer B: Predict Physical Deviations
        b_results = self.layer_b.predict_panchayat_deviations(district_covs)
        pred_rain_dev = b_results["pred_rain_deviation"].values
        pred_temp_dev = b_results["pred_temp_deviation"].values

        # Layer C: Geostatistical Residual Correction
        meta_df = pd.read_csv(STATIONS_DIR / "maharashtra_stations_metadata.csv")
        if "id" in meta_df.columns and "station_id" not in meta_df.columns:
            meta_df["station_id"] = meta_df["id"]
        obs_df = pd.read_csv(STATIONS_DIR / "maharashtra_station_observations.csv")
        district_stations = meta_df[meta_df["district"].str.lower() == district_name.lower()].copy()

        if len(district_stations) > 0:
            decomp = decompose_station_observations(meta_df, obs_df)
            dist_decomp = decomp[decomp["district"].str.lower() == district_name.lower()]
            # Station mean observed deviation
            st_avg_dev = dist_decomp.groupby("station_id")["rainfall_deviation"].mean().reset_index()
            st_merged = district_stations.merge(st_avg_dev, on="station_id")

            # Layer B prediction at station locations
            st_covs = self.layer_b.prepare_station_training_features(dist_decomp, cov_df)
            st_preds = self.layer_b.rain_model.predict(st_covs[FEATURE_COLS])
            # Aggregate station prediction mean
            st_covs["pred"] = st_preds
            st_pred_means = st_covs.groupby("station_id")["pred"].mean().reset_index()
            st_merged = st_merged.merge(st_pred_means, on="station_id")
            
            st_preds_arr = st_merged["pred"].values if "pred" in st_merged else np.zeros(len(st_merged))

            self.layer_c = LocalResidualCorrector(target_district=district_name)
            self.layer_c.fit_local_residuals(st_merged, st_preds_arr)
            layer_c_res = self.layer_c.interpolate_panchayat_residuals(
                district_covs["centroid_lat"].values,
                district_covs["centroid_lon"].values
            )
        else:
            layer_c_res = np.zeros(len(district_covs))
            self.layer_c = LocalResidualCorrector(target_district=district_name)
            self.layer_c.method_used = "IDW"
            self.layer_c.decision_rationale = f"No station in {district_name}, zero residual adjustment applied."

        # Layer D: 30-Member Ensemble Uncertainty Propagation
        topo_var = (district_covs["elevation_std"].values / 10.0) + (district_covs["slope_mean"].values / 5.0)
        ensemble_stats = self.layer_d.propagate_ensemble(
            block_rain_val, pred_rain_dev, layer_c_res, topo_var
        )

        # Assemble Final Disaggregated Panchayat Dataset
        final_df = district_covs.copy()
        final_df["block_rain_mean"] = block_rain_val
        final_df["block_temp_max"] = block_tmax_val
        final_df["block_temp_min"] = block_tmin_val
        final_df["layer_b_deviation"] = pred_rain_dev
        final_df["layer_c_residual"] = layer_c_res
        final_df["downscaled_rain_pred"] = ensemble_stats["ensemble_mean"]
        final_df["rain_ci_lower_80"] = ensemble_stats["ci_lower_80"]
        final_df["rain_ci_upper_80"] = ensemble_stats["ci_upper_80"]
        final_df["rain_ci_lower_95"] = ensemble_stats["ci_lower_95"]
        final_df["rain_ci_upper_95"] = ensemble_stats["ci_upper_95"]
        final_df["uncertainty_std"] = ensemble_stats["uncertainty_std"]
        final_df["confidence_level"] = ensemble_stats["confidence_level"]
        final_df["dominant_factor"] = b_results["dominant_factor"].values
        for field in (
            "forecast_source", "forecast_status", "forecast_issued_date",
            "forecast_valid_date", "forecast_source_url", "observed_24h_mm",
            "observed_24h_date", "observed_24h_status",
        ):
            if input_block_weather and field in input_block_weather:
                final_df[field] = input_block_weather[field]

        # Downscaled temperatures (elevation lapse rate adjusted)
        t_lapse = (district_covs["elevation_mean"].values - 550.0) * (6.5 / 1000.0)
        final_df["downscaled_tmax_pred"] = np.round(block_tmax_val - t_lapse + pred_temp_dev * 0.5, 1)
        final_df["downscaled_tmin_pred"] = np.round(block_tmin_val - t_lapse + pred_temp_dev * 0.5, 1)
        final_df["downscaled_rh_pred"] = np.round(np.clip(60.0 + final_df["downscaled_rain_pred"] * 0.4, 30.0, 98.0), 1)

        # Save output
        out_csv = DATA_DIR / f"downscaled_forecast_{district_name.lower()}.csv"
        final_df.to_csv(out_csv, index=False)
        logger.info(f"  ✓ Saved {len(final_df)} downscaled panchayat forecasts to {out_csv}")

        # Summary of rainfall gradient across district
        min_p = final_df.loc[final_df["downscaled_rain_pred"].idxmin()]
        max_p = final_df.loc[final_df["downscaled_rain_pred"].idxmax()]
        logger.info("=" * 70)
        logger.info(f"DISAGGREGATION CONTRAST SUMMARY FOR {district_name.upper()}:")
        logger.info(f"Coarse Block Uniform Value: {block_rain_val:.1f} mm")
        logger.info(f"Lowest Panchayat:  {min_p['panchayat_name']} ({min_p['block_name']}) -> {min_p['downscaled_rain_pred']:.1f} mm")
        logger.info(f"Highest Panchayat: {max_p['panchayat_name']} ({max_p['block_name']}) -> {max_p['downscaled_rain_pred']:.1f} mm")
        logger.info(f"Within-District Disaggregation Spread: {max_p['downscaled_rain_pred'] - min_p['downscaled_rain_pred']:.1f} mm")
        logger.info("=" * 70)

        return final_df


if __name__ == "__main__":
    pipeline = DownscalingPipeline(footprint_name="Maharashtra", target_district="Nashik")
    pipeline.train_footprint_pipeline()
    pipeline.run_district_downscaling(district_name="Nashik")
