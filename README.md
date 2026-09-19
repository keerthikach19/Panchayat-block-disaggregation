# Nashik Village Weather Downscaling

(Deployement link: https://panchayat-block-disaggregation.onrender.com)

A weather dashboard and rainfall research project for exploring how forecasts
issued for a block or district can be represented at village scale in Nashik,
Maharashtra.

The application combines official India Meteorological Department (IMD) forecast
inputs, village boundaries, elevation data and an experimental terrain model.
Users can explore weather on a map, compare official source values with village
estimates, inspect how each value was calculated, and generate printable advisory
drafts. A separate research workflow evaluates rainfall models against historical
gridded observations.

**Downscaling** here means applying a documented local adjustment to a forecast
for a larger area. It does not mean that weather has been measured in each village
or that local forecast accuracy has been established. This is an academic
prototype: the map's estimates are experimental and its advisory messages are
previews, rather than an operational warning service.

## Contents

- [What you can do](#what-you-can-do)
- [Run locally](#run-locally)
- [Using the dashboard](#using-the-dashboard)
- [How the application works](#how-the-application-works)
- [Data sources and coverage](#data-sources-and-coverage)
- [Rainfall modeling and evaluation](#rainfall-modeling-and-evaluation)
- [Measured rainfall results](#measured-rainfall-results)
- [Managing forecast data](#managing-forecast-data)
- [Reproduce the rainfall research](#reproduce-the-rainfall-research)
- [Project structure and API](#project-structure-and-api)
- [Testing](#testing)
- [Deployment](#deployment)
- [Limitations](#limitations)
- [Documentation and sources](#documentation-and-sources)

## What you can do

| Feature | Purpose |
|---|---|
| Village forecast map | Explore rainfall, maximum/minimum temperature, maximum/minimum humidity and wind speed |
| Source and local views | Compare the official parent forecast with experimental rainfall and temperature estimates |
| Village details | Inspect dates, source values, adjustments, elevation, units and provenance |
| Block and district modes | Use packaged official block tables or retrieve the public IMD district bulletin |
| Model & training | Inspect research methods, rainfall errors, event detection, false alarms and uncertainty |
| Printable bulletin | Generate a five-day GKMS-style advisory draft with source and local weather |
| Message preview | Review advisory text locally without sending messages |

The supported application geography is **Nashik**. The packaged demonstration
contains forecasts for 15 blocks and 1,916 linked village polygons. Although some
filenames and API routes use `panchayat`, the geometries are village polygons;
a verified village-to-gram-panchayat crosswalk is not available.

## Run locally

Use **Python 3.13** and **Node.js 22 with npm**. The backend uses FastAPI and
Uvicorn; the frontend uses React, Vite and Leaflet. Research workflows additionally
use NumPy, pandas, scikit-learn, LightGBM and geospatial libraries.

### Windows quick start

From the repository root:

```powershell
.\Start-Project.ps1 -Setup
```

For subsequent runs, use `.\Start-Project.ps1`. Use
`.\Start-Project.ps1 -Port 8001` if port 8000 is occupied, and Ctrl+C to stop the
server. Setup installs dependencies and builds the frontend; startup uses
packaged forecast artifacts and does not train models.

### Manual setup

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
cd frontend
npm ci
npm run build
cd ..
.venv\Scripts\python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Open [the application](http://127.0.0.1:8000) or [API documentation](http://127.0.0.1:8000/docs).
The demonstration data has passed import validation and is already packaged;
no import or model training is required at startup. Linux/macOS equivalents use
`.venv/bin/python`. FastAPI serves the built frontend and API from the same address.
Rebuild after editing frontend source.

Use Python 3.13 to reproduce the recorded research environment. Runtime, testing
and forecast-archive dependencies are separated:

| Dependency file | Purpose |
|---|---|
| `requirements.txt` | Run the API and packaged dashboard |
| `requirements-dev.txt` | Run the test suite and existing modeling/GIS research |
| `requirements-nwp.txt` | Add the pinned xarray, Icechunk and Zarr packages for GFS archive acquisition; includes development dependencies |

The dashboard reads saved research reports. Downloading the GFS archive or
installing the archive-specific dependencies is not required just to view them.

If the Windows npm wrapper cannot locate its installation, invoke the npm CLI
directly from `frontend` (adjust the installation path if necessary):

```powershell
node 'C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js' ci
node 'C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js' run build
```

## Using the dashboard

The dashboard has two tabs: **Forecast map** and **Model & training**.

### Forecast map

1. Choose **Official block forecasts** or **Live district forecast**.
2. Select a forecast day and, optionally, a block.
3. Choose one of the six weather variables.
4. Click a village polygon or select a village from the dropdown.
5. For rainfall and temperature, compare **Source input (Before)** with
   **Local estimates (After)** and inspect the village details.

The page shows the issue date, validity period, selected date, source coverage and
whether the forecast is current, upcoming or archived. Opening an old demonstration
does not make it a current forecast. Gray map features indicate unavailable values.
Optional street-map labels require internet access and are disabled by default.

**Official block forecast** is the selected parent value; **Village estimate** is
the experimental value after terrain adjustment. For Vanasgaon on 11 September
2026, the packaged source rainfall is 1.40 mm and the village estimate is 1.38 mm.
The 0.02 mm difference is a model adjustment, not a measured gain in accuracy.
Expand **How elevation and terrain change the estimate** to inspect the inputs.

Humidity and wind are shown as values from the official forecast, without local
adjustment. Villages in the same block share the selected block's values; district
mode shares the district's values.

### Model evidence, bulletins and previews

**Model & training** explains the map's serving method and displays separate
GFS rainfall research results. Its tables show the selected model's direct MAE,
RMSE, bias, amount-based detection, event recall, precision and false-alert ratio.
**Training, test coverage and uncertainty** expands the split, forecast-window
definition and approximate 95% intervals. Detection, alert precision and
rainfall-amount errors measure different aspects of performance; definitions
accompany the tables.

On the forecast map, **Village model evaluation** describes the terrain model's
seasonal-pattern evaluation. Expand **Seasonal-pattern evaluation** to view its
MAE and RMSE. These seasonal scores and the GFS research scores evaluate different
methods and targets; neither measures daily village forecast accuracy.

A village's bulletin link opens a printable five-day GKMS-style draft. Advisory
text follows transparent weather rules, such as reviewing spraying/drainage when
rainfall reaches 20 mm or inspecting for moisture-related symptoms under high
humidity. This is not a crop-stage model or a confirmed pest/disease diagnosis.
Field conditions and crop stage require local review.

**Preview message** generates text locally. No SMS, WhatsApp or mKisan message is
sent, and no officer approval or official advisory status is claimed.

## How the application works

The application has a forecast-serving workflow and a separate research workflow:

```text
FORECAST SERVING
Official block CSVs -> validate and import -> packaged block runs --+
                                                                  +-> terrain adjustment
Public district bulletin -> retrieve, parse and cache -------------+
    -> join village geometry -> FastAPI -> map, details and draft bulletins

RAINFALL RESEARCH
Archived GFS forecasts + IMD gridded observations
    -> align locations and rainfall periods
    -> fit models -> calibrate probabilities -> select on development data
    -> freeze choices -> evaluate held-out cases
    -> save reports and predictions -> Model & training
```

### Sources, runs and traceability

Block CSV import validates filenames, titles, dates, labels, numeric ranges and
duplicate/conflicting records. Original input bytes are preserved. Accepted
records are normalized and used to build versioned forecast runs. Activation
changes a pointer while retaining earlier runs.

District mode retrieves the public bulletin on request and maintains a separate
cache. Issue date, validity date and download time are distinct fields. Cache use,
retrieval failures and archived forecasts are explicitly labeled. District data
never silently replaces missing block data.

Forecast requests select a source mode, run and date. Outputs retain source
values, model version, geographic association and adjustment details. Unresolved
geographic associations are excluded rather than guessed. Normal startup, data
filtering and API reads do not train models or overwrite source CSVs.

### The terrain model used by the map

| Variable | Method |
|---|---|
| Rainfall | Multiply parent rainfall by a village factor from a ridge model of seasonal climate patterns, normalized over linked village areas |
| Maximum/minimum temperature | Apply a fixed −6.5°C/km elevation adjustment using Copernicus village elevation relative to an assumed parent reference |
| Humidity and wind speed | Copy the official parent forecast without creating local variation |
| Unavailable fields | Preserve missingness rather than fabricate values |

Rainfall factors are normalized so that the area-weighted village mean reproduces
parent rainfall to rounding tolerance. Zero parent rainfall remains zero. This
assumes the parent forecast is an area mean over the linked village footprints;
the provider has not verified that interpretation.

Temperature adjustments assume the parent reference is the area-weighted elevation
of the linked footprint. Both maximum and minimum temperature receive the same
adjustment. Actual source reference heights are unknown, and inversions or other
atmospheric conditions can invalidate a fixed lapse rate.

The ridge model uses deduplicated NASA POWER seasonal climatology. Its evaluation
measures reconstruction of gridded climate patterns, **not daily forecast accuracy
at villages**. Copernicus elevation is a physical adjustment input, not proof that
the adjusted forecast is more accurate. An unchanged-parent baseline is also
available through the API/build workflow.

The rainfall research models are not loaded as the map's forecasting method.
In particular, a correction fitted to GFS cannot be assumed to calibrate the
different IMD block or district product. Changing the research report displayed
in the dashboard does not change village forecasts.

## Data sources and coverage

| Data | Role | Interpretation |
|---|---|---|
| Manually imported official IMD block tables | Default forecast source | Five-day parent forecasts; original CSV values retained |
| Public IMD district bulletin | Separate district source | Retrieved/cached on request; depends on external availability |
| Village polygons and covariates | Map geometry and parent associations | Village geometry, not verified gram-panchayat boundaries |
| Copernicus DEM | Village elevation | Digital surface model, not a perfect bare-earth terrain model |
| NASA POWER records | Serving model's climate-pattern proxy | Gridded data, not verified local AWS observations |
| IMD annual 0.25° rainfall analyses | Historical research targets | Gridded observations, not independent village gauges |
| IMD provisional daily rainfall | 2026 audit targets | Can change when finalized analyses become available |
| NOAA GFS archive processed by dynamical.org | Research forecast inputs | Archived forecast runs, separate from the IMD forecasts on the map |

The packaged block demonstration was issued **10 September 2026**, valid
**11–15 September 2026**. It includes 15 accepted CSVs, 75 block-day records and
9,580 village-date outputs. Of 1,953 geographic features, 1,916 are linked and
37 are excluded because their parent associations are unresolved. Coverage and
source warnings appear in the UI and import/geography reports.

Parent matching uses canonical source labels and explicit aliases. It has not
been independently confirmed using development-block boundary containment.
See the [implementation handoff](docs/HANDOFF.md) for per-block counts and details.

The legacy training table contains 6,120 NASA POWER records but only 28 distinct
weather profiles statewide and five in Nashik. Deduplication prevents repeated
profiles from being treated as independent stations. Those records must not be
presented as a network of verified local weather observations.

## Rainfall modeling and evaluation

The current research workflow estimates rainfall amounts and ≥20 mm event
probabilities separately, using **issued numerical weather forecasts**: NOAA GFS
rainfall, precipitable water and relative humidity, together with nearby forecast
rainfall, coordinates and season. All weather features come from the same
forecast initialization. Future observed rainfall is never an input. This gives
the model information about forecast atmospheric conditions. The experiment does
not isolate the causal contribution of every individual feature.

This workflow replaces rainfall history alone as the focus of the research
evaluation. The earlier approach and its scores are retained in the
[rainfall-history method](docs/RAINFALL_EVENT_MODEL.md) and
[results archive](docs/reports/rainfall-events-results.md).

### Development and independent evaluation

| Stage | Years | Geography | Purpose |
|---|---|---|---|
| Model fitting | 2021–2023 | Maharashtra excluding Nashik and its 0.25° buffer | Fit amount and event candidates |
| Probability calibration | 2024 | Same geographic exclusion | Calibrate classifier scores |
| Model and threshold selection | 2025 | Same geographic exclusion | Select candidates and alert thresholds |
| Final audit | 2026 | 22 Nashik grid centers | Evaluate frozen choices on previously unevaluated cases |

The development archive has 30 initializations per year, every five days from
May 31 to October 23, for 150 runs. The final audit uses 34 initializations, every
three days from May 31 to September 7, 2026. All are 00:00 UTC runs. Across the
five leads, audit observation dates span June 2–September 13, 2026; 104 daily IMD
grids were acquired. The configured sampling produced **748 Nashik grid-day
cases per lead**, with no missing pairs in this run.

This is a regularly sampled partial-season evaluation, not a complete daily
operational evaluation. One case is one 0.25° grid cell on one date. Neighboring
cells and dates may belong to the same storm, so 748 rows are not 748 independent
weather events. Development uses finalized annual IMD grids; the 2026 daily grids
are **provisional** and may differ from subsequent finalized analyses.

### Matching forecast and observation time

IMD daily rainfall is labeled by the date on which its 24-hour period ends at
03:00 UTC, or 08:30 IST. GFS precipitation rates are integrated over that exact
period. Lead 1 covers initialization +27 to +51 hours; each later lead shifts
the window by 24 hours. For example, the May 31 initialization's lead 1 covers
June 1 03:00 UTC to June 2 03:00 UTC and is matched to IMD's June 2 observation.

GFS rates are converted to rainfall amounts using each native interval's duration.
The code handles hourly steps through hour 120 and three-hourly steps thereafter.
Missing steps, mismatched endpoints and unexpected units are rejected; missing
values are not silently changed to zero. Daily IMD response filenames must match
the requested dates, and extracted observations are checked against the raw grids.

A 12-hour decision buffer after forecast initialization is assumed. Actual
historical publication timestamps are not independently verified. Initialization
time must not be interpreted as measured availability time. The archived GFS
dataset is pinned to Icechunk snapshot `FWTKVCTA0XJXBHS3F9K0`, version `v0.2.7`.

### Model candidates and selection

Rainfall amount candidates are uncorrected GFS, GFS scaled by a training-only
rainfall ratio, and a LightGBM Tweedie regressor. Selection minimizes RMSE among
candidates whose MAE does not exceed raw GFS and whose absolute bias is no more
than 20% of the observed mean. If none qualifies, raw GFS is retained.

Event candidates are raw GFS rainfall ≥20 mm, a logistic classifier using forecast
rain alone, and a LightGBM classifier using all 12 features. The classifiers are
calibrated using 2024 data. Selection aims for recall ≥50%, precision ≥50% and
false-positive rate ≤25%, then maximizes critical success index (CSI). If no
candidate/threshold meets all constraints, it selects maximum CSI and explicitly
records the failed target. None of the five leads met all joint constraints on
the 2025 selection set.

The observed event definition always remains **rainfall ≥20 mm**. A probability
threshold is a decision about raising an alert, not a replacement rainfall
threshold. An alert never forces the numeric amount estimate to 20 mm. All model
choices, calibrations and thresholds were frozen before the 2026 audit and were
not retuned after its results were examined.

The frozen choices used for the displayed evaluation are:

| Lead | Rainfall amount model | Event probability model |
|---|---|---|
| 1 | LightGBM Tweedie | LightGBM classifier |
| 2 | LightGBM Tweedie | LightGBM classifier |
| 3 | Uncorrected GFS | Rain-only logistic classifier |
| 4 | Uncorrected GFS | LightGBM classifier |
| 5 | LightGBM Tweedie | LightGBM classifier |

The event classifiers use the separate probability calibration and alert
threshold selected for each lead.

## Measured rainfall results

**No lead achieved both 50% detection and 50% precision on the 2026 audit.**
The following are measured point estimates on the sampled Nashik grid-days,
not village-level accuracy claims.

| Lead | Detection / recall | Precision / alerts correct | Hits / actual ≥20 mm cases | Missed cases | False / all alerts | CSI |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 41.1% | 86.7% | 39 / 95 | 56 | 6 / 45 | 0.386 |
| 2 | 45.7% | 82.2% | 37 / 81 | 44 | 8 / 45 | 0.416 |
| 3 | 44.8% | 69.6% | 39 / 87 | 48 | 17 / 56 | 0.375 |
| 4 | 48.4% | 49.5% | 46 / 95 | 49 | 47 / 93 | 0.324 |
| 5 | 32.5% | 71.1% | 27 / 83 | 56 | 11 / 38 | 0.287 |

- **Detection / recall:** hits divided by actual ≥20 mm cases. This measures how
  many events were caught.
- **Precision:** hits divided by all alerts. This measures how many alerts were
  correct. The remaining alerts are false alarms.
- **False-alarm ratio:** false alerts divided by all alerts. This differs from
  false-positive rate, which divides by actual below-20 mm cases.
- **CSI:** hits divided by hits + misses + false alarms. Higher is better.

For lead 1, 39 of 95 events were detected, 56 were missed and 6 of 45 alerts were
false. Its 86.7% precision does **not** mean that it detected 86.7% of events.
There is no single rainfall “accuracy percentage” that captures both these
event decisions and the errors in predicted millimeters.

The [full results report](docs/reports/nwp-rainfall-results.md) includes comparisons
with uncorrected GFS on the same cases. Earlier rainfall-history scores use a
different evaluation year and cannot establish a controlled improvement over
these results.

### Rainfall-amount errors

All errors below are in millimeters. MAE is the average absolute error; RMSE
penalizes larger errors more strongly. Lower is better for both. Bias is signed
prediction minus observation, so a negative value indicates underprediction.

These are the selected model's scores, matching the dashboard's amount table.

| Lead | MAE | RMSE | Bias | Amount ≥20 mm detection | Grid-day cases |
|---|---:|---:|---:|---:|---:|
| 1 | 7.19 | 22.13 | -5.36 | 29.5% | 748 |
| 2 | 6.03 | 17.80 | -3.27 | 28.4% | 748 |
| 3 | 6.23 | 15.93 | -4.67 | 26.4% | 748 |
| 4 | 8.50 | 25.86 | -5.96 | 22.1% | 748 |
| 5 | 6.76 | 18.06 | -2.97 | 22.9% | 748 |

Underprediction remains substantial at every lead. The amount-based detection
column thresholds the numeric rainfall estimate at 20 mm; it is separate from
the probability-based alerts above. An event alert can be raised even when the
amount estimate is below 20 mm.

Approximate 95% intervals are included in the dashboard's expanded method details
and the [full results report](docs/reports/nwp-rainfall-results.md). They use 500
circular block-bootstrap replicates of two adjacent initialization dates,
preserving all cells within each date. Intervals are wide because only 34
initialization dates and one partial season are available. An interval crossing
50% does not mean the target was achieved. These results do not establish reliable
village forecasting or consistent performance across other years and regions.

## Managing forecast data

### Import official block tables

1. Manually download new official Nashik block tables. Do not automate the protected portal.
2. Preserve each export in `Block-level data`. Only these filename formats are supported:
   `Nashik_Block_YYYY-MM-DD.csv` and `Nashik_Block_YYYY-MM-DD - Sheet1.csv`.
3. Import and inspect the output report:
   ```powershell
   .venv\Scripts\python scripts/import_block_forecasts.py --input-dir 'Block-level data' --district Nashik
   ```
4. Read `data/imported/block_forecasts/nashik/<dataset-version>/import_report.json`.
   Rejected files or conflicting duplicates prevent activation. Partial coverage is
   allowed and explicitly reported. Issues are never blended.
5. Build without activation, then activate after checking warnings and coverage:
   ```powershell
   .venv\Scripts\python scripts/build_demo_forecasts.py --district Nashik --dataset-version <dataset-version>
   .venv\Scripts\python scripts/build_demo_forecasts.py --district Nashik --dataset-version <dataset-version> --activate
   ```
   If warnings were reviewed, add `--accept-warnings` to the activation command.
   This acknowledges warnings, not rejected files or conflicts.
6. Ship `data/imported`, `data/derived` and `data/models/terrain_proxy` with the code.
   Activation atomically changes one pointer, retaining previous runs.
7. Verify issue, validity period, block coverage and source warnings in the UI.

Current dataset: `imd-2e3bc1b0c762bd8e15a6`.
Current run: `block-8ed619637d1bb7d52fa99ed6`.
Model: `terrain-631e5f007f8d4bca7a85`.
To reproduce the included activation:

```powershell
.venv\Scripts\python scripts/build_demo_forecasts.py --district Nashik --dataset-version imd-2e3bc1b0c762bd8e15a6 --activate --accept-warnings
```

The build CLI defaults to `--method terrain`; use `--method baseline` explicitly
to reproduce the unchanged-parent method. New inputs reuse the packaged model;
normal import/build/GET requests never train it.

To reproduce the offline model comparison and DEM extraction (requires development
dependencies and the existing Copernicus DEM directory):

```powershell
.venv\Scripts\python scripts/train_terrain_proxy.py --dem-dir 'data/dem'
```

The terrain-training command evaluates proxy climatology, not village forecast
accuracy. Its assumptions are described under [How the application works](#how-the-application-works)
and in the [model card](docs/MODEL_CARD.md).

### Retrieve the district forecast

District mode acquires the source only when requested. It never substitutes into
block mode. Cache download time, issue date, validity, retrieval errors and cache
use are separate fields. Each request selects its date from the complete series.
Expired runs remain explicitly archived.

Set `DISTRICT_CACHE_DIR` to a writable runtime directory; packaged data can remain
read-only. The default is `data/cache/district_forecasts`.
Operator refresh command:

```powershell
.venv\Scripts\python scripts/refresh_district_forecast.py --district Nashik
```

The district adapter extracts rainfall, maximum/minimum temperature, maximum/minimum
humidity, wind speed and qualitative cloud descriptions. Numeric cloud oktas and
wind direction remain unavailable when the source does not supply them.

## Reproduce the rainfall research

Running the packaged application does not execute these steps. Use them to
reconstruct or audit the experiment, with Python 3.13 and the recorded dependency
versions. The downloads require internet access. Raw national grids, regional
forecast subsets and extracted training arrays are ignored by Git; manifests,
model artifacts and evaluation predictions are included in the project.

### Restore observations and acquire forecast inputs

From the repository root:

```powershell
.venv\Scripts\python -m pip install -r requirements-nwp.txt
# Restore annual arrays only if the checksum-matching local copies are absent.
.venv\Scripts\python scripts/acquire_maharashtra_history.py --start 2010 --end 2024
.venv\Scripts\python scripts/acquire_maharashtra_history.py --start 2025 --end 2025
.venv\Scripts\python scripts/acquire_nwp_history.py --kind gfs --workers 4
.venv\Scripts\python scripts/acquire_nwp_history.py --kind observations --workers 2
```

The expected annual dataset IDs are `imd-mh-34a5f8f7716669bf2297` and
`imd-mh-ab17f6679502dc028f18`, as specified in
[`config/nwp_experiment.json`](config/nwp_experiment.json). Dataset identities
include source/boundary information. A different ID must be investigated; changing
the configuration is a new experiment, not an exact replay of the packaged one.

The archive download is resumable and verifies cached checksums. Do not overwrite
the original cached provisional observations to hide later source revisions.
If the provider changes those grids, preserve both provenance and the distinction
between the original evaluation and any new run.

### Build pairs, fit, freeze and evaluate

```powershell
.venv\Scripts\python scripts/build_nwp_pairs.py
.venv\Scripts\python scripts/train_nwp_calibration.py
.venv\Scripts\python scripts/build_nwp_pairs.py --fresh
.venv\Scripts\python scripts/evaluate_nwp_calibration.py --experiment-id nwp-model-badc5a9e1eb18c3ff1b4
.venv\Scripts\python scripts/report_nwp_results.py
```

Training prints its experiment ID. The evaluation command above targets the
packaged frozen experiment; use a newly printed ID only when deliberately
evaluating a new experiment. Configuration, code, data and library identities
contribute to the frozen training record. Evaluation checks the configuration,
training-code hashes, input checksums and model checksums before scoring.
The report-generation script's written interpretation is deliberately restricted
to the packaged September 2026 audit.

To evaluate the packaged weights without fitting them again, acquire/restore the
matching inputs, build the fresh pairs and run the evaluation command, omitting
the training command. The original cached data are needed for exact replay if
provisional source observations have subsequently changed.

The preceding rainfall-history experiment can also be replayed using its frozen
models and the finalized 2025 observation array:

```powershell
.venv\Scripts\python scripts/train_rainfall_events.py --stage evaluate --experiment-id rain-events-d46883949173f5fdf284 --fresh-dataset imd-mh-ab17f6679502dc028f18
```

See [GFS method and provenance](docs/NWP_RAINFALL_MODEL.md) and
[earlier rainfall-history reproduction](docs/RAINFALL_EVENT_MODEL.md) for further
details. Neither research pipeline activates a village-serving model.

Research dataset: `gfs-imd-fc0717628c7614b9b55e`.
Experiment: `nwp-model-badc5a9e1eb18c3ff1b4`.
Evaluation: `evaluation-2b37883a3571e9ee`.

The [machine-readable report](data/research/benchmarks/nwp-model-badc5a9e1eb18c3ff1b4/evaluation-2b37883a3571e9ee/report.json)
contains candidate scores and frozen selection details. Its directory includes
`artifact_hashes.json` and five `lead-*-predictions.npz` files. Prediction archives
use numeric/Unicode arrays and open with `numpy.load(..., allow_pickle=False)`.

## Project structure and API

```text
frontend/                  React dashboard, Leaflet map and evidence views
src/api/                   FastAPI routes and frontend serving
src/services/              Forecasts, comparisons, explanations and bulletins
src/ingestion/             Block parsing, district retrieval and research acquisition
src/geography/             Administrative IDs, aliases and village associations
src/modeling/              Terrain model and rainfall research modules
config/                    Geography mappings and experiment configurations
Block-level data/          Original manually supplied block CSVs
data/imported/             Validated and normalized source datasets
data/derived/              Versioned forecasts and activation pointers
data/models/terrain_proxy/ Serving model metadata and adjustments
data/boundaries/           Geographic inputs
data/research/             Manifests, frozen experiments and evaluation artifacts
scripts/                   Import, build, refresh, training and reporting commands
tests/                     Automated behavioral and evidence checks
docs/                      Methods, model card, reports and submission guidance
```

Some legacy research modules remain available but are not part of the serving
workflow. [Baseline documentation](docs/BASELINE.md) records implementation history.

### Main API routes

| Method and route | Purpose |
|---|---|
| `GET /api/health` | Application status and block-data readiness |
| `GET /api/districts`, `GET /api/blocks` | Supported geography |
| `GET /api/forecast/modes`, `GET /api/forecast/runs` | Source modes and available runs |
| `GET /api/forecast` | Selected forecast records and metadata |
| `GET /api/panchayats/geojson` | Forecast values joined to geometry |
| `GET /api/panchayat/{panchayat_id}/explainability` | Source/local values and adjustment details |
| `GET /api/comparison` | Diagnostic block/district comparison API (not shown as a dashboard tab) |
| `GET /api/model-evidence` | Saved rainfall research reports |
| `GET /api/validation-metrics` | Serving-model evidence and validation limitations |
| `GET /api/advisories` | Weather-rule advisory previews |
| `GET /api/bulletin/{panchayat_id}` | Printable HTML bulletin |
| `POST /api/disseminate/preview` | Render message text without sending it |

Forecast selection accepts `mode`, `district`, `run_id`, `valid_date` and `block`.
For example:

```text
/api/forecast?mode=block&district=Nashik&valid_date=2026-09-11&block=Niphad
/api/comparison?valid_date=2026-09-14&block=Igatpuri
```

The diagnostic comparison endpoint matches exact village IDs and overlapping
forecast dates. It also accepts `block_run_id` and `district_run_id` to pin both
sources. This testing tool is available through the API and report script only.
Differences between its two forecast sources are not accuracy scores. Use `/docs`
for schemas, accepted parameters and response formats.

**Model & training** renders the `nwp_benchmark` portion of `/api/model-evidence`,
selected through `data/research/benchmarks/nwp_evidence.json`. The API also retains
the original report and an optional `revised_benchmark`, selected through
`event_evidence.json`, for research access; the dashboard does not render those
earlier experiments. Unsafe IDs and mismatched report identities are rejected.
These pointers select saved evidence; they do not activate a forecasting model.

To generate the retained diagnostic source-comparison report from the existing
district cache without external requests:

```powershell
.venv\Scripts\python scripts/report_forecast_comparison.py
```

The packaged [comparison report](docs/reports/comparison-1ba7a9427fa1b01026b3.md)
has a companion JSON snapshot containing 7,664 paired village-date rows.

## Testing

```powershell
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest tests -q
.venv\Scripts\python -m pip check
```

`pytest.ini` scopes default collection to `tests`, keeping network-probing utility
scripts out of the automated test suite. To rerun the focused rainfall/evidence
checks:

```powershell
.venv\Scripts\python -m pytest tests/test_nwp_calibration.py tests/test_nwp_evidence.py tests/test_rainfall_events.py tests/test_event_evidence_api.py -q
```

Tests cover forecast-window integration, missing native steps, observation-date
receipts, temporal/geographic exclusions, event counts, frozen thresholds and
evidence identity. The packaged-evidence regression recomputes all reported
amount/event metrics and selected alert decisions from saved predictions and
verifies artifact/model hashes. Existing tests cover source parsing, weather
propagation, rainfall conservation, date/filter behavior, block/district isolation,
comparisons and printable bulletins.

Tests distinguish software correctness from meteorological accuracy. Research
modules and old district model artifacts are retained but are not loaded by production.
Training rejects zero-variance targets; inference does not train or overwrite CSVs.

The most recent full verification completed **82 passing tests** and a successful
production frontend build. The served JavaScript bundle was also checked for the
removed comparison tab. These are recorded checks of that code state; rerun the
commands above after changing application or model code. They establish software
behavior and reproducibility, not meteorological accuracy.

## Deployment

The application needs a Python-capable host because the backend serves forecasts,
source retrieval and bulletin endpoints. The supplied Dockerfile builds the
frontend, packages serving data and research reports, and uses a writable
`/tmp/nashik-district-cache` directory for district caching.

```sh
docker build -t nashik-hybrid .
docker run --rm -p 8000:8000 --read-only --tmpfs /tmp nashik-hybrid
```

Alternatively build the frontend, install `requirements.txt`, package the source,
configuration, imported/derived outputs, `data/models/terrain_proxy`,
`data/research/benchmarks`, Nashik boundary GeoJSON and covariates,
then start `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`.
Configure the platform's port/reverse proxy and writable district-cache directory.

Health: `/api/health` separately reports application running, block demo readiness,
and district cache status without contacting IMD. Check `block_demo_ready == true`
in deployment readiness checks; process health alone is not data readiness.

See [implementation handoff](docs/HANDOFF.md) for coverage, architecture, checks,
administrative limitations and source semantics.

For a submission archive, follow the [submission guide](docs/SUBMISSION.md).
`scripts/package_submission.py` requires reviewed changes to be committed and the
frontend built before it creates a checksum-verified ZIP. Large raw research
downloads are not runtime dependencies.

## Limitations

- Village polygons are not verified gram-panchayat boundaries. Parent associations
  use source labels rather than independently verified development-block containment.
- Terrain adjustments assume a parent rainfall footprint and reference elevation.
  Independent village forecast accuracy is unverified.
- Humidity and wind are inherited; local variation is not modeled.
- GFS research uses coarse grids, sampled runs, provisional 2026 observations and
  assumed publication timing. It is not village-gauge validation or a complete
  operational evaluation.
- Heavy-rain detection remains below the joint target. High precision alone does
  not establish good detection, accurate rainfall amounts or reliable warnings.
- Advisory text is weather-triggered guidance, not an official IMD advisory, an
  officer-approved recommendation or a message-delivery service.

## Documentation and sources

| Document | What to read it for |
|---|---|
| [Model card](docs/MODEL_CARD.md) | Serving assumptions, model evidence and limitations |
| [GFS research method](docs/NWP_RAINFALL_MODEL.md) | Features, splits, timing, acquisition and reproducibility |
| [GFS results](docs/reports/nwp-rainfall-results.md) | Counts, baseline comparisons, thresholds and uncertainty |
| [Rainfall-history method](docs/RAINFALL_EVENT_MODEL.md) and [results](docs/reports/rainfall-events-results.md) | Earlier modeling approach and its evaluation |
| [Implementation handoff](docs/HANDOFF.md) | Detailed architecture, coverage and data semantics |
| [Submission guide](docs/SUBMISSION.md) | Demonstration checklist and distribution instructions |
| [Baseline evidence](docs/BASELINE.md) | Preserved implementation history |

Forecast and research sources include:

- [IMD district bulletin](https://imdagrimet.gov.in/Services/DistrictBulletin.php?state=Maharashtra&district=Nashik&language=English) and manually supplied official block tables.
- [IMD annual rainfall analyses](https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html) and [provisional daily rainfall](https://imdpune.gov.in/cmpg/Realtimedata/Rainfall/Rain_Download.html).
- [NOAA GFS processed by dynamical.org](https://dynamical.org/catalog/noaa-gfs-forecast/), attributed to NOAA NWS NCEP GFS processed by dynamical.org under CC BY 4.0.
- [NASA POWER meteorology](https://power.larc.nasa.gov/docs/methodology/meteorology/) for the seasonal climate-pattern proxy.
- [Copernicus DEM](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM) for elevation inputs.

Source use does not imply provider endorsement. Acquisition receipts, source hashes
and method assumptions are retained so results can be inspected and reproduced
within their stated limits.
