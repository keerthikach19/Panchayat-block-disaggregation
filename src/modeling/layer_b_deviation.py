#!/usr/bin/env python3
"""
Layer B: Footprint-Wide Physical Deviation Model (LightGBM).

Trained ONCE across the entire Maharashtra training footprint:
  - Learns the generalizable terrain/land-cover/coastal -> weather deviation relationship.
  - Separate models for rainfall (orographic/coastal) and temperature (lapse rate).
  - Produces and stores feature importances for explainability panel.
  - Applies via inference-only to any target district within the footprint.
"""

import os
import sys
import json
import logging
import pickle
import numpy as np
import pandas as pd
import lightgbm as lgb
from pathlib import Path
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "data" / "models"
CONFIG_DIR = PROJECT_ROOT / "config"

# Primary physical feature set specified by PRP Section 5
FEATURE_COLS = [
    "elevation_mean",
    "elevation_std",
    "slope_mean",
    "aspect_mean",
    "lulc_tree_pct",
    "lulc_shrub_pct",
    "lulc_grass_pct",
    "lulc_crop_pct",
    "lulc_urban_pct",
    "lulc_water_pct",
    "dist_to_coast_km",
    "dist_to_water_km",
    "historical_rain_bias"
]


class FootprintDeviationModel:
    def __init__(self):
        self.rain_model = None
        self.temp_model = None
        self.rain_feature_importance = {}
        self.temp_feature_importance = {}
        self.station_loso_preds = {}
        self.metrics = {}

    def prepare_station_training_features(self, decomposed_df, covariates_df):
        """
        Merge station coordinates/observations with nearest spatial covariates across Maharashtra.
        Vectorized by unique station location.
        """
        unique_stations = decomposed_df[["station_id", "lat", "lon"]].drop_duplicates()
        station_cov_map = {}

        cov_lats = covariates_df["centroid_lat"].values
        cov_lons = covariates_df["centroid_lon"].values

        for _, st in unique_stations.iterrows():
            st_id = st["station_id"]
            dists = (cov_lats - st["lat"])**2 + (cov_lons - st["lon"])**2
            best_idx = np.argmin(dists)
            station_cov_map[st_id] = covariates_df.iloc[best_idx][FEATURE_COLS].to_dict()

        # Vectorized dataframe construction
        feats_list = []
        for _, row in decomposed_df.iterrows():
            st_cov = station_cov_map.get(row["station_id"], {})
            rec = {
                **st_cov,
                "station_id": row["station_id"],
                "date": row["date"],
                "rainfall_deviation": row["rainfall_deviation"],
                "temp_deviation": row["temp_deviation"]
            }
            feats_list.append(rec)

        df_train = pd.DataFrame(feats_list)
        return df_train

    def train_footprint_models(self, df_train, save_artifact=True):
        """
        Train footprint-wide LightGBM deviation models for rainfall and temperature.
        If save_artifact=True, persists the model dictionary to data/models/layer_b_models.pkl.
        """
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Training Layer B Footprint Deviation Models on {len(df_train)} training records...")

        X = df_train[FEATURE_COLS].copy()
        y_rain = df_train["rainfall_deviation"].values
        y_temp = df_train["temp_deviation"].values

        # 1. Rain Deviation Model (Tuned for orographic / non-linear effects)
        rain_params = {
            'objective': 'regression',
            'metric': 'rmse',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.85,
            'min_child_samples': 20,
            'verbose': -1,
            'random_state': 42
        }
        train_rain_data = lgb.Dataset(X, label=y_rain)
        self.rain_model = lgb.train(rain_params, train_rain_data, num_boost_round=150)

        # 2. Temperature Deviation Model (Tuned for elevation lapse rate)
        temp_params = {
            'objective': 'regression',
            'metric': 'mae',
            'boosting_type': 'gbdt',
            'num_leaves': 21,
            'learning_rate': 0.04,
            'feature_fraction': 0.9,
            'verbose': -1,
            'random_state': 42
        }
        train_temp_data = lgb.Dataset(X, label=y_temp)
        self.temp_model = lgb.train(temp_params, train_temp_data, num_boost_round=120)

        # 3. Calculate Feature Importances for Explainability Panel
        rain_imp = self.rain_model.feature_importance(importance_type='gain')
        temp_imp = self.temp_model.feature_importance(importance_type='gain')

        self.rain_feature_importance = {
            feat: round(float(imp) / max(1e-5, sum(rain_imp)), 4)
            for feat, imp in zip(FEATURE_COLS, rain_imp)
        }
        self.temp_feature_importance = {
            feat: round(float(imp) / max(1e-5, sum(temp_imp)), 4)
            for feat, imp in zip(FEATURE_COLS, temp_imp)
        }

        # Save trained model artifacts only if requested (prevents validation CV loops from corrupting production weights)
        if save_artifact:
            self.save_model_artifact()

        logger.info(f"Top 3 Rain Deviation Features: {sorted(self.rain_feature_importance.items(), key=lambda x: x[1], reverse=True)[:3]}")
        logger.info(f"Top 3 Temp Deviation Features: {sorted(self.temp_feature_importance.items(), key=lambda x: x[1], reverse=True)[:3]}")

        return self

    def save_model_artifact(self):
        """Persist Layer B model artifacts and precomputed LOSO station predictions to disk."""
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        artifact_path = MODELS_DIR / "layer_b_models.pkl"
        with open(artifact_path, "wb") as f:
            pickle.dump({
                "rain_model": self.rain_model,
                "temp_model": self.temp_model,
                "rain_feature_importance": self.rain_feature_importance,
                "temp_feature_importance": self.temp_feature_importance,
                "feature_cols": FEATURE_COLS,
                "station_loso_preds": self.station_loso_preds
            }, f)
        logger.info(f"  ✓ Saved Layer B models to {artifact_path}")

    def compute_station_loso_predictions(self, df_train):
        """
        Compute Leave-One-Station-Out (LOSO) out-of-sample rainfall deviation predictions
        for all weather stations in the training dataset.

        Methodology Note (PRP Layer C Geostatistical Correction):
        Evaluating the fully-fit Layer B model on its own training stations results in
        in-sample memorization leakage (residuals collapse to ~0.00 mm). By training a separate
        GBDT model with each target station withheld, we produce honest, out-of-sample predictions
        (and therefore non-trivial residuals) for Layer C geostatistical interpolation.
        """
        if "station_id" not in df_train.columns:
            logger.warning("df_train missing station_id; cannot compute LOSO predictions.")
            return {}

        unique_stations = df_train["station_id"].unique()
        logger.info(f"Computing out-of-sample LOSO predictions across {len(unique_stations)} stations...")

        rain_params = {
            'objective': 'regression',
            'metric': 'rmse',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.85,
            'min_child_samples': 20,
            'verbose': -1,
            'random_state': 42
        }

        loso_preds = {}
        for st_id in unique_stations:
            train_fold = df_train[df_train["station_id"] != st_id]
            test_fold = df_train[df_train["station_id"] == st_id]

            if len(train_fold) == 0 or len(test_fold) == 0:
                continue

            fold_ds = lgb.Dataset(train_fold[FEATURE_COLS], label=train_fold["rainfall_deviation"].values)
            fold_model = lgb.train(rain_params, fold_ds, num_boost_round=150)
            pred = float(fold_model.predict(test_fold[FEATURE_COLS]).mean())
            loso_preds[st_id] = pred

        self.station_loso_preds = loso_preds
        logger.info(f"  ✓ Computed {len(loso_preds)} out-of-sample station predictions.")
        return loso_preds

    def get_station_loso_prediction(self, station_id, fallback_features=None):
        """
        Retrieve the out-of-sample LOSO predicted rainfall deviation for a given station.
        Falls back to in-sample model prediction or 0.0 if the station was not precomputed.
        """
        if station_id in self.station_loso_preds:
            return float(self.station_loso_preds[station_id])
        if fallback_features is not None and self.rain_model is not None:
            return float(self.rain_model.predict(fallback_features[FEATURE_COLS]).mean())
        return 0.0

    def predict_panchayat_deviations(self, panchayat_covariates_df):
        """
        Apply footprint-trained Layer B model to a specific district's panchayat covariates (Inference only).
        """
        X_panch = panchayat_covariates_df[FEATURE_COLS].copy()
        
        pred_rain_dev = self.rain_model.predict(X_panch)
        pred_temp_dev = self.temp_model.predict(X_panch)

        # Feature explanation per panchayat
        dominant_factors = []
        for idx, row in X_panch.iterrows():
            if row["elevation_mean"] > 600 or row["slope_mean"] > 8:
                dominant_factors.append("Orographic Sahyadri Elevation Gradient")
            elif row["dist_to_coast_km"] < 60:
                dominant_factors.append("Coastal Maritime Proximity")
            elif row["lulc_crop_pct"] > 65:
                dominant_factors.append("Horticultural Orchard Microclimate")
            elif row["dist_to_water_km"] < 10:
                dominant_factors.append("Riparian Godavari River Valley")
            else:
                dominant_factors.append("Rain-Shadow Plateau Topography")

        results_df = panchayat_covariates_df.copy()
        results_df["pred_rain_deviation"] = np.round(pred_rain_dev, 2)
        results_df["pred_temp_deviation"] = np.round(pred_temp_dev, 2)
        results_df["dominant_factor"] = dominant_factors

        return results_df
