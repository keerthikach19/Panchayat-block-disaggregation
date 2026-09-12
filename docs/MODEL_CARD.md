# Final model card — 12 September 2026

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

Historical analyses stop in 2024, while the supplied issued forecasts are from 2026; there are zero verified issued-forecast/observation pairs. An operational bias-calibration model cannot be honestly trained from those non-overlapping records. The alignment and reconciliation modules are implemented and tested, but do not invent missing training pairs or operational reconciliation weights.

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
