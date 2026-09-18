import numpy as np
import pandas as pd
import pytest
from src.ingestion.forecast_schema import ROOT,read_json
from src.ingestion.nwp_archive import integrate_window,decode_daily,verify_daily_receipt,initialization_dates
from src.modeling.nwp_calibration import window_times,forecast_features,development_masks


@pytest.fixture
def config():
    return read_json(ROOT/'config/nwp_experiment.json')


def test_rate_integration_handles_hourly_to_three_hourly_transition():
    hours=np.r_[np.arange(121),np.arange(123,151,3)]
    rate=np.full((len(hours),2),2/3600.)
    assert integrate_window(hours,rate,99,123)==pytest.approx([48.,48.])
    assert integrate_window(hours,rate,123,147)==pytest.approx([48.,48.])
    rate[hours==123,0]=np.nan
    assert np.isnan(integrate_window(hours,rate,99,123)[0])
    with pytest.raises(ValueError,match='endpoints'):integrate_window(hours,rate,100,124)
    with pytest.raises(ValueError,match='axis'):integrate_window([0,1,1],np.ones((3,2)),0,1)
    with pytest.raises(ValueError,match='Missing native'):integrate_window(np.delete(hours,30),np.delete(rate,30,axis=0),27,51)


def test_exact_imd_dates_and_leads(config):
    init,decision,start,end=window_times('2024-05-31T00:00Z',1,config)
    assert str(start)=='2024-06-01 03:00:00+00:00'
    assert str(end)=='2024-06-02 03:00:00+00:00'
    assert decision < start and (start-init).total_seconds()==27*3600
    assert window_times('2024-05-31T00:00Z',5,config)[3].strftime('%Y-%m-%d')=='2024-06-06'
    with pytest.raises(ValueError,match='cycle'):window_times('2024-05-31T06:00Z',1,config)
    with pytest.raises(ValueError):window_times('2024-05-31',6,config)


def test_feature_window_is_not_contaminated_by_other_steps(config):
    hours=np.r_[np.arange(121),np.arange(123,151,3)]
    cells=[dict(lat=20+i*.25,lon=74.) for i in range(3)]
    payload={'lead_hours':hours,'precipitation_surface':np.full((len(hours),3),1/3600.),
             'precipitable_water_atmosphere':np.full((len(hours),3),40.),'relative_humidity_2m':np.full((len(hours),3),80.)}
    X,good,date=forecast_features(payload,'2024-05-31',1,cells,config)
    assert good.all() and date=='2024-06-02' and np.allclose(X[:,0],24.)
    payload['precipitation_surface'][hours>51]=999
    again,_,_=forecast_features(payload,'2024-05-31',1,cells,config)
    np.testing.assert_array_equal(X,again)
    payload['relative_humidity_2m'][hours==30,0]=np.nan
    _,good,_=forecast_features(payload,'2024-05-31',1,cells,config)
    assert not good[0]


def test_no_nashik_or_future_labels_enter_development(config):
    years=np.array([2021,2022,2023,2024,2025,2026,2021])
    masks=development_masks(years,np.array([0,0,0,0,0,0,1]),config)
    assert masks['train'].tolist()==[True,True,True,False,False,False,False]
    assert not any(m[5] or m[6] for m in masks.values())
    changed={**config,'selection_years':[2024]}
    with pytest.raises(ValueError,match='Overlapping'):development_masks(years,np.zeros(7),changed)
    dates=initialization_dates(config,fresh=True)
    assert dates[0]==pd.Timestamp('2026-05-31') and dates[-1]<=pd.Timestamp('2026-09-09')


def test_daily_binary_and_response_date_fail_closed():
    grid=np.full((129,135),-999.,dtype='<f4');grid[40:90,40:90]=10.
    a=decode_daily(grid.tobytes());assert a[50,50]==10 and np.isnan(a[0,0])
    with pytest.raises(ValueError,match='length'):decode_daily(b'<html>Missing date</html>')
    info={'date':'2026-06-02','response_headers':{'Content-disposition':'attachment; filename=rain_ind0.25_26_06_02.grd'}}
    verify_daily_receipt(info,'2026-06-02')
    with pytest.raises(ValueError,match='date'):verify_daily_receipt(info,'2026-06-03')
