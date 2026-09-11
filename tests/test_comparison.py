from copy import deepcopy
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from src.services.forecast_service import ForecastService
from src.services.comparison import ComparisonService, pair_rows, statistics


@pytest.fixture(scope='module')
def comparison():
    live=Mock()
    live.fetch_forecast.return_value={'issued_date':'2026-09-11','source_url':'https://imdagrimet.gov.in/example.pdf',
        'forecast_days':[{'date':f'2026-09-{day}','rainfall_mm':rain} for day,rain in [(12,9.),(13,35.),(14,50.),(15,20.),(16,10.)]]}
    return ComparisonService(ForecastService(live=live))


def test_exact_overlap_decomposition_and_weighting(comparison):
    r=comparison.compare(valid_date='2026-09-14')
    assert r['overlap_dates']==['2026-09-12','2026-09-13','2026-09-14','2026-09-15']
    assert r['block_only_dates']==['2026-09-11']
    assert r['district_only_dates']==['2026-09-16']
    assert r['district_issue_days_later']==1
    assert r['comparable_variables']==['rainfall_mm']
    assert len(r['rows'])==1916
    assert all(abs(x['rounding_residual_mm'])<.0001 for x in r['rows'])
    assert r['summary']['area_weighted_district_mm']==pytest.approx(50.,abs=.0001)
    assert r['summary']['mean_absolute_difference_mm']==pytest.approx(29.0210623173)
    assert r['summary']['mean_absolute_difference_mm']>abs(r['summary']['mean_difference_mm'])
    assert r['summary']['different_20mm_trigger']==718


def test_filters_pin_runs_and_reject_unshared_dates(comparison):
    first=comparison.compare()
    pins=dict(block_run_id=first['block_source']['run_id'],district_run_id=first['district_source']['run_id'])
    filtered=comparison.compare(valid_date='2026-09-13',block='Igatpuri',**pins)
    assert filtered['comparison_id']==first['comparison_id']
    assert len(filtered['rows'])==117
    assert {r['block_source_mm'] for r in filtered['rows']}=={38.2}
    assert {r['district_source_mm'] for r in filtered['rows']}=={35.}
    assert {r['valid_date'] for r in filtered['rows']}=={'2026-09-13'}
    with pytest.raises(ValueError,match='not shared'): comparison.compare(valid_date='2026-09-11',**pins)
    with pytest.raises(ValueError,match='Unresolved'): comparison.compare(block='Central',**pins)


def test_zero_denominator_duplicates_and_misalignment():
    # Deliberate unit fixtures, not meteorological observations.
    b={'panchayat_id':'v','panchayat_name':'Village','block_id':'b','block_name':'Block','valid_date':'2026-09-12',
       'source_rainfall_mm':2.,'local_rainfall_mm':2.,'adjustment_details':{'area_m2':1.,'village_elevation_m':1.,'rainfall_factor':1.}}
    d={**b,'source_rainfall_mm':0.,'local_rainfall_mm':0.}
    rows,_=pair_rows([b],[d]);assert rows[0]['percent_vs_district'] is None
    assert statistics(rows)['mean_absolute_difference_mm']==2.
    with pytest.raises(ValueError,match='Duplicate'):pair_rows([b,b],[d])
    with pytest.raises(ValueError,match='alignment'):pair_rows([b],[{**d,'valid_date':'2026-09-13'}])
    _,missing=pair_rows([b],[]);assert missing['block_only_ids']==['v']


def test_endpoint_and_no_overlap_fail_closed(comparison,monkeypatch):
    import src.api.main as api
    monkeypatch.setattr(api,'comparison_service',comparison)
    client=TestClient(api.app)
    response=client.get('/api/comparison?valid_date=2026-09-13&block=Igatpuri')
    assert response.status_code==200 and response.json()['summary']['count']==117
    assert client.get('/api/comparison?valid_date=2026-09-11').status_code==422
    live=Mock()
    live.fetch_forecast.return_value={'issued_date':'2027-01-01','forecast_days':[{'date':'2027-01-02','rainfall_mm':5.}]}
    with pytest.raises(ValueError,match='No overlapping'):ComparisonService(ForecastService(live=live)).compare()


def test_model_mismatch_is_not_attributed_to_sources(comparison):
    original=comparison.service.forecast
    def altered(**kwargs):
        result=deepcopy(original(**kwargs))
        if kwargs.get('mode')=='district':result['model_version']='different-model'
        return result
    service=Mock()
    service.forecast.side_effect=altered
    with pytest.raises(ValueError,match='Models differ'):ComparisonService(service).compare()
