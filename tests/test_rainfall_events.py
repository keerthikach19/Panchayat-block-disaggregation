import numpy as np
import pandas as pd
import pytest
from src.modeling.rainfall_events import build_features, choose_threshold, event_metrics, amount_metrics


def test_event_counts_include_false_alarms_and_threshold_boundary():
    score = amount_metrics(np.array([0., 19., 20., 50.]), np.array([0., 21., 20., 10.]))
    event = score['event_at_20mm']
    assert (event['hits'], event['misses'], event['false_alarms'], event['correct_negatives']) == (1, 1, 1, 1)
    assert event['recall'] == .5 and event['precision'] == .5
    assert event['csi'] == pytest.approx(1/3)
    assert score['bias_mm'] == -9.5
    empty = event_metrics([False, False], [False, False])
    assert empty['recall'] is None and empty['precision'] is None


def test_threshold_selection_cannot_win_by_alerting_every_day():
    y = np.array([1, 1, 0, 0, 0, 0, 0, 0], bool)
    p = np.array([.8, .4, .6, .2, .1, .1, .1, .1])
    policy = dict(probability_thresholds=[0., .3, .7], minimum_recall=.5,
                  minimum_precision=.5, maximum_false_positive_rate=.25)
    selected, sweep = choose_threshold(y, p, policy)
    assert selected['threshold'] == .3 and selected['constraints_met']
    assert not sweep[0]['constraints_met']
    policy['minimum_recall'] = 1.
    policy['minimum_precision'] = 1.
    selected, _ = choose_threshold(y, p, policy)
    assert not selected['constraints_met']
    with pytest.raises(ValueError):
        choose_threshold(y, p*2, policy)


def test_features_never_read_future_rain_or_holdout_neighbors():
    dates = pd.date_range('2020-05-01', '2020-06-30')
    cells = [dict(lat=19.+i*.25, lon=74., excluded_from_training=(i == 3)) for i in range(4)]
    rain = np.random.default_rng(4).uniform(0, 40, (len(dates), len(cells)))
    X, _, times, names = build_features(rain, dates, cells, lead=3, lag=2)
    cutoff = times[0]-5
    perturbed = rain.copy(); perturbed[cutoff+1:] = 999.
    later, _, _, _ = build_features(perturbed, dates, cells, lead=3, lag=2)
    np.testing.assert_array_equal(X[:4], later[:4])
    perturbed = rain.copy(); perturbed[:, 3] = 888.
    excluded, _, _, _ = build_features(perturbed, dates, cells, lead=3, lag=2)
    neighbor_cols = [i for i, name in enumerate(names) if name.startswith('neighbor_')]
    np.testing.assert_array_equal(X[:, neighbor_cols], excluded[:, neighbor_cols])
    assert X[0, 0] == pytest.approx(rain[cutoff, 0])
    with pytest.raises(ValueError, match='continuous'):
        build_features(rain[:-1], dates.delete(10), cells, 3)
