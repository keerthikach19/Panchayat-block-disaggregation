import sys
sys.path.insert(0, ".")
from src.advisory.crop_calendar import get_dominant_crop_for_panchayat, CROP_CALENDARS
from src.advisory.rule_engine import GKMSAdvisoryEngine

engine = GKMSAdvisoryEngine()

# Test 1: Crop calendar across talukas and seasons
print("=== TEST 1: CROP & STAGE LOOKUP ===")
test_cases = [
    ("Niphad", "2026-09-15"),   # Sept -> Forward_Pruning
    ("Niphad", "2026-11-20"),   # Nov -> Flowering_Berry_Set
    ("Bhor", "2026-07-10"),     # July -> Grand_Growth (Sugarcane)
    ("Bhor", "2026-11-15"),     # Nov -> Ripening_Maturation (Sugarcane)
    ("Malegaon", "2026-09-10"), # Sept -> Vegetative_Bulb_Formation (Onion)
    ("Igatpuri", "2026-08-20"), # Aug -> Grain_Filling (Bajra)
]
for block, dt in test_cases:
    f_m = int(dt.split("-")[1])
    crop, stage = get_dominant_crop_for_panchayat(block, current_month=f_m)
    print(f"Block: {block:12s} | Date: {dt} (m={f_m:02d}) -> Crop: {crop:10s} | Stage: {stage}")

# Test 2: GKMS Advisory Engine generation for Sugarcane vs Grape vs Onion
print("\n=== TEST 2: GKMS BULLETIN GENERATION ===")
panchayat_pune = {
    "panchayat_id": "MH_488_BHOR_01",
    "panchayat_name": "Bhor Gaon",
    "block_name": "Bhor",
    "district_name": "Pune",
    "downscaled_rain_pred": 28.5,
    "block_rain_mean": 18.0,
    "downscaled_tmax_pred": 29.0,
    "downscaled_tmin_pred": 20.5,
    "downscaled_rh_pred": 82.0,
    "dominant_factor": "Sahyadri Western Ghats Upslope"
}
bulletin_pune = engine.generate_panchayat_advisory(panchayat_pune, forecast_date="2026-09-09")
print(f"Pune Sugarcane Bulletin Header: {bulletin_pune['bulletin_header']}")
print(f"Crop: {bulletin_pune['dominant_crop']} ({bulletin_pune['crop_stage']})")
print(f"Alert Level: {bulletin_pune['alert_level']}")
print(f"Pest Warning EN: {bulletin_pune['pest_disease_warning_en']}")
print(f"Spray EN: {bulletin_pune['spray_recommendation_en']}")
print(f"Irrigation EN: {bulletin_pune['irrigation_advice_en']}")
print(f"Pest Warning MR: {bulletin_pune['pest_disease_warning_mr']}")

assert bulletin_pune["dominant_crop"] == "Sugarcane", f"Expected Sugarcane, got {bulletin_pune['dominant_crop']}"
assert "बाजरी" not in bulletin_pune["irrigation_advice_mr"], "Error: Sugarcane should not have Bajra Marathi text!"
assert "White Grub" in bulletin_pune["pest_disease_warning_en"] or "waterlogging" in bulletin_pune["pest_disease_warning_en"].lower(), "Expected cane pest warning"
print("\n✓ ALL ADVISORY TESTS PASSED!")
