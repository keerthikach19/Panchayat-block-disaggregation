import unittest
import numpy as np
import pandas as pd
from pathlib import Path
from src.modeling.downscaling_pipeline import DownscalingPipeline
from src.api.main import get_panchayat_explainability

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


class LayerCResidualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = DownscalingPipeline()
        cls.nashik_df = cls.pipeline.run_district_downscaling("Nashik")
        cls.pune_df = cls.pipeline.run_district_downscaling("Pune")

    def test_nashik_layer_c_residuals_vary_and_do_not_collapse(self):
        residuals = self.nashik_df["layer_c_residual"].values
        std_val = float(np.std(residuals))
        abs_max = float(np.max(np.abs(residuals)))
        
        # Layer C residuals must have significant spatial variation across Nashik
        self.assertGreater(std_val, 0.2, f"Nashik residual std {std_val:.4f} is too low (expected > 0.2)")
        self.assertGreater(abs_max, 1.0, f"Nashik max residual magnitude {abs_max:.4f} is too low (expected > 1.0)")
        
        # Less than 5% of panchayats should be near zero (|residual| < 0.01)
        near_zero_pct = float(np.mean(np.abs(residuals) < 0.01) * 100.0)
        self.assertLess(near_zero_pct, 5.0, f"Too many panchayats ({near_zero_pct:.1f}%) have near-zero residual")

    def test_pune_layer_c_residuals_vary_and_do_not_collapse(self):
        residuals = self.pune_df["layer_c_residual"].values
        std_val = float(np.std(residuals))
        abs_max = float(np.max(np.abs(residuals)))
        
        # Layer C residuals must have significant spatial variation across Pune
        self.assertGreater(std_val, 0.5, f"Pune residual std {std_val:.4f} is too low (expected > 0.5)")
        self.assertGreater(abs_max, 2.0, f"Pune max residual magnitude {abs_max:.4f} is too low (expected > 2.0)")

    def test_explainability_endpoint_surfaces_nonzero_kriging_residual(self):
        # Pick a panchayat with non-trivial residual
        sample_p = self.nashik_df.loc[self.nashik_df["layer_c_residual"].abs().idxmax()]
        p_id = sample_p["panchayat_id"]
        
        res = get_panchayat_explainability(p_id)
        breakdown = res.get("disaggregation_breakdown", {})
        kriging_res = breakdown.get("layer_c_kriging_residual_mm", 0.0)
        
        self.assertNotEqual(round(kriging_res, 2), 0.00, f"Explainability panel returned {kriging_res:.2f} mm (expected non-zero)")


if __name__ == "__main__":
    unittest.main()
