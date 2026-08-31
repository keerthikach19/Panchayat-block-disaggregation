#!/usr/bin/env python3
"""
Crop Calendar and Phenological Sensitivity Matrix for Maharashtra / Nashik.

Defines real agronomic stages, weather vulnerability rules, and intervention thresholds
for the dominant agro-climatic crops in Nashik and Western Maharashtra.
"""

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
        "stages": {
            "Tillering": {"months": [2, 3, 4, 5], "critical_hazards": ["Early shoot borer", "Water stress"]},
            "Grand_Growth": {"months": [6, 7, 8, 9], "critical_hazards": ["Water logging", "White grub"]}
        }
    }
}


def get_dominant_crop_for_panchayat(block_name, current_month=9):
    """
    Lookup primary commercial crop based on Nashik taluka agro-ecology.
    """
    b = str(block_name).lower()
    if any(k in b for k in ["niphad", "dindori", "nashik", "sinnar", "chandvad", "kalwan"]):
        return "Grape", "Flowering_Berry_Set" if current_month in [10, 11, 12] else "Forward_Pruning"
    elif any(k in b for k in ["malegaon", "deola", "yeola", "nandgaon", "baglan"]):
        return "Onion", "Vegetative_Bulb_Formation"
    elif any(k in b for k in ["igatpuri", "trimbak", "peint", "peth", "surgana"]):
        return "Bajra", "Grain_Filling"
    else:
        return "Grape", "Berry_Development"
