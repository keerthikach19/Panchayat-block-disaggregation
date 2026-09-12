from datetime import date
from unittest.mock import Mock
import pytest
from src.ingestion.imd_live import IMDLiveData, LiveDataUnavailable
from src.services.forecast_service import ForecastService
from src.ingestion.forecast_schema import ROOT

def series(live):
    return {"parser_version":2,"issued_date":"2026-09-10","source_url":"https://imdagrimet.gov.in/example.pdf",
            "forecast_days":[{"date":f"2026-09-{d}","rainfall_mm":float(d)} for d in range(11,16)],
            "fetched_at":live._now_iso()}

def test_cache_selects_every_date_and_expiry(tmp_path):
    live=IMDLiveData(tmp_path)
    live._write_cache("agromet","Nashik",series(live))
    live._get_bytes=Mock(side_effect=AssertionError("network"))
    assert live.fetch_forecast("Nashik","2026-09-12")["selected_rainfall_mm"]==12
    assert live.fetch_forecast("Nashik","2026-09-15")["selected_rainfall_mm"]==15
    with pytest.raises(ValueError):
        live.fetch_forecast("Nashik","2026-09-20")
    assert live.select_forecast(series(live),cached=True,today=date(2026,9,20))["freshness"]=="archived"
    assert live.select_forecast(series(live),cached=True,today=date(2026,9,13))["freshness"]=="current"
    live._get_bytes.assert_not_called()

def test_network_failure_cached_and_unavailable(tmp_path):
    live=IMDLiveData(tmp_path)
    live._get_bytes=Mock(side_effect=OSError("offline"))
    with pytest.raises(LiveDataUnavailable):
        live.fetch_forecast("Nashik")
    live._write_cache("agromet","Nashik",series(live))
    result=live.fetch_forecast("Nashik","2026-09-14",force_refresh=True)
    assert result["selected_rainfall_mm"]==14 and result["cache_status"]=="cached"
    assert "offline" in result["live_error"]

@pytest.mark.parametrize("content",[b"<html>login required</html>",b"not a pdf",b"<html><a href='https://evil.test/evil.pdf'>PDF</a></html>"])
def test_invalid_content(tmp_path,content):
    live=IMDLiveData(tmp_path)
    live._get_bytes=Mock(return_value=content)
    with pytest.raises(ValueError):
        live._get_bulletin("https://imdagrimet.gov.in/a")
    with pytest.raises(ValueError):
        live.parse_bulletin_pdf(content,"Nashik","x")

def test_html_pdf_link(tmp_path):
    live=IMDLiveData(tmp_path)
    live._get_bytes=Mock(side_effect=[b'<html><a href="/file.pdf">PDF</a></html>',b"%PDF-test"])
    data,url=live._get_bulletin("https://imdagrimet.gov.in/a")
    assert data==b"%PDF-test" and url=="https://imdagrimet.gov.in/file.pdf"

def test_corrupt_cache_ignored(tmp_path):
    live=IMDLiveData(tmp_path)
    (tmp_path/"agromet_nashik.json").write_text("{")
    live._get_bytes=Mock(side_effect=OSError("offline"))
    with pytest.raises(LiveDataUnavailable):
        live.fetch_forecast("Nashik")

def test_district_independent_of_block_dataset(tmp_path):
    import shutil
    shutil.copytree(ROOT/"config",tmp_path/"config")
    (tmp_path/"data/boundaries").mkdir(parents=True)
    shutil.copy(ROOT/"data/panchayat_covariates.csv",tmp_path/"data/panchayat_covariates.csv")
    shutil.copy(ROOT/"data/boundaries/nashik_panchayats_covariates.geojson",tmp_path/"data/boundaries/nashik_panchayats_covariates.geojson")
    live=IMDLiveData(tmp_path/"cache")
    live._write_cache("agromet","Nashik",series(live))
    s=ForecastService(tmp_path,live)
    r=s.forecast(mode="district",valid_date="2026-09-12")
    assert r["mode"]==r["input_level"]=="district"
    assert {x["rainfall_mm"] for x in r["data"]}=={12}
    assert all(x["relative_humidity_max_pct"] is None for x in r["data"])
    assert s.forecast(mode="district",run_id=r["run_id"],valid_date="2026-09-13")["data"][0]["rainfall_mm"]==13
