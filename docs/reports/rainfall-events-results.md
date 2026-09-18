# Rainfall model revision: measured results

Experiment: `rain-events-d46883949173f5fdf284`. All models and thresholds were frozen before the following evaluation.

The revised event classifier raises probability-based alerts separately from rainfall amounts. Detection is not overall accuracy. Most alerts are still false alarms; the revision is not suitable evidence of reliable village forecasting.

## Fresh Nashik 2025 audit

3,366 grid-days per lead, June–October. Not used in fitting, calibration or selection.

| Lead | Old detection | New alert detection | Hits / observed | False / all alerts | Precision | Old → new CSI |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 6.84% | 34.47% | 121 / 351 | 263 / 384 | 31.51% | 0.066 → 0.197 |
| 2 | 3.13% | 35.33% | 124 / 351 | 269 / 393 | 31.55% | 0.030 → 0.200 |
| 3 | 3.13% | 33.90% | 119 / 351 | 263 / 382 | 31.15% | 0.030 → 0.194 |
| 4 | 2.56% | 33.33% | 117 / 351 | 258 / 375 | 31.20% | 0.025 → 0.192 |
| 5 | 4.56% | 30.20% | 106 / 351 | 253 / 359 | 29.53% | 0.044 → 0.175 |

| Lead | Old → new MAE (mm) | Old → new RMSE (mm) | Old → new bias (mm) | New amount ≥20 mm detection |
|---|---:|---:|---:|---:|
| 1 | 6.56 → 8.20 | 15.99 → 15.60 | -4.70 → -0.34 | 20.51% |
| 2 | 6.72 → 8.25 | 16.14 → 15.76 | -4.72 → -0.43 | 19.94% |
| 3 | 6.78 → 8.25 | 16.20 → 15.85 | -4.76 → -0.48 | 19.37% |
| 4 | 6.80 → 8.31 | 16.24 → 15.93 | -4.78 → -0.41 | 17.38% |
| 5 | 6.83 → 8.20 | 16.29 → 15.96 | -4.74 → -0.69 | 15.38% |

## Reused Nashik 2022–2024 comparison

10,098 grid-days per lead, June–October. Previously examined years; not a fresh holdout.

| Lead | Old detection | New alert detection | Hits / observed | False / all alerts | Precision | Old → new CSI |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 4.61% | 28.89% | 288 / 997 | 727 / 1015 | 28.37% | 0.044 → 0.167 |
| 2 | 3.71% | 27.48% | 274 / 997 | 684 / 958 | 28.60% | 0.036 → 0.163 |
| 3 | 3.21% | 28.79% | 287 / 997 | 707 / 994 | 28.87% | 0.031 → 0.168 |
| 4 | 3.41% | 29.09% | 290 / 997 | 719 / 1009 | 28.74% | 0.033 → 0.169 |
| 5 | 4.41% | 27.98% | 279 / 997 | 714 / 993 | 28.10% | 0.043 → 0.163 |

| Lead | Old → new MAE (mm) | Old → new RMSE (mm) | Old → new bias (mm) | New amount ≥20 mm detection |
|---|---:|---:|---:|---:|
| 1 | 6.13 → 7.53 | 14.61 → 14.07 | -4.21 → -0.18 | 20.46% |
| 2 | 6.17 → 7.59 | 14.70 → 14.22 | -4.26 → -0.23 | 19.96% |
| 3 | 6.19 → 7.62 | 14.75 → 14.26 | -4.32 → -0.24 | 18.46% |
| 4 | 6.18 → 7.66 | 14.77 → 14.33 | -4.36 → -0.21 | 19.56% |
| 5 | 6.18 → 7.52 | 14.77 → 14.28 | -4.32 → -0.44 | 18.05% |

## Interpretation

Detection, CSI, RMSE and signed bias improve relative to the old selected absolute-loss model. MAE worsens. Alert precision remains low and there are substantially more false alerts. This is not an across-the-board improvement. The original experiment also had an unselected Tweedie candidate with better event skill than its selected absolute-loss model; the before/after tables compare against the selected model the application previously highlighted.

The combined validation target (recall ≥50%, precision ≥20%, false-positive rate ≤25%) was not met for any lead. The predeclared fallback maximized CSI; all five selected a 22.5% alert-probability threshold. A probability threshold is not a rainfall-amount threshold.

Saved reports also include persistence, event probability Brier scores, average precision, and every tested validation threshold. Per-case `.npz` files retain dates and grid IDs. No test-year tuning followed this evaluation.

[Method and reproduction](../RAINFALL_EVENT_MODEL.md) | [Machine-readable report](../../data/research/benchmarks/rain-events-d46883949173f5fdf284/evaluation-49c470f6091f0ac3/report.json)
