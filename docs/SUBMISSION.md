# Submission guide — Nashik weather downscaling

## Run

Windows, Python 3.13 and Node 22, from the project root:

```powershell
.\Start-Project.ps1 -Setup
```

Subsequent runs: `.\Start-Project.ps1`. Open http://127.0.0.1:8000.
Use `-Port 8001` if another server occupies 8000. Ctrl+C stops the server.
The first setup installs locked dependencies and builds the frontend. Forecast
artifacts are already packaged; training is not required to start the app.

## Demonstration checklist

| Action | Expected result |
|---|---|
| Open Forecast map | Official block source, 15 blocks and 1,916 linked villages; source validity and archive status shown |
| Change forecast day or block | Map and village details use that exact date/filter; unavailable selections are not substituted |
| Select each weather layer | Rain, maximum/minimum temperature, maximum/minimum humidity and wind speed |
| Toggle Before / After | Available for rainfall/temperature; humidity and wind speed display source values with no local-adjustment toggle |
| Click a village | Source/local values, units, model, elevation, provenance and advisory preview |
| Switch to Live district forecast | Current public IMD bulletin, full available weather; cached retrieval and failures explicitly labelled |
| Open Same-day comparison | Exact shared village IDs/dates, rainfall differences and all-weather summary; source issues may differ |
| Open Model & training | Completed Maharashtra benchmark, test results, limitations and explicit retain-model decision |
| Open a village's bulletin link | Printable five-day GKMS-style draft, source/local weather, general guidance, missing field inputs, provenance |
| Preview dissemination | Text preview only; no SMS or WhatsApp message sent |
| Run block mode offline | Packaged forecasts work; optional street labels and uncached district retrieval require internet |
| Open `/api/health` and `/docs` | Data readiness status and interactive API documentation |

The imported block issue is 10 September 2026, valid 11–15 September. It becomes
an explicitly archived demonstration after that period. Update it only by importing
new official CSVs as described in the README. New district bulletins may no longer
overlap the old block dates; comparison then explains that no paired dates exist.

## What to submit and describe

Submit the tracked source, packaged data/models, dependency locks, this guide and
the [model card](MODEL_CARD.md). Include `frontend/dist` for a prepared local demo,
or rebuild with setup. Large raw IMD grids and DEM files are not runtime dependencies.
Their hashes, acquisition commands and model reports are retained for reproducibility.

This is a working academic prototype for traceable weather downscaling. It does
not establish village-scale forecast accuracy. The new statewide historical
benchmark was completed and rejected as a serving replacement because its low
average error hid poor heavy-rain performance. No arbitrary agreement cap is used.
The bulletin is an academic GKMS-style draft, not an official advisory.

The original partial migration and the previously working hybrid release remain
preserved on separate Git branches. No source CSV was rewritten for model training.

## Automated checks

```powershell
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest tests -q
```

Tests cover import conflicts, immutable source/model IDs, dates and missing data,
block/district independence, rainfall conservation, source comparisons, parser
column alignment, full-weather propagation, bulletin generation and training leakage
contracts. They establish software behavior, not observational forecast accuracy.

## Recreate the submission ZIP

After committing reviewed changes and building the frontend:

```powershell
.venv\Scripts\python scripts/package_submission.py
```

The ZIP includes tracked project files, the built frontend, an available district
source cache and a RELEASE.json file manifest. Each ZIP entry is read back and
SHA-256 checked. A companion .sha256 file identifies the complete archive.

Cloud cover and wind direction are omitted from the dashboard and draft bulletin.
Humidity and wind speed are shown as source weather, without duplicate local
estimates. District inputs are uniform over villages for a selected date; block
inputs can differ between blocks. No local variation is invented.
