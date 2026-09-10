#!/usr/bin/env python3
"""
Unit tests for Layer A decomposition with block_col='taluka'.

Tests:
  1. Taluka-level grouping produces correct block means and deviations.
  2. Single-station taluka: deviation == 0.
  3. Multi-station taluka: deviation is non-zero for non-uniform data.
  4. Fallback to 'district' when taluka column absent.
  5. apply_taluka_climatology: known ratio applied correctly.
  6. apply_taluka_climatology: missing taluka → returns district value.
  7. reconstruct_panchayat_prediction: floor at 0.
"""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

# Make project root importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.modeling.layer_a_decomposition import (
    apply_taluka_climatology,
    decompose_station_observations,
    reconstruct_panchayat_prediction,
)


# ---------------------------------------------------------------------------
# Minimal synthetic fixtures
# ---------------------------------------------------------------------------

def _make_meta():
    """3-station metadata: 2 in Nashik/Niphad, 1 in Nashik/Igatpuri."""
    return pd.DataFrame([
        {"id": "ST01", "station_id": "ST01", "name": "Niphad_A",   "district": "Nashik", "taluka": "Niphad"},
        {"id": "ST02", "station_id": "ST02", "name": "Niphad_B",   "district": "Nashik", "taluka": "Niphad"},
        {"id": "ST03", "station_id": "ST03", "name": "Igatpuri_A", "district": "Nashik", "taluka": "Igatpuri"},
    ])


def _make_obs():
    """
    Daily observations for 2 dates.
    Niphad: ST01=10mm, ST02=20mm  → mean=15mm; deviations: -5, +5
    Igatpuri: ST03=40mm           → mean=40mm; deviation: 0
    """
    rows = []
    for date_str in ["2024-07-01", "2024-07-02"]:
        rows += [
            {"station_id": "ST01", "date": date_str, "district": "Nashik", "taluka": "Niphad",
             "rainfall_mm": 10.0, "temp_mean_c": 25.0, "temp_max_c": 30.0, "temp_min_c": 20.0},
            {"station_id": "ST02", "date": date_str, "district": "Nashik", "taluka": "Niphad",
             "rainfall_mm": 20.0, "temp_mean_c": 27.0, "temp_max_c": 32.0, "temp_min_c": 22.0},
            {"station_id": "ST03", "date": date_str, "district": "Nashik", "taluka": "Igatpuri",
             "rainfall_mm": 40.0, "temp_mean_c": 22.0, "temp_max_c": 26.0, "temp_min_c": 18.0},
        ]
    return pd.DataFrame(rows)


RATIOS = {
    "Igatpuri": 1.68,
    "Niphad":   0.62,
    "Nashik":   1.40,
}


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

class TestDecomposeStationObservations(unittest.TestCase):

    def setUp(self):
        self.meta = _make_meta()
        self.obs  = _make_obs()

    def test_taluka_block_means_are_correct(self):
        """Niphad block mean should be (10+20)/2 = 15 mm."""
        result = decompose_station_observations(self.meta, self.obs, block_col="taluka")
        niphad_rows = result[result["taluka"] == "Niphad"]
        self.assertTrue((niphad_rows["block_rainfall_mean"] == 15.0).all(),
                        f"Expected 15.0, got {niphad_rows['block_rainfall_mean'].unique()}")

    def test_igatpuri_single_station_deviation_zero(self):
        """Single-station taluka (Igatpuri) → deviation should be 0."""
        result = decompose_station_observations(self.meta, self.obs, block_col="taluka")
        igt_rows = result[result["taluka"] == "Igatpuri"]
        self.assertTrue((igt_rows["rainfall_deviation"] == 0.0).all(),
                        f"Expected 0.0 deviation, got {igt_rows['rainfall_deviation'].unique()}")

    def test_niphad_multi_station_deviations(self):
        """Niphad two-station deviations: ST01 → -5, ST02 → +5."""
        result = decompose_station_observations(self.meta, self.obs, block_col="taluka")
        st01 = result[result["station_id"] == "ST01"]["rainfall_deviation"].iloc[0]
        st02 = result[result["station_id"] == "ST02"]["rainfall_deviation"].iloc[0]
        self.assertAlmostEqual(st01, -5.0, places=1)
        self.assertAlmostEqual(st02,  5.0, places=1)

    def test_block_col_used_column_populated(self):
        """block_col_used column should record the grouping column name."""
        result = decompose_station_observations(self.meta, self.obs, block_col="taluka")
        self.assertTrue((result["block_col_used"] == "taluka").all())

    def test_fallback_to_district_when_taluka_absent(self):
        """If taluka column absent from obs but in metadata, join should work via meta."""
        obs_no_taluka = self.obs.drop(columns=["taluka"])
        result = decompose_station_observations(self.meta, obs_no_taluka, block_col="taluka")
        # Should still compute block means (via merge)
        self.assertIn("block_rainfall_mean", result.columns)
        self.assertFalse(result["block_rainfall_mean"].isna().all())

    def test_district_level_grouping_still_works(self):
        """Legacy block_col='district' path must still produce valid output."""
        result = decompose_station_observations(self.meta, self.obs, block_col="district")
        # All 3 stations are in Nashik → one block mean for entire district
        district_mean = self.obs["rainfall_mm"].mean()
        self.assertTrue(
            np.isclose(result["block_rainfall_mean"].iloc[0], district_mean, atol=0.5),
            f"Expected district mean ~{district_mean:.1f}, got {result['block_rainfall_mean'].iloc[0]}"
        )

    def test_output_columns_present(self):
        """Expected columns are present in decomposed output."""
        result = decompose_station_observations(self.meta, self.obs, block_col="taluka")
        for col in ["block_rainfall_mean", "block_temp_mean",
                    "rainfall_deviation", "temp_deviation"]:
            self.assertIn(col, result.columns, f"Missing column: {col}")

    def test_no_nulls_in_key_columns(self):
        """No NaN values in block_rainfall_mean or rainfall_deviation."""
        result = decompose_station_observations(self.meta, self.obs, block_col="taluka")
        self.assertFalse(result["block_rainfall_mean"].isna().any())
        self.assertFalse(result["rainfall_deviation"].isna().any())


class TestApplyTalukaClimatology(unittest.TestCase):

    def test_known_ratio_applied(self):
        """Igatpuri ratio 1.68 × 20mm = 33.6mm."""
        result = apply_taluka_climatology(20.0, "Igatpuri", RATIOS)
        self.assertAlmostEqual(result, 33.6, places=1)

    def test_missing_taluka_returns_district_value(self):
        """Unknown taluka → returns district value unchanged."""
        result = apply_taluka_climatology(15.0, "UnknownTaluka", RATIOS)
        self.assertAlmostEqual(result, 15.0, places=2)

    def test_zero_district_value(self):
        """Zero district value → zero scaled value regardless of ratio."""
        result = apply_taluka_climatology(0.0, "Niphad", RATIOS)
        self.assertAlmostEqual(result, 0.0, places=2)

    def test_niphad_ratio(self):
        """Niphad ratio 0.62 × 50mm = 31.0mm."""
        result = apply_taluka_climatology(50.0, "Niphad", RATIOS)
        self.assertAlmostEqual(result, 31.0, places=1)


class TestReconstructPanchayatPrediction(unittest.TestCase):

    def test_basic_reconstruction(self):
        val = reconstruct_panchayat_prediction(15.0, 5.0, 0.5)
        self.assertAlmostEqual(val, 20.5, places=2)

    def test_floor_at_zero(self):
        """Negative raw value must be clipped to 0.0."""
        val = reconstruct_panchayat_prediction(5.0, -20.0, 0.0)
        self.assertEqual(val, 0.0)

    def test_no_residual_correction(self):
        val = reconstruct_panchayat_prediction(10.0, -3.0)
        self.assertAlmostEqual(val, 7.0, places=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
