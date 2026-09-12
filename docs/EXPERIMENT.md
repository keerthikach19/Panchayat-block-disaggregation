# Maharashtra benchmark — completed, candidate not promoted

Training and evaluation are complete. The selected models underpredict heavy rain
and are not substitutes for issued IMD forecasts. See [final model card](MODEL_CARD.md).
The application improvements from this branch are included in the final release;
this benchmark is retained as reproducible evidence. The original plan follows.

# Isolated Maharashtra calibration experiment

The working fallback remains `codex/nashik-hybrid` at `49ea992`, in the sibling
`nashik-hybrid` worktree. Its application is on port 8000. This experiment is
`codex/maharashtra-calibrated`, created from that exact commit, with its own Python
environment, inputs, caches and artifacts. Nothing is merged or promoted to the
fallback automatically. If an experimental server is needed, use port 8001.

## Work sequence

1. Acquire original IMD daily gridded rainfall with content hashes and strict
   shape/missing-value validation. Extract Maharashtra grid cells using the state
   polygon, retaining Nashik as a geographic holdout.
2. Establish a retrospective lagged-rainfall benchmark across 2010–2024, with
   fixed train/validation/test periods and five lead days. This tests whether
   daily dynamics generalize better than static seasonal climatology. It does not
   calibrate official forecasts and cannot establish village-scale accuracy.
3. Archive issued forecasts independently of their later observations. Validate
   issue/availability/accumulation intervals before joining training pairs. Never
   call NASA POWER location samples independent rain gauges.
4. Fit forecast-calibration models only when genuine paired records exist, then
   estimate shared-field reconciliation weights from development-set errors.
   Retain original source forecasts and expose all adjustments.
5. Evaluate independent Nashik observations before considering replacement of the
   working model. A smaller district/block difference alone is not a promotion gate.

The initial research benchmark deliberately uses only historical rainfall lags,
location and season. A two-day observation lag is a declared retrospective
assumption, not proof of real-time IMD archive availability. Dynamic atmospheric
forecast features and archived issue-time source predictions are still required
for the proposed operational calibration model.

## Data sources

- IMD 0.25° daily rainfall: https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html
  Cite Pai et al. (2014), MAUSAM 65(1), 1–18. Grid spacing is not village resolution.
- NOAA GEFS retrospective forecasts: https://www.psl.noaa.gov/forecasts/reforecast2/teleconn/
  Useful future forecast-pair source; a correction trained on GEFS is not
  automatically transferable to IMD products.
- NASA IMERG: https://gpm.nasa.gov/data/imerg — auxiliary estimates, not gauge truth.

No future truth, synthetic observations or source-agreement target is used as an
observational training label. Source download failures must remain visible.

## Commands (run from this worktree)

```powershell
.venv\Scripts\python scripts/acquire_maharashtra_history.py --start 2010 --end 2024
.venv\Scripts\python scripts/audit_calibration_readiness.py
.venv\Scripts\python scripts/benchmark_maharashtra_rainfall.py --dataset-version <version-printed-by-acquisition>
.venv\Scripts\python -m pytest tests/test_calibration_research.py -q
```

The acquisition uses IMD's public annual-download form with two concurrent
downloads. It validates leap-year size, endian order, the documented -999 missing
sentinel and rainfall ranges before accepting a file. Existing files are checked
against recorded hashes rather than overwritten. Raw national files and extracted
arrays are local, ignored research inputs; manifests, source hashes, benchmark
reports and selected model text are tracked. Re-download with the same script on
another checkout and verify recorded hashes before reproducing a benchmark.

The initial benchmark compares persistence, a training-only regional monthly
mean, LightGBM absolute loss and LightGBM Tweedie loss. Candidate selection uses
2019–2021 validation outside Nashik and its exclusion halo. Nashik 2022–2024 test
results are computed only after selection; they do not select the winner. Every
report keeps heavy-rain misses/false alarms alongside average errors. This
research benchmark never writes a production activation pointer.

`align_pairs` requires matching location, geographic support and timezone-aware
accumulation intervals; source hashes and predictor availability are mandatory.
The current date-only five-day exports cannot pass this contract without further
source information. `reconcile` minimizes weighted changes to block estimates and
the district aggregate with nonnegative outputs. Its weights must be estimated
from development-set forecast errors; no default operational weights are claimed.
