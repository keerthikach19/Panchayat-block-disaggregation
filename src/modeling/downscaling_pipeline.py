#!/usr/bin/env python3
"""
End-to-End Weather Downscaling Pipeline Orchestrator.

Integrates:
  Layer A: Bias / Anomaly Spatial Decomposition
  Layer B: Footprint-Trained Physical Deviation Model (LightGBM)
  Layer C: Local Geostatistical Residual Correction (Universal Kriging / IDW)
  Layer D: 30-Member Ensemble Uncertainty Propagation (IPED)

Supports both district-level (legacy) and block/taluka-level (SIH PS 26074) framing.
When taluka-level weather is supplied, each panchayat's block mean is anchored to its
enclosing taluka's observed/forecast value rather than a single uniform district value.
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

from src.modeling.layer_a_decomposition import (
    decompose_station_observations,
    apply_taluka_climatology,
    reconstruct_panchayat_prediction,
)
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

        # Load taluka climatology ratios for per-taluka block value scaling
        _ratios_path = PROJECT_ROOT / "data" / "corrections" / "taluka_climatology_ratios.json"
        try:
            with open(_ratios_path) as _f:
                self._taluka_ratios = json.load(_f)
        except FileNotFoundError:
            self._taluka_ratios = {}
            logger.warning("taluka_climatology_ratios.json not found; per-taluka scaling disabled.")

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
            self.layer_b.station_loso_preds = saved.get("station_loso_preds", {})
            
            # If station_loso_preds is empty in pickle, check if standalone JSON exists
            if not self.layer_b.station_loso_preds:
                json_path = MODELS_DIR / "station_loso_residuals.json"
                if json_path.exists():
                    try:
                        with open(json_path, "r") as jf:
                            self.layer_b.station_loso_preds = json.load(jf)
                    except Exception:
                        pass

            self.is_trained = True
            logger.info("✓ Loaded pre-trained Layer B model from %s (%d LOSO station predictions cached)", 
                        model_path, len(self.layer_b.station_loso_preds))
        except Exception as exc:
            logger.warning("Failed to load pre-trained model: %s — will retrain on first request.", exc)

    def train_footprint_pipeline(self):
        """
        Step 1: Train Layer B model ONCE across the full Maharashtra footprint.
        Precomputes out-of-sample Leave-One-Station-Out (LOSO) predictions for Layer C.
        Uses taluka-level block decomposition (block_col='taluka') as the primary grouping.
        """
        logger.info("=" * 70)
        logger.info(f"TRAINING DOWNSCALING PIPELINE ON FOOTPRINT: {self.footprint_name}")
        logger.info("=" * 70)

        # Load station data & covariates
        meta_df = pd.read_csv(STATIONS_DIR / "maharashtra_stations_metadata.csv")
        obs_df = pd.read_csv(STATIONS_DIR / "maharashtra_station_observations.csv")
        cov_df = pd.read_csv(DATA_DIR / "panchayat_covariates.csv")

        # Layer A: Taluka-level Spatial Decomposition (SIH PS 26074)
        decomposed_obs = decompose_station_observations(meta_df, obs_df, block_col="taluka")

        # Layer B: Footprint Deviation Training
        self.layer_b = FootprintDeviationModel()
        train_features = self.layer_b.prepare_station_training_features(decomposed_obs, cov_df)
        self.layer_b.train_footprint_models(train_features, save_artifact=False)

        # Step 1b: Precompute Leave-One-Station-Out (LOSO) predictions
        # Methodological necessity: Using in-sample predictions causes GBDT memorization leakage
        # where residuals collapse to ~0.00 mm. LOSO provides genuine out-of-sample station residuals.
        self.layer_b.compute_station_loso_predictions(train_features)
        self.layer_b.save_model_artifact()

        # Also persist a human-readable JSON artifact for inspection
        loso_json_path = MODELS_DIR / "station_loso_residuals.json"
        with open(loso_json_path, "w") as jf:
            json.dump(self.layer_b.station_loso_preds, jf, indent=2)
        logger.info(f"  ✓ Saved station LOSO predictions to {loso_json_path}")

        self.is_trained = True
        logger.info("Pipeline Footprint Training Complete.")
        return self

    def run_district_downscaling(
        self,
        district_name: str = "Nashik",
        input_block_weather=None,
        target_taluka: str = None,
    ):
        """
        Step 2: Apply trained pipeline to downscale weather for a target district.

        Parameters
        ----------
        district_name : str
            District to downscale (e.g. 'Nashik', 'Pune').
        input_block_weather : dict | None
            Block-level weather values.  May be either:

            • *District-level* (legacy):
              ``{"rainfall_mm": 22.5, "temp_max_c": 29.5, "temp_min_c": 21.0}``

            • *Taluka-level* (preferred, SIH PS 26074):
              ``{"talukas": {"Igatpuri": {"rainfall_mm": 38.0, ...},
                             "Niphad":   {"rainfall_mm": 14.0, ...}, ...}}``
              Each panchayat's block mean is then taken from its enclosing taluka's
              value instead of a single uniform district number.

        target_taluka : str | None
            Optional taluka filter — if supplied, only panchayats in this taluka
            are returned (useful for single-taluka API endpoints).
        """
        if not self.is_trained:
            self.train_footprint_pipeline()

        logger.info("=" * 70)
        logger.info(f"DOWNSCALING {'TALUKA ' + target_taluka.upper() if target_taluka else 'DISTRICT'} FORECAST: {district_name}")
        logger.info("=" * 70)

        # Load district panchayat covariates
        cov_df = pd.read_csv(DATA_DIR / "panchayat_covariates.csv")
        district_covs = cov_df[cov_df["district_name"].str.strip().str.lower() == district_name.lower()].copy()

        if len(district_covs) == 0:
            logger.warning(f"District {district_name} not found, using all available records in dataset.")
            district_covs = cov_df.copy()

        # Optional taluka filter (Phase 3: per-taluka API endpoint support)
        if target_taluka:
            mask = district_covs["block_name"].str.strip().str.lower() == target_taluka.lower()
            if mask.sum() > 0:
                district_covs = district_covs[mask].copy()
                logger.info(f"Filtered to taluka '{target_taluka}': {len(district_covs)} panchayats.")
            else:
                logger.warning(f"Taluka '{target_taluka}' not found in covariates; using full district.")

        logger.info(f"Target District {district_name}: {len(district_covs)} panchayats found.")

        # ------------------------------------------------------------------
        # Resolve block weather — district-level or per-taluka
        # ------------------------------------------------------------------
        taluka_weather_map: dict = {}  # taluka_name → {rainfall_mm, temp_max_c, temp_min_c}

        if input_block_weather and "talukas" in input_block_weather:
            # Taluka-level input (preferred)
            taluka_weather_map = input_block_weather["talukas"]
            # Compute district-level fallback as average across supplied talukas
            all_rain = [v.get("rainfall_mm", 0) for v in taluka_weather_map.values() if v.get("rainfall_mm") is not None]
            block_rain_val = float(np.mean(all_rain)) if all_rain else 0.0
            block_tmax_val = float(np.mean([v.get("temp_max_c", 29.5) for v in taluka_weather_map.values()]))
            block_tmin_val = float(np.mean([v.get("temp_min_c", 21.0) for v in taluka_weather_map.values()]))
            logger.info(
                "Using per-taluka block weather for %d talukas (district avg: %.1f mm).",
                len(taluka_weather_map), block_rain_val,
            )
        else:
            # District-level input (legacy / fallback)
            # The serving layer supplies the current IMD forecast. These defaults
            # remain only for explicit local/demo execution without an input.
            block_rain_val = input_block_weather.get("rainfall_mm", 22.5) if input_block_weather else 22.5
            block_tmax_val = input_block_weather.get("temp_max_c", 29.5) if input_block_weather else 29.5
            block_tmin_val = input_block_weather.get("temp_min_c", 21.0) if input_block_weather else 21.0

        # Layer B: Predict Physical Deviations
        b_results = self.layer_b.predict_panchayat_deviations(district_covs)
        pred_rain_dev = b_results["pred_rain_deviation"].values
        pred_temp_dev = b_results["pred_temp_deviation"].values

        # ------------------------------------------------------------------
        # Resolve per-panchayat block means from taluka weather map
        # ------------------------------------------------------------------
        if taluka_weather_map and "block_name" in district_covs.columns:
            panchayat_block_rain = np.array([
                taluka_weather_map.get(
                    row["block_name"],
                    {"rainfall_mm": apply_taluka_climatology(
                        block_rain_val, row["block_name"], self._taluka_ratios
                    )}
                ).get("rainfall_mm", block_rain_val)
                for _, row in district_covs.iterrows()
            ], dtype=float)
            panchayat_block_tmax = np.array([
                taluka_weather_map.get(row["block_name"], {}).get("temp_max_c", block_tmax_val)
                for _, row in district_covs.iterrows()
            ], dtype=float)
            panchayat_block_tmin = np.array([
                taluka_weather_map.get(row["block_name"], {}).get("temp_min_c", block_tmin_val)
                for _, row in district_covs.iterrows()
            ], dtype=float)
            logger.info("Per-panchayat block means resolved from taluka weather map.")
        else:
            # Legacy: uniform district value for all panchayats
            panchayat_block_rain = np.full(len(district_covs), block_rain_val)
            panchayat_block_tmax = np.full(len(district_covs), block_tmax_val)
            panchayat_block_tmin = np.full(len(district_covs), block_tmin_val)

        # Layer C: Geostatistical Residual Correction
        meta_df = pd.read_csv(STATIONS_DIR / "maharashtra_stations_metadata.csv")
        if "id" in meta_df.columns and "station_id" not in meta_df.columns:
            meta_df["station_id"] = meta_df["id"]
        obs_df = pd.read_csv(STATIONS_DIR / "maharashtra_station_observations.csv")
        district_stations = meta_df[meta_df["district"].str.lower() == district_name.lower()].copy()

        if len(district_stations) > 0:
            decomp = decompose_station_observations(meta_df, obs_df, block_col="taluka")
            dist_decomp = decomp[decomp["district"].str.lower() == district_name.lower()]
            # Station mean observed deviation
            st_avg_dev = dist_decomp.groupby("station_id")["rainfall_deviation"].mean().reset_index()
            st_merged = district_stations.merge(st_avg_dev, on="station_id")

            # Layer B prediction at station locations
            # CRITICAL METHODOLOGY FIX (PRP Layer C Geostatistical Correction):
            # Re-predicting with the in-sample footprint rain_model causes GBDT memorization
            # leakage over ~40 stations, collapsing residuals to ~0.00 mm (making Kriging a no-op).
            # We instead use precomputed Leave-One-Station-Out (LOSO) out-of-sample predictions
            # so that residual = observed_deviation - predicted_deviation captures genuine spatial
            # error across the district.
            st_covs = self.layer_b.prepare_station_training_features(dist_decomp, cov_df)
            
            loso_preds_list = []
            for st_id in st_merged["station_id"].values:
                st_sub = st_covs[st_covs["station_id"] == st_id]
                pred_val = self.layer_b.get_station_loso_prediction(st_id, fallback_features=st_sub)
                loso_preds_list.append(pred_val)

            st_merged["pred"] = loso_preds_list
            st_preds_arr = np.array(loso_preds_list)

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
            panchayat_block_rain, pred_rain_dev, layer_c_res, topo_var
        )

        # Assemble Final Disaggregated Panchayat Dataset
        final_df = district_covs.copy()
        final_df["block_rain_mean"] = panchayat_block_rain  # per-panchayat taluka block value
        final_df["block_temp_max"] = panchayat_block_tmax
        final_df["block_temp_min"] = panchayat_block_tmin
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

        # Downscaled temperatures (elevation lapse rate adjusted, per-panchayat block anchored)
        t_lapse = (district_covs["elevation_mean"].values - 550.0) * (6.5 / 1000.0)
        final_df["downscaled_tmax_pred"] = np.round(panchayat_block_tmax - t_lapse + pred_temp_dev * 0.5, 1)
        final_df["downscaled_tmin_pred"] = np.round(panchayat_block_tmin - t_lapse + pred_temp_dev * 0.5, 1)
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
