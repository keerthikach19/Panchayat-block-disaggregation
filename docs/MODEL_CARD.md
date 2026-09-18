# Model card — updated 18 September 2026

## Forecast-informed experiment: final iteration

The [GFS experiment](NWP_RAINFALL_MODEL.md) uses archived rainfall and moisture
forecasts, training on 2021–2023, calibrating on 2024 and selecting on 2025 outside
Nashik and its buffer. The frozen models were audited on 748 provisional 2026
Nashik grid-days per lead. Detection is 32.5–48.4%; precision is 49.5–86.7%.
**No lead reaches both 50% targets.** Against raw GFS on the same cases, event CSI
improves for leads 2–5 and worsens for lead 1. Amount MAE/RMSE improve for leads
1, 2 and 5; underprediction remains, and bias worsens for leads 1 and 5.

See [complete results, counts and uncertainty](reports/nwp-rainfall-results.md).
This is a sampled partial-season grid test, not village validation or a complete
operational archive. Forecast initialization and assumed delivery timing are
distinguished. The serving map remains unchanged; GFS corrections are not applied
to the different IMD block forecast product.

## Earlier rainfall-history experiment

The [revised experiment](RAINFALL_EVENT_MODEL.md) adds neighboring rainfall and
trends, Tweedie/squared-error amount candidates, and a separately calibrated
≥20 mm event classifier. Training uses 2010–2018, calibration 2019 and selection
2020–2021, excluding Nashik and its buffer throughout. The locked models were
audited on newly acquired 2025 observations.

On fresh Nashik 2025 grid-days, event detection is 30.2–35.3% across leads,
compared with 2.6–6.8% for the old selected model. Alert precision is 29.5–31.6%,
so most alerts are still false alarms. Day 1 bias improves from −4.70 to −0.34 mm
and RMSE from 15.99 to 15.60 mm, while MAE worsens from 6.56 to 8.20 mm.
These are tradeoffs, not uniformly better forecasts. Validation did not achieve
the combined event selection targets; the declared fallback selected maximum CSI.
See the [complete measured results](reports/rainfall-events-results.md).

The event output does not change rainfall amounts. No serving model is replaced:
this is a grid-scale research model with limited event skill and no matched
historical issued-forecast inputs or independent village observations.

## Release decision

Retain `terrain-631e5f007f8d4bca7a85` for the serving pipeline. The statewide historical training and evaluation are complete, but the candidate fails heavy-rain and operational-evidence checks. Application version 3.0.0 includes the full-weather improvements and this evidence; it does not silently activate the rejected candidate.

## Serving methods

| Target | Method | Evidence |
|---|---|---|
| Rainfall | Ridge-regression proxy climatology; village/parent area-normalized factor multiplied by official input | NASA POWER 6,120 records, 28 independent profiles, five Nashik profiles; later-period proxy RMSE 4.73 versus 5.93 mm/day regional mean; not local forecast accuracy |
| Maximum/minimum temperature | Copernicus DEM and −6.5°C/km lapse-rate adjustment relative to assumed parent footprint elevation | Physical assumption, no independent temperature validation |
| Humidity, wind, cloud | Inherit official parent source | No unsupported fine-scale variation; missing fields remain unavailable |

The unchanged-parent baseline remains packaged. Parent rainfall is assumed to represent an area mean over linked village footprints; the provider has not confirmed this. Temperature reference elevation is likewise assumed. The model does not infer current atmospheric circulation, inversions or localized storms.

## Completed Maharashtra experiment

Official IMD 0.25° daily rainfall analyses, 2010–2024: 5,479 days × 423 Maharashtra grid centres (2,317,617 grid-day values), including 22 Nashik centres. Zero missing extracted values. National files are preserved locally with SHA-256 manifests. Grid analyses are not independent village gauges.

Train: 2010–2018 outside Nashik and its 0.25° halo; validation: 2019–2021 outside the same halo; test: Nashik 2022–2024. June–October. Each lead has 524,637 training, 174,879 validation and 10,098 test rows. Neighbouring cells/days are correlated; row count is not independent sample size.

Features: lagged rain at 0/1/2/6/13 days before the availability cutoff, trailing 3/7/14-day means, latitude, longitude and seasonal sine/cosine. Cutoff is target minus lead minus a declared two-day availability lag. That lag is a retrospective assumption, not verified provider delivery timing.

Candidates: persistence, training-only regional monthly mean, LightGBM absolute loss and Tweedie loss. LightGBM uses 120 trees, 15 leaves, minimum 200 samples per leaf, learning rate 0.06, L2 10, seed 42, deterministic column-wise training and four threads. Validation MAE selects absolute loss for all five leads before inspecting the test. Selected models are saved as text; no production pointer is changed.

| Lead | Selected MAE | Persistence MAE | RMSE | Bias | Heavy ≥20 mm MAE | Heavy hits / events |
|---|---|---|---|---|---|---|
| 1 | 6.129 | 8.745 | 14.614 | -4.207 | 35.496 | 46 / 997 |
| 2 | 6.171 | 9.245 | 14.696 | -4.257 | 35.731 | 37 / 997 |
| 3 | 6.190 | 9.287 | 14.750 | -4.322 | 35.963 | 32 / 997 |
| 4 | 6.180 | 9.454 | 14.766 | -4.356 | 35.995 | 34 / 997 |
| 5 | 6.177 | 9.553 | 14.773 | -4.323 | 35.947 | 44 / 997 |

All errors are mm on held-out grid-days. MAE around 6 mm is not a promise of 6 mm operational error. The model misses 951–965 of 997 heavy-rain grid-days and predicts systematically low rain. Using more training data did not fix this objective/predictor mismatch. No confidence interval is claimed.

## Why district and block outputs can still differ

The two sources were issued on different days and may use different forecast products and accumulation intervals. Each route normalizes the terrain pattern against a different parent footprint. Equal terrain does not make atmospheric forecasts or parent references equal. Forcing a 6–10 mm maximum gap would hide disagreement without proving accuracy. The comparison preserves both predictions, original inputs, dates and numerical source/reference decomposition.

The supplied IMD block/district bulletins still lack verified, time-aligned local
observation pairs for operational calibration. The separate GFS experiment now
has matched historical forecast/IMD grid pairs, with an explicitly assumed
publication buffer and provisional 2026 test observations. These do not establish
calibration of the IMD block/district products or local village accuracy. No
operational reconciliation weights are invented.

## Reproduce

```powershell
.venv\Scripts\python scripts/acquire_maharashtra_history.py --start 2010 --end 2024
.venv\Scripts\python scripts/audit_calibration_readiness.py
.venv\Scripts\python scripts/benchmark_maharashtra_rainfall.py --dataset-version imd-mh-34a5f8f7716669bf2297
```

Frozen benchmark: `data/research/benchmarks/rain-benchmark-ad798db16fc9a58f9dc1/report.json`; per-lead reports preserve every candidate score and heavy-event count. Existing frozen output is verified by provenance and reused, not overwritten. Source manifests are in `data/research/manifests`. See requirements-dev.txt for pinned library versions.

## Sources

- [IMD daily gridded rainfall download](https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html), citing Pai et al. (2014), MAUSAM 65(1), 1–18.
- [Official Nashik district bulletin](https://imdagrimet.gov.in/Services/DistrictBulletin.php?state=Maharashtra&district=Nashik&language=English).
- [IMD GKMS SOP](https://mausam.imd.gov.in/imd_latest/contents/pdf/gkms_sop.pdf), section 6 informs the draft bulletin structure; it does not certify this application.
