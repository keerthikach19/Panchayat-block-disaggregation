#!/usr/bin/env python3
"""
Crop Calendar and Phenological Sensitivity Matrix for Maharashtra / Nashik.

Defines real agronomic stages, weather vulnerability rules, and intervention thresholds
for the dominant agro-climatic crops in Nashik and Western Maharashtra.
"""

from datetime import datetime

# Nashik & Maharashtra Crop Phenology Database
CROP_CALENDARS = {
    "Grape": {
        "marathi_name": "द्राक्ष (Grape)",
        "varieties": ["Thompson Seedless", "Tas-A-Ganesh", "Manik Chaman", "Sharad Seedless"],
        "stages": {
            "Foundation_Pruning": {"months": [4, 5], "temp_opt": (25, 35), "critical_hazards": ["Heat stress", "Water stress"]},
            "Forward_Pruning": {"months": [9, 10], "temp_opt": (22, 32), "critical_hazards": ["Excessive unseasonal rain", "Downy mildew"]},
            "Shooting_Bud_Burst": {"months": [10, 11], "temp_opt": (20, 30), "critical_hazards": ["Flea beetle", "Anthracnose"]},
            "Flowering_Berry_Set": {"months": [11, 12], "temp_opt": (18, 28), "critical_hazards": ["Downy mildew", "Cloudy weather", "Drizzle"]},
            "Berry_Development": {"months": [12, 1, 2], "temp_opt": (15, 30), "critical_hazards": ["Powdery mildew", "Berry cracking", "Hailstorm"]},
            "Harvesting": {"months": [2, 3, 4], "temp_opt": (20, 35), "critical_hazards": ["Unseasonal rainfall", "High humidity"]}
        },
        "pathogen_thresholds": {
            "downy_mildew": {"rh_min": 80.0, "temp_range": (20.0, 30.0), "rain_min_mm": 5.0},
            "powdery_mildew": {"rh_range": (40.0, 75.0), "temp_range": (22.0, 32.0)},
            "berry_cracking": {"rain_single_day_mm": 25.0}
        }
    },
    "Onion": {
        "marathi_name": "कांदा (Onion / Kanda)",
        "varieties": ["Bhima Super", "Bhima Red", "N-53", "Agri Found Light Red"],
        "stages": {
            "Nursery": {"months": [6, 7, 10, 11], "critical_hazards": ["Damping off", "Heavy rain splash"]},
            "Transplanting": {"months": [7, 8, 12, 1], "critical_hazards": ["Water stagnation"]},
            "Vegetative_Bulb_Formation": {"months": [8, 9, 1, 2], "critical_hazards": ["Thrips", "Purple blotch", "Dry spell"]},
            "Harvesting_Curing": {"months": [9, 10, 3, 4], "critical_hazards": ["Rain during curing", "Rotting"]}
        },
        "pathogen_thresholds": {
            "purple_blotch": {"rh_min": 75.0, "temp_range": (20.0, 28.0), "rain_min_mm": 10.0},
            "thrips_infestation": {"dry_spell_days": 5, "temp_min": 30.0}
        }
    },
    "Bajra": {
        "marathi_name": "बाजरी (Pearl Millet / Bajra)",
        "stages": {
            "Sowing_Emergence": {"months": [6, 7], "critical_hazards": ["Dry spell > 10 days"]},
            "Vegetative_Tillering": {"months": [7, 8], "critical_hazards": ["Prolonged moisture stress"]},
            "Grain_Filling": {"months": [8, 9], "critical_hazards": ["Heavy rain during anthesis (Ergot risk)"]},
            "Maturity_Harvest": {"months": [9, 10], "critical_hazards": ["Rain at harvesting"]}
        }
    },
    "Sugarcane": {
        "marathi_name": "ऊस (Sugarcane / Us)",
        "varieties": ["Co 86032", "CoM 0265", "MS 10001", "VSI 434"],
        "stages": {
            "Germination_Tillering": {"months": [2, 3, 4, 5], "critical_hazards": ["Early shoot borer", "Water stress", "Heat waves"]},
            "Grand_Growth": {"months": [6, 7, 8, 9], "critical_hazards": ["Water logging", "White grub (हुमणी)", "Rust disease"]},
            "Ripening_Maturation": {"months": [10, 11, 12], "critical_hazards": ["Unseasonal rainfall decreasing brix", "Smut disease"]},
            "Harvesting_Crushing": {"months": [1, 2, 3], "critical_hazards": ["Labor availability", "Crushing delays"]}
        },
        "pathogen_thresholds": {
            "white_grub": {"rain_min_mm": 15.0, "temp_range": (22.0, 32.0)},
            "water_logging": {"rain_single_day_mm": 35.0}
        }
    },
    "Soybean": {
        "marathi_name": "सोयाबीन (Soybean)",
        "varieties": ["JS 335", "JS 9305", "Phule Kalyani", "MACS 1188"],
        "stages": {
            "Sowing_Emergence": {"months": [6, 7], "critical_hazards": ["Dry spell > 7 days", "Seed rot from heavy rain"]},
            "Vegetative_Flowering": {"months": [7, 8], "critical_hazards": ["Girdle beetle", "Stem fly", "Yellow mosaic virus"]},
            "Pod_Development": {"months": [8, 9, 10], "critical_hazards": ["Rust", "Pod borer (Spodoptera)", "Drought stress"]},
            "Maturity_Harvest": {"months": [9, 10, 11], "critical_hazards": ["Rain during harvesting causing pod shattering"]}
        },
        "pathogen_thresholds": {
            "soybean_rust": {"rh_min": 85.0, "temp_range": (20.0, 28.0), "rain_min_mm": 10.0},
            "spodoptera_litura": {"temp_range": (25.0, 35.0)}
        }
    },
    "Tomato": {
        "marathi_name": "टोमॅटो (Tomato)",
        "varieties": ["Abhinav", "Aryaman", "Saaho", "Phule Raja"],
        "stages": {
            "Transplanting_Vegetative": {"months": [6, 7, 10, 11], "critical_hazards": ["Damping off", "Leaf curl virus"]},
            "Flowering_Fruit_Set": {"months": [7, 8, 11, 12], "critical_hazards": ["Early blight", "Flower drop from heavy rain"]},
            "Harvesting": {"months": [8, 9, 1, 2, 3], "critical_hazards": ["Fruit rot", "Fruit borer"]}
        },
        "pathogen_thresholds": {
            "early_blight": {"rh_min": 80.0, "temp_range": (20.0, 30.0), "rain_min_mm": 10.0}
        }
    }
}

def _current_stage(crop_name, month):
    """Determine the current phenological stage for a crop by checking which stage
    contains the given month. Falls back to the first stage if no match."""
    cal = CROP_CALENDARS.get(crop_name, {})
    stages = cal.get("stages", {})
    for stage_name, stage_meta in stages.items():
        if month in stage_meta.get("months", []):
            return stage_name
    # Fallback: return last stage (closest to harvest)
    return list(stages.keys())[-1] if stages else "Vegetative"


def get_dominant_crop_for_panchayat(block_name, current_month=None):
    """
    Lookup primary commercial crop based on Nashik/Pune taluka agro-ecology.
    Uses the actual calendar month to determine the current crop phenological stage.
    """
    if current_month is None:
        current_month = datetime.now().month

    b = str(block_name).lower()
    if any(k in b for k in ["niphad", "dindori", "nashik", "sinnar", "chandvad", "kalwan"]):
        return "Grape", _current_stage("Grape", current_month)
    elif any(k in b for k in ["malegaon", "deola", "yeola", "nandgaon", "baglan"]):
        return "Onion", _current_stage("Onion", current_month)
    elif any(k in b for k in ["igatpuri", "trimbak", "peint", "peth", "surgana"]):
        return "Bajra", _current_stage("Bajra", current_month)
    elif any(k in b for k in ["bhor", "velhe", "mulshi", "mawal", "ambegaon", "junnar", "khed"]):
        return "Sugarcane", _current_stage("Sugarcane", current_month)
    elif any(k in b for k in ["baramati", "indapur", "daund", "purandhar", "shirur"]):
        return "Onion", _current_stage("Onion", current_month)
    elif any(k in b for k in ["haveli", "pune"]):
        return "Grape", _current_stage("Grape", current_month)
    else:
        return "Grape", _current_stage("Grape", current_month)
