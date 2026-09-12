"""Weather-table facts from the Nashik bulletin issued 11 September 2026."""
from unittest.mock import Mock
import pytest
from src.ingestion.imd_live import IMDLiveData
from src.services.forecast_service import ForecastService
from src.services.comparison import ComparisonService
from src.services.bulletin import render_bulletin

TEXT = '''meeting dated 11.09.2026
Weather Forecast (12.09.2026 to 16.09.2026)
05 06 07 08 09 10 11 Date 12 13 14 15 16
14.4 10.6 4.7 4.6 7.0 5.0 1.8 Rainfall (mm) 9 35 50 20 10
26.0 24.5 26.5 25.0 25.5 27.6 26.3 Max. Temp. (0C) 30 29 27 28 30
21.7 21.8 22.0 21.8 21.7 21.5 21.8 Min. Temp. (0C) 21 20 18 19 20
Cloudy Cloudy Cloudy Cloudy Cloudy Cloudy Cloudy Cloud Cover Cloudy Cloudy Cloudy Cloudy Cloudy
95 97 94 95 92 94 89 Max. RH (%) 87 86 93 87 88
93 85 85 86 74 88 70 Min. RH (%) 68 85 86 86 80
5.1 3.6 4.0 3.0 3.8 3.3 3.2 Wind Speed (km/hr) 11 14 16 16 12
'''


def test_parser_separates_forecast_from_observations_and_preserves_cloud_text():
    r = IMDLiveData.parse_bulletin_text(TEXT, 'Nashik', 'https://imdagrimet.gov.in/example.pdf')
    assert [d['temp_max_c'] for d in r['forecast_days']] == [30,29,27,28,30]
    assert r['forecast_days'][0]['relative_humidity_min_pct'] == 68
    assert r['forecast_days'][0]['wind_speed_kmph'] == 11
    assert r['forecast_days'][0]['cloud_description'] == 'Cloudy'
    assert 'cloud_cover_oktas' not in r['forecast_days'][0]
    assert 'wind_direction_deg' not in r['forecast_days'][0]


@pytest.mark.parametrize('replacement', ['87 86 93 87', '101 86 93 87 88', 'oops 86 93 87 88'])
def test_bad_optional_row_rejected(replacement):
    with pytest.raises(ValueError):
        IMDLiveData.parse_bulletin_text(TEXT.replace('87 86 93 87 88', replacement), 'Nashik', 'x')


@pytest.mark.parametrize('replacement', ['9 35 50 20', '9 35 50 20 10 7', '9 35 -50 20 10'])
def test_rain_row_never_borrows_next_rows_historical_values(replacement):
    with pytest.raises(ValueError):
        IMDLiveData.parse_bulletin_text(TEXT.replace('9 35 50 20 10', replacement), 'Nashik', 'x')


def test_weather_propagation_comparison_and_printable_pinned_bulletin():
    live = Mock()
    live.fetch_forecast.return_value = IMDLiveData.parse_bulletin_text(TEXT, 'Nashik', 'https://imdagrimet.gov.in/example.pdf')
    service = ForecastService(live=live)
    forecast = service.forecast(mode='district', valid_date='2026-09-14')
    p = forecast['data'][0]
    assert p['temp_max_c'] == pytest.approx(27+p['adjustment_details']['temperature_adjustment_c'], abs=.006)
    assert p['relative_humidity_max_pct'] == 93
    assert p['cloud_description'] == 'Cloudy'
    geo = service.geojson(mode='district', run_id=forecast['run_id'], valid_date='2026-09-14')
    g = next(f['properties'] for f in geo['features'] if f['properties']['panchayat_id']==p['panchayat_id'])
    assert g['source_temp_max_c'] == 27
    assert g['local_temp_max_c'] == p['temp_max_c']
    comparison = ComparisonService(service).compare(valid_date='2026-09-14')
    assert comparison['weather_summary']['temp_max_c']['count'] == 1916
    assert comparison['weather_summary']['cloud_cover_oktas']['count'] == 0
    html = render_bulletin(service, p['panchayat_id'], 'district', forecast['run_id'])
    assert '2026-09-12' in html and '2026-09-16' in html and 'Maximum temperature' in html
    assert 'not an official IMD/GKMS advisory' in html and 'Cloudy' in html
    assert forecast['run_id'] in html
    live.fetch_forecast.side_effect = AssertionError('offline')
    block = service.forecast()['data'][0]
    assert '2026-09-11' in render_bulletin(service, block['panchayat_id'])


def test_legacy_rain_only_cache_refreshes_to_full_weather(tmp_path):
    live = IMDLiveData(tmp_path)
    old = IMDLiveData.parse_bulletin_text(TEXT, 'Nashik', 'x')
    old.pop('parser_version'); old['fetched_at'] = live._now_iso()
    live._write_cache('agromet', 'Nashik', old)
    live._get_bulletin = Mock(side_effect=OSError('offline'))
    assert 'offline' in live.fetch_forecast('Nashik')['live_error']
    live._get_bulletin.assert_called_once()
