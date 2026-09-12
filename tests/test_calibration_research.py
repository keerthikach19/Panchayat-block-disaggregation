import calendar
from copy import deepcopy
import numpy as np
import pytest
from src.ingestion.imd_history import decode
from src.modeling.calibration_contracts import align_pairs, reconcile

def test_binary_layout_endian_missing_and_leap_year():
    # Explicit binary-format unit fixture, not an observational training dataset.
    a=np.full((366,129,135),-999,dtype='<f4');a[:,30:100,40:120]=12.5
    result=decode(a.tobytes(),2024)
    assert result.shape==(366,129,135) and np.isnan(result[0,0,0])
    assert result[20,50,60]==12.5
    assert np.array_equal(decode(a.astype('>f4').tobytes(),2024),result,equal_nan=True)
    with pytest.raises(ValueError,match='length'):decode(a.tobytes(),2023)
    a[0,50,50]=-5
    with pytest.raises(ValueError,match='Invalid|invalid'):decode(a.tobytes(),2024)
    with pytest.raises(ValueError,match='length'):decode(b'<html>download failed</html>',2024)

def sample():
    obs={'location_id':'grid1','support_id':'IMD025','valid_start':'2024-07-01T03:00:00Z',
         'valid_end':'2024-07-02T03:00:00Z','target_kind':'gauge_based_gridded_analysis',
         'source_sha256':'a'*64,'rainfall_mm':10.}
    fc={**{k:v for k,v in obs.items() if k!='target_kind'},'source':'IMD',
        'issued_at':'2024-06-30T03:00:00Z','available_at':'2024-06-30T04:00:00Z',
        'features':[{'name':'antecedent_rain','value':5.,'available_at':'2024-06-30T02:00:00Z'}]}
    return fc,obs

def test_exact_pairs_do_not_guess_dates_or_spatial_support():
    fc,obs=sample();result=align_pairs([fc],[obs]);assert result['pairs'][0]['lead_hours']==24
    assert not result['unmatched_forecasts']
    wrong={**obs,'valid_start':'2024-07-01T00:00:00Z'}
    assert len(align_pairs([fc],[wrong])['unmatched_forecasts'])==1
    wrong={**obs,'support_id':'village1'}
    assert len(align_pairs([fc],[wrong])['unmatched_forecasts'])==1

def test_leakage_duplicates_and_unverified_targets_fail():
    fc,obs=sample()
    future=deepcopy(fc);future['features'][0]['available_at']='2024-07-02T04:00:00Z'
    with pytest.raises(ValueError,match='leakage'):align_pairs([future],[obs])
    with pytest.raises(ValueError,match='Duplicate'):align_pairs([fc,fc],[obs])
    with pytest.raises(ValueError,match='Duplicate'):align_pairs([fc],[obs,obs])
    with pytest.raises(ValueError,match='relabeled'):align_pairs([fc],[{**obs,'target_kind':'NASA_POWER_Blended'}])
    with pytest.raises(ValueError,match='Timezone'):align_pairs([{**fc,'issued_at':'2024-06-30'}],[obs])

def test_soft_reconciliation_preserves_inputs_and_aggregates_consistently():
    blocks=[{'rainfall_mm':10.,'area_m2':1.},{'rainfall_mm':30.,'area_m2':3.}]
    before=deepcopy(blocks)
    result=reconcile(blocks,50.,[1.,1.],1.)
    assert blocks==before
    assert result['district_value']==pytest.approx((result['block_values'][0]+3*result['block_values'][1])/4)
    assert 25<result['district_value']<50
    # Trusting district more shifts the solution toward its input, not an arbitrary gap cap.
    trusted=reconcile(blocks,50.,[1.,1.],100.)
    assert abs(trusted['district_value']-50)<abs(result['district_value']-50)
    coherent=reconcile(blocks,25.,[1.,1.],1.)
    assert coherent['block_values']==pytest.approx([10.,30.])
    with pytest.raises(ValueError):reconcile(blocks,50.,[0.,1.],1.)
