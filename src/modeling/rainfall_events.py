"""Causal rainfall features and separate amount/event verification.

An event alert is a probability decision, never a fabricated rainfall amount.
All observed predictors stop at target day minus lead minus availability lag.
"""
import numpy as np


def event_metrics(observed, alert):
    observed, alert = np.asarray(observed, bool), np.asarray(alert, bool)
    if observed.shape != alert.shape or observed.ndim != 1 or not observed.size:
        raise ValueError('Event arrays must be nonempty aligned vectors')
    hits = int(np.sum(observed & alert))
    misses = int(np.sum(observed & ~alert))
    false = int(np.sum(~observed & alert))
    correct = int(np.sum(~observed & ~alert))
    ratio = lambda a, b: a / b if b else None
    return dict(hits=hits, misses=misses, false_alarms=false, correct_negatives=correct,
                observed_events=hits + misses, alerts=hits + false,
                recall=ratio(hits, hits + misses), precision=ratio(hits, hits + false),
                false_alarm_ratio=ratio(false, hits + false),
                false_positive_rate=ratio(false, false + correct),
                csi=ratio(hits, hits + misses + false))


def choose_threshold(y, probability, policy):
    """Only development data may be passed here. Return every tested threshold."""
    p = np.asarray(probability)
    if not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError('Invalid event probabilities')
    rows = []
    for threshold in policy['probability_thresholds']:
        row = dict(threshold=threshold, **event_metrics(y, p >= threshold))
        row['constraints_met'] = (
            (row['recall'] or 0) >= policy['minimum_recall'] and
            (row['precision'] or 0) >= policy['minimum_precision'] and
            row['false_positive_rate'] is not None and
            row['false_positive_rate'] <= policy['maximum_false_positive_rate'])
        rows.append(row)
    eligible = [r for r in rows if r['constraints_met']] or rows
    best = max(eligible, key=lambda r: (r['csi'] or 0, r['precision'] or 0, r['threshold']))
    return best, rows


def amount_metrics(y, prediction):
    y, prediction = np.asarray(y, dtype=float), np.asarray(prediction, dtype=float)
    if y.shape != prediction.shape or not y.size or not np.isfinite([y, prediction]).all():
        raise ValueError('Amount arrays must be finite and aligned')
    err = prediction - y
    return dict(n=len(y), mae_mm=float(np.abs(err).mean()),
                rmse_mm=float(np.sqrt(np.mean(err ** 2))), bias_mm=float(err.mean()),
                observed_mean_mm=float(y.mean()), predicted_mean_mm=float(prediction.mean()),
                event_at_20mm=event_metrics(y >= 20, prediction >= 20))


def build_features(rain, dates, cells, lead, lag=2):
    """Neighbor predictors use only cells outside Nashik and its exclusion buffer."""
    if lead < 1 or lag < 0:
        raise ValueError('Invalid lead or lag')
    rain = np.asarray(rain)
    if len(dates) != len(rain) or rain.shape[1] != len(cells):
        raise ValueError('Data shape mismatch')
    if not np.all(np.diff(np.asarray(dates, dtype='datetime64[D]')) == np.timedelta64(1, 'D')):
        raise ValueError('Daily series must be continuous')
    times = np.arange(lead + lag + 14, len(dates))
    times = times[np.isin(dates.month[times], [6, 7, 8, 9, 10])]
    available = times - lead - lag
    n = len(cells)
    lat, lon = np.array([[c['lat'], c['lon']] for c in cells]).T
    values = [rain[available-k] for k in (0, 1, 2, 6, 13)]
    names = ['rain_last', 'rain_previous', 'rain_two_before', 'rain_six_before', 'rain_thirteen_before']
    means = {}
    for length in (3, 7, 14):
        means[length] = np.mean([rain[available-k] for k in range(length)], axis=0)
        values.append(means[length]); names.append(f'mean{length}')
    values += [np.broadcast_to(lat, (len(times), n)), np.broadcast_to(lon, (len(times), n)),
               np.broadcast_to(np.sin(2*np.pi*dates.dayofyear[times].to_numpy()/365.25)[:, None], (len(times), n)),
               np.broadcast_to(np.cos(2*np.pi*dates.dayofyear[times].to_numpy()/365.25)[:, None], (len(times), n))]
    names += ['latitude', 'longitude', 'season_sin', 'season_cos']
    # Preserve the original first twelve features for exact old-model replay.
    eligible = np.flatnonzero([not c['excluded_from_training'] for c in cells])
    if len(eligible) < 2:
        raise ValueError('Insufficient spatial context cells')
    distances = (lat[:, None]-lat[eligible])**2 + ((lon[:, None]-lon[eligible])*np.cos(np.deg2rad(lat[:, None])))**2
    distances[np.arange(n)[:, None] == eligible[None, :]] = np.inf
    neighbors = eligible[np.argsort(distances, axis=1)[:, :min(8, len(eligible)-1)]]
    for label, field in [('last', rain[available]), ('mean3', means[3]), ('mean7', means[7])]:
        values.append(np.mean(field[:, neighbors], axis=2)); names.append(f'neighbor_{label}')
    values += [np.mean(rain[available][:, neighbors] >= 20, axis=2),
               rain[available] - rain[available-1], means[3] - means[7],
               np.max([rain[available-k] for k in range(3)], axis=0)]
    names += ['neighbor_event_fraction', 'trend1', 'trend3_7', 'max3']
    return np.stack(values, axis=2).reshape(-1, len(names)).astype(np.float32), rain[times].reshape(-1), times, names
