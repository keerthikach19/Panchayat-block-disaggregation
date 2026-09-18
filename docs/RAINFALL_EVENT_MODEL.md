# Revised rainfall experiment

The original absolute-loss model substantially underpredicted rain and missed most
grid-days with at least 20 mm. The revised experiment trains **two outputs**:

- An amount estimate in mm, selected using RMSE with bias and MAE constraints.
- A probability of rainfall reaching 20 mm, with a validation-selected alert threshold.

The amount is never raised to 20 mm merely because an alert is issued. Detection
of alerts and detection from amount estimates are reported separately.

## Reproduce

Install `requirements-dev.txt`. Restore the original hash-verified rainfall array
using `scripts/acquire_maharashtra_history.py --start 2010 --end 2024` if absent.
The raw arrays are ignored by git; the source manifests are tracked.

```powershell
.venv/Scripts/python.exe scripts/acquire_maharashtra_history.py --start 2025 --end 2025
.venv/Scripts/python.exe scripts/train_rainfall_events.py --stage train
.venv/Scripts/python.exe scripts/train_rainfall_events.py --stage evaluate --fresh-dataset imd-mh-ab17f6679502dc028f18
```

The fresh dataset identifier printed by acquisition depends on the source and
boundary files. Use the printed identifier if it differs. Evaluation verifies
that its grid cells and spatial exclusion flags match the original dataset.

To evaluate the packaged frozen models without training again:

```powershell
.venv/Scripts/python.exe scripts/train_rainfall_events.py --stage evaluate --experiment-id rain-events-d46883949173f5fdf284 --fresh-dataset imd-mh-ab17f6679502dc028f18
```

See [measured results](reports/rainfall-events-results.md). During evaluation,
the original-model replay check caught an omitted nonnegative clamp. The scorer
was corrected to match the original benchmark; no trained weights, calibration
or thresholds changed. The original training source and feature source are
archived beside the frozen selection, and the report records the evaluation
code hash separately.

Evaluation outputs are versioned independently under `evaluation-*/`. The
`event_evidence.json` pointer identifies the report shown by the app. Prediction
archives in the current evaluation use plain numeric and Unicode arrays and can
be opened with `numpy.load(..., allow_pickle=False)`. Earlier scorer outputs are
retained for provenance; the current output corrects date-array serialization
without changing model choices or numeric results.

`config/rainfall_event_experiment.json` fixes the models and selection rules.
Code hashes, library versions and the dataset checksum contribute to experiment
identity. Saved model checksums, calibration coefficients and thresholds are
frozen in `selection.json` before evaluation starts. The original benchmark is
retained and its saved models are replayed to check the old scores.

## Data separation

| Stage | Years | Geography | Purpose |
|---|---|---|---|
| Training | 2010–2018 | Maharashtra excluding Nashik and its buffer | Fit amount and event models |
| Probability calibration | 2019 | Same training geography | Fit logistic calibration on raw event scores |
| Selection | 2020–2021 | Same training geography | Choose amount model and event alert threshold |
| Reused comparison | 2022–2024 | Nashik | Before/after comparison on previously examined years |
| Fresh audit | 2025 | Nashik | First evaluation of the frozen revised models on this year |

Only June–October target dates are scored. Training discards 2022 onward before
feature construction. No test labels choose model parameters or alert thresholds.
The fresh year remains a one-year test at grid scale, not independent station or
village validation. Grid-days may belong to the same storm and are not independent
storm events.

## Changes

Amount candidates use Tweedie and squared-error objectives. Selection minimizes
RMSE among candidates whose absolute bias is at most 20% of the observed mean
and whose MAE does not exceed persistence on selection data. If no candidate
passes, minimum RMSE is used and the failed constraints are reported.

The event classifier uses unweighted binary loss. Logistic probability calibration
uses 2019 only. The alert threshold maximizes critical success index (CSI), aiming
for recall ≥50%, precision ≥20%, and false-positive rate ≤25% on selection data.
These are experimental selection constraints, not production acceptance criteria.
If none pass, maximum CSI is used and the constraint failure is reported.

Features add neighboring rainfall, recent maxima and trends to the original
lagged rainfall, coordinates and seasonal cycle. Neighbor features exclude cells
in Nashik and its buffer. All observed inputs stop at the target date minus the
lead time minus the assumed two-day observation delay. Tests perturb future
observations to verify that earlier features cannot change.

## Reading the results

- Recall: hits / observed ≥20 mm cases.
- Precision: hits / alerts. The remaining alerts are false alarms.
- CSI: hits / (hits + misses + false alarms). Reporting CSI prevents an always-alert
  strategy from appearing successful merely because it has 100% recall.
- False-positive rate: false alarms / actual below-20 mm cases. This differs from
  false-alarm ratio, which divides by all alerts.
- Brier score and average precision evaluate event probabilities beyond one alert
  threshold. Brier score is compared with a constant training-frequency baseline.
- MAE, RMSE and signed bias evaluate amount estimates separately.

The report includes every lead and both evaluation periods. Compressed per-case
predictions retain observed rainfall, original and revised amounts, event
probabilities, alerts, dates and grid IDs for inspection.

## Application behavior

`event_evidence.json` selects the revised **evidence report**, not the map's serving
model. The Model & training page displays before/after scores, false alarms and
the distinction between amount predictions and event alerts.

The project still lacks historical issued-forecast/observation pairs and verified
local gauge observations. This experiment adds no NWP inputs and does not claim
operational observation availability or village-scale accuracy. A model relying
on past rain alone cannot be assumed to predict approaching weather systems.
