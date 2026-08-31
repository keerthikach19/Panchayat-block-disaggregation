#!/usr/bin/env python3
"""
Backend Direct Unit Test Suite for Nashik and Pune endpoints.
"""
import sys
import io
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.api.main import (
    health_check,
    list_supported_districts,
    get_downscaled_forecast,
    get_panchayats_geojson,
    get_panchayat_explainability,
    list_advisories,
    get_validation_metrics,
    get_feedback_logs,
    preview_dissemination,
    DisseminationPreviewPayload
)

def test_endpoints():
    print("Testing health_check()...")
    h = health_check()
    assert h["status"] == "healthy"
    print("  [OK] Health OK:", h)

    print("\nTesting list_supported_districts()...")
    d_list = list_supported_districts()
    districts = d_list.get("districts", [])
    print(f"  [OK] Found {len(districts)} districts: {[d['name'] for d in districts]}")

    for d in ["Nashik", "Pune"]:
        print(f"\n--- Testing District: {d} ---")
        
        # 1. Forecast endpoint
        fc = get_downscaled_forecast(d)
        print(f"  [OK] Forecast returned {fc['count']} panchayats, min: {fc['min_rain_panchayat_mm']}mm, max: {fc['max_rain_panchayat_mm']}mm")
        assert fc['count'] > 0

        # 2. GeoJSON endpoint
        geo = get_panchayats_geojson(d)
        features = geo.get("features", [])
        print(f"  [OK] GeoJSON returned {len(features)} polygon features")
        assert len(features) > 0

        # 3. Explainability for first panchayat
        first_pid = features[0]["properties"]["panchayat_id"]
        exp = get_panchayat_explainability(first_pid)
        print(f"  [OK] Explainability for {first_pid} ({exp['panchayat_name']}):")
        print(f"      Rain Pred: {exp['disaggregation_breakdown']['final_downscaled_rainfall_mm']} mm")
        print(f"      Crop: {exp['advisory_bulletin']['dominant_crop']} ({exp['advisory_bulletin']['marathi_crop_name']})")
        print(f"      Advisory (EN): {exp['advisory_bulletin']['agromet_advisory_en'][:70]}...")
        print(f"      Advisory (MR): {exp['advisory_bulletin']['agromet_advisory_mr'][:70]}...")

        # 4. Advisories list
        adv_res = list_advisories(d, limit=5)
        print(f"  [OK] List advisories returned {adv_res['count']} bulletins")

    print("\nTesting validation metrics...")
    vm = get_validation_metrics()
    print(f"  [OK] LOOCV RMSE Improvement: {vm['headline_metrics']['rmse_improvement_percent']}%")

    print("\nTesting feedback logs...")
    fl = get_feedback_logs()
    print(f"  [OK] Feedback log count: {fl['count']}")

    print("\nTesting dissemination preview...")
    payload = DisseminationPreviewPayload(
        panchayat_id="MH_PUNE_556846",
        channel="WhatsApp",
        language="mr"
    )
    prev = preview_dissemination(payload)
    print("  [OK] Dissemination preview:")
    print("--------------------------------------------------")
    print(prev["rendered_preview"])
    print("--------------------------------------------------")

    print("\nALL BACKEND API CHECKS PASSED SUCCESSFULLY WITH ZERO ERRORS!")

if __name__ == "__main__":
    test_endpoints()
