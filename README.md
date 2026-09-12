# Nashik weather downscaling — final academic release

See [submission guide](docs/SUBMISSION.md) for the demonstration checklist, training
results and final model decision. The application includes six weather map layers,
a same-day comparison, training evidence and printable GKMS-style draft bulletins.


Official, manually imported IMD **block** tables are the default source. A separate
**live district** mode fetches the public IMD district bulletin. Block mode works
without external requests, uploads, authentication or CAPTCHA.

The default method is an **experimental terrain model**: ridge regression fitted
to deduplicated NASA POWER seasonal climatology provides parent-normalized rainfall
factors; real Copernicus DEM elevations support a documented temperature lapse-rate
adjustment. The original unchanged-parent run remains available through the API.
These are traceable experimental estimates, not validated village predictions.
Available geography consists of village polygons, not verified gram-panchayat
boundaries. These limitations are visible in the application.

## Preserved baseline

Work was isolated on `codex/nashik-hybrid`, starting at district commit
`7bcf270e01cf2f8467b6f22d580d59114e40e74c`.
The original `main` migration at `e96561e` and original CSV inputs remain intact.
The migration was reviewed, not merged. See [baseline evidence](docs/BASELINE.md).

## Run locally

From the project checkout on `main` (or the isolated final-release branch):

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
The validated demonstration data is already packaged; no import or model training
is required at startup. Linux equivalents use `.venv/bin/python`.

On this Windows machine the npm wrapper can resolve its installation incorrectly.
The verified alternative, from `frontend`, is:

```powershell
node 'C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js' install
node 'C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js' run build
```

## Refresh block data

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
.venv\Scripts\python scripts/train_terrain_proxy.py --dem-dir 'C:\Users\keert\OneDrive\Desktop\Panchayat-downscaling\data\dem'
```

The 6,120 legacy records are NASA POWER gridded data, not independently verified
AWS observations. There are 28 distinct profiles statewide and only five in Nashik.
The model report separates its proxy-climatology benchmark from forecast accuracy.
Rainfall redistribution assumes the parent input is an area mean over linked
village footprints; the provider has not verified this interpretation. Temperature
adjustment assumes the parent reference is the area-weighted footprint elevation
and uses −6.5°C/km; inversions and unknown source reference heights can cause errors.
Humidity, wind and cloud values are inherited unchanged from the source.

## District mode

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

## Verification

The **Same-day comparison** view pairs block-derived and district-derived rainfall
by exact village ID and overlapping validity dates. Date/block changes pin both
runs; **Compare latest sources** starts a new pairing. It reports signed and absolute
disagreement, area-weighted means, per-block/village results, source/reference
decomposition and advisory-threshold sensitivity. This is not an accuracy test.
An all-weather summary also compares temperature, humidity and wind speed when both
sources supply them. The comparison is loaded only
when its view is opened, so the default map retains offline block behavior.

API: `/api/comparison?valid_date=2026-09-14&block=Igatpuri`, with optional
`block_run_id` and `district_run_id` to pin a pair. Mismatched model versions and
non-overlapping dates fail explicitly. A server restart requires fetching district
runs again; the packaged written report remains reproducible from its frozen source.

Generate a detailed Markdown report and complete JSON snapshot from the current
local district cache, without external requests:

```powershell
.venv\Scripts\python scripts/report_forecast_comparison.py
```

The report is in `docs/reports/comparison-1ba7a9427fa1b01026b3.md`, with a companion
JSON containing the full district bulletin and 7,664 paired village-date rows.

```powershell
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest tests -q
```

Tests distinguish software correctness from meteorological accuracy. Research
modules and old district model artifacts are retained but are not loaded by production.
Training rejects zero-variance targets; inference does not train or overwrite CSVs.

## Deployment

No deployment has been published. The existing application is Python/FastAPI,
so deploy it on a Python or container-capable platform; it is not a static-only
site or a Cloudflare Worker.

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
