import sys
sys.path.insert(0, ".")
import asyncio
import httpx
from src.api.main import app, get_downscaled_forecast, get_panchayat_explainability, preview_dissemination, DisseminationPreviewPayload

async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        print("=== TEST 1: DISTRICT FORECAST (NASHIK OVERRIDE) ===")
        res = await ac.get("/api/forecast/nashik?block_rain=25.0")
        assert res.status_code == 200, f"Forecast failed: {res.status_code} {res.text}"
        data = res.json()
        print(f"District: {data['district']}, Count: {data['count']}, Block Rain: {data['block_uniform_rain_mm']} mm")
        print(f"Spread: {data['min_rain_panchayat_mm']} to {data['max_rain_panchayat_mm']} mm")

        print("\n=== TEST 2: EXPLAINABILITY ENDPOINT ===")
        p_id = data["data"][0]["panchayat_id"]
        res_exp = await ac.get(f"/api/panchayat/{p_id}/explainability")
        assert res_exp.status_code == 200, f"Explainability failed: {res_exp.status_code} {res_exp.text}"
        exp = res_exp.json()
        print(f"Panchayat: {exp['panchayat_name']} ({exp['block_name']})")
        print(f"Topography: Elevation={exp['topography']['elevation_mean_m']}m, Slope={exp['topography']['slope_degrees']}deg, Aspect={exp['topography']['aspect_degrees']}deg")
        print(f"Local TreeSHAP Drivers: {list(exp['local_feature_contributions'].keys())[:3]}")
        for feat, info in list(exp['local_feature_contributions'].items())[:3]:
            print(f"  {feat}: {info['contribution_mm']:+.3f} mm ({info['pct_of_total']}%) [{info['direction']}]")

        assert "local_feature_contributions" in exp, "Missing local_feature_contributions"
        assert "aspect_degrees" in exp["topography"], "Missing aspect_degrees"
        assert "advisory_bulletin" in exp, "Missing advisory_bulletin"

        print("\n=== TEST 3: DISSEMINATION PREVIEW ===")
        res_diss = await ac.post("/api/disseminate/preview", json={"panchayat_id": p_id, "channel": "WhatsApp", "language": "mr"})
        assert res_diss.status_code == 200, f"Dissemination failed: {res_diss.status_code}"
        diss = res_diss.json()
        print(f"Rendered Preview:\n{diss['rendered_preview'][:150]}...")

        print("\n✓ ALL API ENDPOINT TESTS PASSED!")

if __name__ == "__main__":
    asyncio.run(main())
