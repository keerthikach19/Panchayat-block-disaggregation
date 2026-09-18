# Forecast-informed rainfall: measured results

**The joint 50% detection / 50% precision target was not achieved at any lead.**
The frozen choices improve event CSI over uncorrected GFS on leads 2–5, while lead 1 is worse.
Most observed ≥20 mm cases are still missed. Four leads have precision above 50%; lead 4 does not.
These results support a narrower claim of useful forecast information and some calibration gains, not validated village forecasting.

Final audit: 22 Nashik grid centers × 34 sampled initialization dates = **748 cases per lead**,
with no missing pairs. Target dates span June 2–September 13, 2026 across the five leads.
2026 IMD observations are provisional. Models, calibrations and thresholds were selected without Nashik
labels and frozen before this audit. See [method and reproducibility](../NWP_RAINFALL_MODEL.md).

## Event alerts

| Lead | Detection | Precision | Hits / observed | Misses | False / alerts | CSI |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 41.1% | 86.7% | 39 / 95 | 56 | 6 / 45 | 0.386 |
| 2 | 45.7% | 82.2% | 37 / 81 | 44 | 8 / 45 | 0.416 |
| 3 | 44.8% | 69.6% | 39 / 87 | 48 | 17 / 56 | 0.375 |
| 4 | 48.4% | 49.5% | 46 / 95 | 49 | 47 / 93 | 0.324 |
| 5 | 32.5% | 71.1% | 27 / 83 | 56 | 11 / 38 | 0.287 |

Detection = hits / actual ≥20 mm cases. Precision = hits / alerts. Neither is an overall
rainfall “accuracy percentage.” CSI = hits / (hits + misses + false alarms).
For example, lead 1 correctly alerts for 39 of 95 events, misses 56, and issues 6 false alerts.
Its 86.7% precision therefore does **not** mean it catches 86.7% of events.

## Same-case comparison with uncorrected GFS

| Lead | GFS → selected detection | GFS → selected precision | GFS → selected CSI |
|---|---:|---:|---:|
| 1 | 44.2% → 41.1% | 84.0% → 86.7% | 0.408 → 0.386 |
| 2 | 16.0% → 45.7% | 76.5% → 82.2% | 0.153 → 0.416 |
| 3 | 26.4% → 44.8% | 74.2% → 69.6% | 0.242 → 0.375 |
| 4 | 22.1% → 48.4% | 72.4% → 49.5% | 0.204 → 0.324 |
| 5 | 31.3% → 32.5% | 74.3% → 71.1% | 0.283 → 0.287 |

The earlier rainfall-history model was tested on 2025, so its numbers cannot establish a
controlled before/after improvement against these 2026 scores. Uncorrected GFS is the
matched baseline here. High precision on this sample is partly present in that baseline already.
The strongest event gain is lead 2: 13 → 37 hits with false alerts increasing from 4 to 8.
Lead 4 catches more events but produces substantially more false alerts. Lead 5 gains little in CSI.
These comparisons are descriptive; broad uncertainty prevents a claim of universal improvement.

## Rainfall amounts

All errors are in mm. Lower MAE/RMSE is better; bias closer to zero is better.
An event alert does not change the numeric amount estimate.

| Lead | MAE: GFS → selected | RMSE: GFS → selected | Bias: GFS → selected | Amount-based ≥20 mm detection |
|---|---:|---:|---:|---:|
| 1 | 7.43 → 7.19 | 22.60 → 22.13 | -3.87 → -5.36 | 29.5% |
| 2 | 6.63 → 6.03 | 20.17 → 17.80 | -3.80 → -3.27 | 28.4% |
| 3 | 6.23 → 6.23 | 15.93 → 15.93 | -4.67 → -4.67 | 26.4% |
| 4 | 8.50 → 8.50 | 25.86 → 25.86 | -5.96 → -5.96 | 22.1% |
| 5 | 8.93 → 6.76 | 31.06 → 18.06 | -1.57 → -2.97 | 22.9% |

Amount MAE and RMSE improve on leads 1, 2 and 5; leads 3 and 4 retain raw GFS.
Underprediction remains substantial. Bias worsens on leads 1 and 5 despite lower MAE/RMSE.
The validation constraints did not guarantee the same behavior in Nashik 2026.

## Uncertainty and frozen choices

| Lead | Detection: approximate 95% interval | Precision: approximate 95% interval | Event model | Probability threshold |
|---|---:|---:|---|---:|
| 1 | 10.9%–52.0% | 65.0%–100.0% | weather_classifier | 22.5% |
| 2 | 21.4%–61.9% | 69.2%–96.0% | weather_classifier | 15.0% |
| 3 | 8.3%–71.4% | 33.3%–86.0% | rain_only_logistic | 20.0% |
| 4 | 11.3%–81.1% | 14.4%–70.3% | weather_classifier | 12.5% |
| 5 | 0.0%–57.1% | 45.5%–90.6% | weather_classifier | 25.0% |

Intervals use a circular bootstrap of two adjacent initialization dates, preserving all
cells within each date (500 replicates, fixed seed). They are wide: only 34 initialization dates
and one partial season are available. Do not interpret an interval crossing 50% as passing the target.
None of the five leads met all joint event constraints on the 2025 selection set either.

The new approach supplies future atmospheric forecasts instead of only rainfall history, and
selects alerts separately from amount error. The same-case GFS comparison measures the added
value of the statistical correction. It does not isolate a causal benefit from every individual feature.
Improvement remains limited by the small sampled archive, geographic/year shift, storm-location
and timing errors in the forecast, and coarse/provisional target data; this experiment does not
measure the contribution of each limitation separately.

## Release and verification

No village-serving forecast or official IMD block input was replaced. The app presents this as
research evidence and explains detection, precision, false alerts and amount errors separately.
The saved-prediction test recomputes all reported metrics and frozen threshold decisions.
Timing, missing steps, date receipts, geographic exclusions and API evidence identity are tested.
An initial evaluator date-label reduction was corrected before the report was generated;
no fitted model, calibration coefficient or selected threshold changed.

Experiment: `nwp-model-badc5a9e1eb18c3ff1b4`  
Evaluation: `evaluation-2b37883a3571e9ee`  
Selection frozen: `2026-09-18T03:06:57.201824+00:00`  
Selection SHA-256: `63780088a6fad1b786f777947e3ce0def1a7072b503bc150bfcea757567b9096`

Sources: [NOAA GFS processed by dynamical.org, CC BY 4.0](https://dynamical.org/catalog/noaa-gfs-forecast/)
and [IMD daily provisional rainfall](https://imdpune.gov.in/cmpg/Realtimedata/Rainfall/Rain_Download.html).
Archive snapshot, observation receipts, checksums, candidate scores and prediction arrays accompany the experiment.
