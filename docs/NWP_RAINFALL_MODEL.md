# Forecast-informed rainfall experiment

This iteration supplies actual archived weather forecasts to the rainfall model.
The previous experiment used rainfall history and season, which cannot describe
the atmospheric conditions forecast for an upcoming storm. The new inputs are
NOAA GFS rainfall, atmospheric precipitable water, 2 m relative humidity, nearby
forecast rainfall, coordinates and season. All weather inputs come from the same
initialization. Future observed rain is never a predictor.

See [measured results](reports/nwp-rainfall-results.md). This remains a research
experiment at 0.25° grid scale. It does not replace the map's official IMD parent
forecasts or establish accuracy at villages. The GFS correction must not be
applied to IMD block forecasts: they are different forecast products.

## Frozen experiment

| Stage | Years | Geography | Purpose |
|---|---|---|---|
| Fit | 2021–2023 | Maharashtra excluding Nashik and its 0.25° buffer | Amount and event models |
| Probability calibration | 2024 | Same exclusion | Logistic calibration of raw classifier scores |
| Model/threshold selection | 2025 | Same exclusion | Choose from the fixed candidate set |
| Final audit | 2026 | Nashik's 22 grid centers | Evaluate choices frozen before examining these scores |

Each development year uses 30 regularly spaced 00 UTC initializations, every five
days from May 31 to October 23. The final audit uses 34 initializations every three
days from May 31 to September 7, 2026. This is a sampled, partial-season audit,
not a complete daily operational evaluation. All available prescribed runs are
used; dates are not chosen based on observed rainfall. Missing inputs are dropped
and counted, never filled with zero. Nearby cells and dates are correlated.

The configuration is `config/nwp_experiment.json`. Selection is stored in
`data/research/benchmarks/nwp-model-badc5a9e1eb18c3ff1b4/selection.json`.
It includes model checksums, code hashes, package versions, all validation scores,
threshold sweeps and the freeze timestamp. `nwp_evidence.json` identifies the
separately versioned evaluation shown in the application.

Amount candidates are uncorrected GFS, GFS multiplied by a training-only rainfall
ratio, and a LightGBM Tweedie regressor. Selection minimizes RMSE among candidates
whose MAE does not exceed raw GFS and whose absolute bias is at most 20% of observed
mean rainfall; if none qualifies, raw GFS is retained. Event candidates are raw
GFS ≥20 mm, a logistic model using forecast rain alone, and a LightGBM classifier
using all 12 features. The two classifiers are calibrated on 2024 only.

Alert selection seeks **recall ≥50%, precision ≥50%, and false-positive rate
≤25%**, then maximizes CSI. If no choice meets all constraints, it selects maximum
CSI and explicitly records failure. The observed event threshold always remains
20 mm. Thresholds and candidates are never reselected on the 2026 audit. Amount
selection is independent: an alert does not force the rainfall estimate to 20 mm.

## Timing and rainfall conversion

The [NOAA GFS archive processed by dynamical.org](https://dynamical.org/catalog/noaa-gfs-forecast/)
contains historical forecast initializations. The experiment pins Icechunk snapshot
`FWTKVCTA0XJXBHS3F9K0` of its `v0.2.7` dataset, preserving the archived source
despite later updates. Attribution: NOAA NWS NCEP GFS processed by dynamical.org,
CC BY 4.0.

GFS `precipitation_surface` is a mean precipitation rate in kg m⁻² s⁻¹ over the
previous native forecast step. It is converted to mm by multiplying each rate by
its interval in seconds and summing. Native steps change from one hour to three
hours after hour 120. Tests reject missing steps and misaligned endpoints; units
and the archive's interval description are checked during acquisition.

IMD daily rain is labeled by the date ending at 03:00 UTC (08:30 IST). See the
[IMD report](https://mausam.imd.gov.in/chennai/mcdata/ne_monsoon_2020.pdf) and
[rainfall-data methodology](https://journals.ametsoc.org/view/journals/hydr/24/6/JHM-D-22-0160.1.xml).
Lead 1 therefore integrates initialization +27 through +51 hours; leads 2–5 shift
that exact 24-hour period by 24 hours each. For example, the May 31 initialization
predicts June 1 03 UTC to June 2 03 UTC for lead 1, matched to IMD's June 2 label.
These lead definitions must accompany the scores.

A decision time 12 hours after initialization is assumed to allow for forecast
production. Initialization is **not** a measured publication timestamp. Actual
historical dissemination times have not been independently verified, so this is
not proof that every run met a live delivery deadline.

## Observation provenance

Development targets use finalized IMD annual grids through 2025. Audit targets use
the [IMD daily real-time rainfall download](https://imdpune.gov.in/cmpg/Realtimedata/Rainfall/Rain_Download.html).
The 2026 grids are provisional and can change when annual analyses are finalized.
The receipt filename must match the requested date, the binary must have the
expected shape and plausible values, and hashes protect both raw and extracted
data. The pair builder verifies extracted values against each raw daily grid.

A control request for June 15, 2025 was compared with the finalized annual file
on the same grid centers: 400 of 423 values matched exactly, with mean absolute
difference 0.0318 mm. The audit is saved in
`data/research/audits/nwp-observation-window-check.json`. This checks extraction and
supports date consistency; it does not make provisional 2026 data final or provide
independent village observations.

Approximate 95% intervals use 500 circular block bootstrap replicates, sampling
two adjacent initialization dates at a time with all grid cells together. They
reflect some temporal/spatial dependence but do not establish skill across other
years or regions. Do not treat thousands of grid-day rows as independent storms.

## Reproduce

Use Python 3.13 and install `requirements-nwp.txt`. Annual observation arrays are
large ignored files; restore them with `scripts/acquire_maharashtra_history.py`
for 2010–2024 and 2025 if absent, matching the dataset IDs and cell metadata in the
configuration. Source manifests and frozen models/results are tracked.

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-nwp.txt
.venv/Scripts/python.exe scripts/acquire_nwp_history.py --kind gfs --workers 4
.venv/Scripts/python.exe scripts/acquire_nwp_history.py --kind observations --workers 2
.venv/Scripts/python.exe scripts/build_nwp_pairs.py
.venv/Scripts/python.exe scripts/train_nwp_calibration.py
.venv/Scripts/python.exe scripts/build_nwp_pairs.py --fresh
.venv/Scripts/python.exe scripts/evaluate_nwp_calibration.py --experiment-id nwp-model-badc5a9e1eb18c3ff1b4
.venv/Scripts/python.exe -m pytest tests -q
```

Fresh acquisition may produce a different checksum if provisional observations
are revised. Preserve the original cached files/manifests for exact replay; do
not overwrite the frozen evidence to hide revisions. Changing feature code,
configuration or training libraries produces a different experiment identity.
The packaged prediction NPZ files use plain numeric/Unicode arrays and open with
`allow_pickle=False`. The evidence tests recompute all published metrics and
alert decisions from these predictions and verify the model/file hashes.
