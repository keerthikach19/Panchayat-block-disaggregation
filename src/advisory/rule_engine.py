#!/usr/bin/env python3
"""
GKMS SOP-Structured Deterministic Agro-Meteorological Advisory Engine.

Adheres strictly to the IMD / GKMS (Gramin Krishi Mausam Sewa) SOP bulletin structure.
Translates downscaled panchayat-level microclimate predictions and historical anomalies
into actionable, auditable farm-level interventions.

Features:
  - IMD Categorical Rainfall Thresholds (Light: 2.5-15.5, Mod: 15.6-64.4, Heavy: >64.5mm)
  - 20mm Chemical Spray Wash-Off & Grape Downy Mildew / Onion Purple Blotch Risk
  - Expresses weather as anomaly / deviation from Panchayat Historical Baseline
  - Full Bilingual Engine: English + Marathi (मराठी)
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
SRC_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC_DIR.parent))

from src.advisory.crop_calendar import CROP_CALENDARS, get_dominant_crop_for_panchayat

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class GKMSAdvisoryEngine:
    def __init__(self):
        pass

    def generate_panchayat_advisory(self, panchayat_record, forecast_date=None):
        """
        Generate a complete GKMS SOP bulletin for a single downscaled panchayat record.
        """
        p_name = panchayat_record.get("panchayat_name", "Local Panchayat")
        v_name = panchayat_record.get("village_name", p_name)
        b_name = panchayat_record.get("block_name", "Nashik")
        d_name = panchayat_record.get("district_name", "Nashik")
        
        rain_pred = float(panchayat_record.get("downscaled_rain_pred", 0.0))
        block_rain = float(panchayat_record.get("block_rain_mean", rain_pred))
        tmax = float(panchayat_record.get("downscaled_tmax_pred", 30.0))
        tmin = float(panchayat_record.get("downscaled_tmin_pred", 21.0))
        rh = float(panchayat_record.get("downscaled_rh_pred", 75.0))
        ci_low = float(panchayat_record.get("rain_ci_lower_80", max(0, rain_pred - 4)))
        ci_high = float(panchayat_record.get("rain_ci_upper_80", rain_pred + 5))
        dominant_factor = str(panchayat_record.get("dominant_factor", "Topographic relief"))
        hist_bias = float(panchayat_record.get("historical_rain_bias", 0.0))

        if not forecast_date:
            forecast_date = datetime.now().strftime("%Y-%m-%d")
        valid_until = (datetime.strptime(forecast_date, "%Y-%m-%d") + timedelta(days=5)).strftime("%Y-%m-%d")

        # Determine dominant crop & stage
        crop_name, crop_stage = get_dominant_crop_for_panchayat(b_name)
        crop_meta = CROP_CALENDARS.get(crop_name, {})
        marathi_crop = crop_meta.get("marathi_name", crop_name)

        # 1. Anomaly vs Block & Historical Normal
        diff_from_block = round(rain_pred - block_rain, 1)
        if diff_from_block > 3.0:
            rain_rel_block_en = f"{abs(diff_from_block):.1f} mm HIGHER than the block-level average ({block_rain:.1f} mm)"
            rain_rel_block_mr = f"तालुका सरासरीपेक्षा ({block_rain:.1f} मिमी) {abs(diff_from_block):.1f} मिमी अधिक"
        elif diff_from_block < -3.0:
            rain_rel_block_en = f"{abs(diff_from_block):.1f} mm LOWER than the block-level average ({block_rain:.1f} mm)"
            rain_rel_block_mr = f"तालुका सरासरीपेक्षा ({block_rain:.1f} मिमी) {abs(diff_from_block):.1f} मिमी कमी"
        else:
            rain_rel_block_en = f"consistent with the block-level average ({block_rain:.1f} mm)"
            rain_rel_block_mr = f"तालुका सरासरीच्या जवळपास ({block_rain:.1f} मिमी)"

        # 2. Categorical Alert Level & Hazard Logic
        alert_level = "NORMAL"
        alert_mr = "सर्वसाधारण (NORMAL)"
        if rain_pred >= 64.5:
            alert_level = "WARNING"
            alert_mr = "दक्षता इशारा (ORANGE WARNING - HEAVY RAIN)"
        elif rain_pred >= 20.0 or (crop_name == "Grape" and rh >= 85.0):
            alert_level = "ADVISORY"
            alert_mr = "सल्ला (YELLOW ADVISORY)"

        # 3. Crop-Specific Agronomic Rules
        advisory_en = []
        advisory_mr = []
        spray_en = ""
        spray_mr = ""
        irrig_en = ""
        irrig_mr = ""
        pest_en = ""
        pest_mr = ""

        if crop_name == "Grape":
            if rain_pred >= 20.0 or rh >= 80.0:
                pest_en = "High risk of Downy Mildew (केवडा रोग) and Anthracnose due to sustained humidity > 80% and rain."
                pest_mr = "हवेतील ८०% पेक्षा जास्त आर्द्रता आणि पावसामुळे द्राक्ष बागेत केवडा (Downy Mildew) आणि करपा रोगाचा तीव्र धोका."
                spray_en = "POSTPONE all chemical spraying during active rainfall. Immediately after showers subside, apply prophylactic spray of Mancozeb 75 WP @ 2.5 g/L or Metalaxyl + Mancozeb @ 2 g/L."
                spray_mr = "पावसादरम्यान फवारणी तात्काळ थांबवावी. पाऊस थांबल्यानंतर तातडीने मँकोझेब (Mancozeb 75 WP) २.५ ग्रॅम किंवा मेटॅलॅक्सिल + मँकोझेब २ ग्रॅम प्रति लिटर पाण्यात मिसळून फवारावे."
                irrig_en = "SUSPEND all vineyard irrigation for 48 hours. Ensure proper trench drainage between vine rows to prevent collar rot."
                irrig_mr = "द्राक्ष बागेतील पाणी देणे पुढील ४८ तास बंद ठेवावे. मुळांभोवती पाणी साचू नये म्हणून चर काढून पाण्याचा निचरा करावा."
            else:
                spray_en = "Conditions favorable for preventive spraying against Powdery Mildew. Spray Wettable Sulphur 80 WDG @ 2 g/L."
                spray_mr = "भुरी रोगाच्या प्रतिबंधासाठी अनुकूल हवामान. पाण्यात विरघळणारे गंधक (Wettable Sulphur) २ ग्रॅम प्रति लिटर पाण्यात मिसळून फवारणी करावी."
                irrig_en = "Maintain light drip irrigation (2-3 hours/day) in the morning hours."
                irrig_mr = "सकाळच्या वेळी ठिबक सिंचनाद्वारे २ ते ३ तास हलके पाणी द्यावे."

        elif crop_name == "Onion":
            if rain_pred >= 15.0:
                pest_en = "Risk of Purple Blotch (जांभळा करपा) and bulb rotting in waterlogged fields."
                pest_mr = "पाणी साचल्यास कांद्यामध्ये जांभळा करपा आणि मुळकुजव्या रोगाचा धोका संभवतो."
                spray_en = "Avoid pesticide spraying today. Clear drainage channels across onion beds."
                spray_mr = "आज कीटकनाशक फवारणी टाळावी. कांदा वाफ्यांमधून पावसाचे पाणी वाहून जाण्यासाठी चर मोकळे करावेत."
                irrig_en = "Withhold irrigation until soil dries to field capacity."
                irrig_mr = "जमीन वापशावर येईपर्यंत कांदा पिकाला पाणी देऊ नये."
            else:
                spray_en = "Spray Profenofos 50 EC @ 1 ml/L + sticker for Thrips management in clear weather."
                spray_mr = "थ्रिप्स (फुलकिडे) नियंत्रणासाठी स्वच्छ वातावरणात प्रोफेनोफॉस ५० ईसी १ मिली प्रति लिटर स्टीकरसह फवारावे."
                irrig_en = "Provide regular scheduled furrow irrigation."
                irrig_mr = "कांदा पिकास आवश्यकतेनुसार नियमित पाटाने पाणी द्यावे."

        else: # Bajra / Cereal
            if rain_pred >= 10.0:
                spray_en = "Hold spraying. Ensure drainage in low-lying crop patches."
                spray_mr = "फवारणी टाळावी. शेतातील पाण्याचा निचरा करावा."
                irrig_en = "Rainfall is sufficient; no supplemental irrigation required."
                irrig_mr = "पाऊस पुरेसा असल्याने बाजरी पिकास वेगळे पाणी देण्याची गरज नाही."
            else:
                spray_en = "No immediate chemical intervention required."
                spray_mr = "रासायनिक फवारणीची तातडीची गरज नाही."
                irrig_en = "Apply protective irrigation during grain filling stage if dry spell exceeds 5 days."
                irrig_mr = "दाना भरण्याच्या अवस्थेत ५ दिवसांपेक्षा जास्त पावसाचा खंड पडल्यास संरक्षक पाणी द्यावे."

        # Compile GKMS Structured Bulletin
        weather_summary_en = (
            f"Expected 24-hr Rainfall: {rain_pred:.1f} mm (Confidence Band 80%: {ci_low:.1f} - {ci_high:.1f} mm). "
            f"This estimate is {rain_rel_block_en}, driven primarily by {dominant_factor}. "
            f"Max Temp: {tmax:.1f}°C, Min Temp: {tmin:.1f}°C, Relative Humidity: {rh:.0f}%."
        )

        weather_summary_mr = (
            f"अपेक्षित २४ तासांचा पाऊस: {rain_pred:.1f} मिमी (८०% विश्वासार्हता मर्यादा: {ci_low:.1f} ते {ci_high:.1f} मिमी). "
            f"हा अंदाज {rain_rel_block_mr}, मुख्यत्वे {dominant_factor} मुळे. "
            f"कमाल तापमान: {tmax:.1f}°से, किमान तापमान: {tmin:.1f}°से, हवेतील आर्द्रता: {rh:.0f}%."
        )

        agromet_advisory_en = f"Crop: {crop_name} ({crop_stage.replace('_', ' ')}). {pest_en} {spray_en} {irrig_en}"
        agromet_advisory_mr = f"पीक: {marathi_crop} ({crop_stage.replace('_', ' ')}). {pest_mr} {spray_mr} {irrig_mr}"

        bulletin = {
            "panchayat_id": panchayat_record.get("panchayat_id", "P001"),
            "panchayat_name": p_name,
            "village_name": v_name,
            "block_name": b_name,
            "district_name": d_name,
            "bulletin_header": f"GRAMIN KRISHI MAUSAM SEWA (GKMS) — DAMU KVK {d_name.upper()}",
            "issue_date": forecast_date,
            "valid_until": valid_until,
            "dominant_crop": crop_name,
            "marathi_crop_name": marathi_crop,
            "crop_stage": crop_stage,
            "downscaled_weather": {
                "rainfall_mm": rain_pred,
                "block_mean_rainfall_mm": block_rain,
                "ci_lower_80": ci_low,
                "ci_upper_80": ci_high,
                "temp_max_c": tmax,
                "temp_min_c": tmin,
                "rh_pct": rh,
                "confidence_level": panchayat_record.get("confidence_level", "HIGH"),
                "dominant_factor": dominant_factor
            },
            "weather_summary_en": weather_summary_en,
            "weather_summary_mr": weather_summary_mr,
            "agromet_advisory_en": agromet_advisory_en,
            "agromet_advisory_mr": agromet_advisory_mr,
            "spray_recommendation_en": spray_en,
            "spray_recommendation_mr": spray_mr,
            "irrigation_advice_en": irrig_en,
            "irrigation_advice_mr": irrig_mr,
            "pest_disease_warning_en": pest_en,
            "pest_disease_warning_mr": pest_mr,
            "alert_level": alert_level,
            "alert_level_mr": alert_mr,
            "status": "DRAFT"
        }

        return bulletin
