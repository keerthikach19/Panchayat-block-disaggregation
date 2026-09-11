# Nashik hybrid implementation handoff

## Delivered behavior

Official manually imported block CSVs are the offline default; live district IMD
forecasts remain a separate working mode. The original map's dark styling,
floating before/after controls, blue/indigo rainfall palette, hover highlighting,
zoom and adjacent detail panel are restored. The Forecast issue selector is removed.
Issue and validity dates remain in provenance. Optional street labels fetch online
only when enabled; initial rendering needs no external assets, upload or CAPTCHA.

The default experimental model now produces spatially varying rainfall and
maximum/minimum temperature estimates. Original source values are preserved in a
separate field and displayed beside local values. Humidity, cloud and wind remain
explicitly inherited; missing district variables remain unavailable.

Example: Igatpuri's 13 September source rainfall is 38.2 mm. The model estimates
36.30–40.94 mm across its 117 linked villages. Gondedumala displays 38.23 mm and a
maximum temperature of 26.0°C against source values of 38.2 mm and 25.7°C. These
differences demonstrate the implemented adjustment, not verified forecast accuracy.

## Preservation and architecture

The new branch `codex/nashik-hybrid` starts from verified district commit
`7bcf270e01cf2f8467b6f22d580d59114e40e74c` in `.worktrees/nashik-hybrid`.
Checkpoint `74edb49` preserves the district baseline and adds strict CSV contracts.
The original main at `e96561e`, partial migration, 15 raw CSVs and legacy model
artifacts are retained. No reset, deletion, force-push or remote publication occurred.
The migration was inspected; only its parent-association concept was reused. No
whole migration merge or blanket cherry-pick was used.

- `src/ingestion/block_csv.py` and `forecast_schema.py`: strict filename/title
  identity, five daily columns, explicit labels, numeric/range/min-max checks,
  BOM/CRLF handling, summary warnings, duplicate provenance and conflict rejection.
  Invalid/conflicting datasets cannot activate; original input bytes are unchanged.
- `config/administrative_units.json`, `config/block_aliases.json`, `src/geography/registry.py`: shared
  internal IDs, explicit spelling aliases and strict geographic joins. No fuzzy
  parent guessing or fabricated official GP identifiers.
- `src/services/forecast_service.py`: separate providers, immutable complete runs,
  exact run/date filters, source/local records, compatibility/checksum checks,
  explanations and weather-triggered advisory previews. Filters never overwrite data.
  District runs retain both source snapshot and model version, including across
  active-model changes. In-memory district runs expire on server restart.
- `src/ingestion/imd_live.py`: complete cached forecast series, date selection on
  every request, separate issue/download/validity fields, trusted HTML-to-PDF links,
  bounded validated PDF retrieval and explicit cache/error/archive behavior.
- `src/modeling/terrain_model.py`, `scripts/train_terrain_proxy.py`: offline
  reproducible proxy-model comparison and real DEM extraction; serving reads
  versioned JSON coefficients, adjustment factors and validation reports.
- `src/api/main.py`: FastAPI serving, health/readiness, source/runs/forecast/geometry,
  explanation/validation/advisory and preview endpoints. No startup training,
  protected-portal automation, public upload or logging-only approval gate.
- `frontend/src/App.jsx`, map/details/validation components, `hybrid.css`: restored
  map presentation and explicit provenance. Requests are keyed by mode, district,
  run, block and date, aborting stale responses. Before/after views share quantile
  breaks from both source/local distributions; gray means unavailable.
- CLI import/build/refresh scripts, requirements, Dockerfile and README: owner
  operations and deployment packaging. Legacy research Layers A–D remain available
  but are excluded from serving; guards prevent automatic training, output CSV
  overwrites, unknown-district fallback and zero-variance target training.

## Import and geographic coverage

Issued 10 September 2026; valid 11–15 September 2026.
15 accepted CSVs, zero rejected/conflicting/duplicate files, 75 normalized block-day
records and 9,580 village-date outputs in the final dataset.

| Block | Linked village polygons |
|---|---:|
| Baglan | 170 |
| Chandwad | 111 |
| Deola | 50 |
| Dindori | 157 |
| Igatpuri | 117 |
| Kalwan | 151 |
| Malegaon | 142 |
| Nandgaon | 100 |
| Nashik | 73 |
| Niphad | 133 |
| Peth | 145 |
| Sinnar | 129 |
| Surgana | 189 |
| Trimbak | 125 |
| Yeola | 124 |
| **Total** | **1,916** |

Of 1,953 village features, 37 with unresolved Central parent labels are excluded,
including four sharing placeholder ID `MH_487_999999`. Displayed features have
unique IDs, valid geometry and matching canonical parent labels in covariates and
boundaries. No trustworthy development-block boundary layer was established for
containment validation. Per-feature reasons are in each run's geography report.

All source GP codes are blank: these are village polygons, not verified
panchayat boundaries. The official [Grampanchayat page](https://nashik.gov.in/en/grampanchayat/)
lists block/revenue circle/villages in Sajja, without the required GP-code crosswalk.
Aliases were checked against district [taluka maps](https://nashik.gov.in/en/about-district/talukawise-map/)
and the [land-record tehsil list](https://dilrmp.gov.in/dilrmpold/PhyscialComponent/mapDigitization/tehsil-level/516).
Central remains unresolved. Pune remains disabled; no Pune inputs were added.

Three warnings were acknowledged for the demo: Baglan's two temperature unit
symbols are `?`, interpreted as Celsius from the table schema pending owner
verification; Niphad's RH maximum summary is 93 while the daily mean is 92.4.
Daily values and raw bytes are retained exactly. An earlier rejected Baglan import
is kept inactive for audit; the final parser explicitly recognizes its observed label.

## Model selection and scientific limits

The former baseline intentionally inherited every parent value. The migration's
one-station-per-taluka deviation target would collapse to zero, so its weights and
reported historic scores were not presented as block-level validation.

The legacy training CSV has 6,120 rows under 40 station labels, all misleadingly
labeled `IMD_AWS_NASA_POWER_Blended`. The actual acquisition path in
`scripts/07_assemble_stations.py` fetches NASA POWER without an AWS join. Identical
daily weather profiles reduce this to 28 distinct statewide profiles, only five in
Nashik. These are gridded proxies, not independently verified observations; NASA's
[meteorology methodology](https://power.larc.nasa.gov/docs/methodology/meteorology/)
describes the underlying reanalysis. No synthetic observations were created or used.

An offline comparison withheld entire duplicate-profile groups to prevent their
appearance on both sides of a split. June–July seasonal means supplied training
targets and August supplied validation. The lowest validation RMSE selected ridge
regression, with standardized latitude, longitude and catalog elevation, log1p
rainfall targets and alpha 10. The frozen model choice was then evaluated using
June–August training and September–October targets, still withholding each spatial
group. The later period also serves as a promotion gate, not independent final
certification; there is no untouched forecast-accuracy test dataset.

| Candidate | August proxy RMSE, mm/day | August proxy MAE, mm/day |
|---|---:|---:|
| Regional-mean baseline | 10.54 | 10.28 |
| Ridge | 9.14 | 8.31 |
| Random forest | 12.06 | 10.22 |
| Distance-weighted neighbours | 9.43 | 8.19 |

Exact scores and protocol are stored in the versioned `validation_report.json`.
Ridge's later-period proxy RMSE is 4.73 mm/day versus 5.93 for the regional mean.
This compares seasonal gridded climatology; it does **not** measure daily IMD
forecast accuracy, within-block skill or improvement over actual parent forecasts.

Real existing Copernicus DEM tiles were read without modification to extract
1,916 village elevations. Tile hashes, pixel counts and geodesic areas are recorded.
Copernicus provides a [digital surface model](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM),
which is not a perfect bare-earth terrain model. Training elevations come from the
legacy location catalog; prediction elevations use the DEM, another transfer limitation.

Rainfall factors normalize predicted seasonal climatology to each parent's
area-weighted linked-village mean; block factors span approximately 0.899–1.098.
The implementation conserves that footprint-weighted input to rounding tolerance.
This experimentally assumes the provider forecast is an area mean over those
footprints; IMD has not confirmed this spatial interpretation or accumulation interval.
Import-stage notes saying no redistribution describe the original source normalization;
the terrain model explicitly adds this conditional assumption at the modeling stage.

Temperature uses a fixed −6.5°C/km lapse rate relative to assumed parent footprint
mean elevation, with adjustments of approximately −2.89 to +2.58°C. Source reference
height is unknown and inversions can invalidate the assumption. Temperature skill,
humidity/wind/cloud downscaling, uncertainty intervals and lead-time skill are
unvalidated. The model is labeled experimental everywhere; no highest-performance
or accuracy guarantee is claimed. Independent local observations and archived
forecast/observation pairs are needed to establish those claims.

## Verification

- Before edits: six existing parser/Layer C tests, dynamic advisory assertions and
  original district API smoke passed; the old model loaded 40 cached LOSO
  predictions. Training and forecast-file writes were blocked during baseline checks.
- Final suite: 53 tests pass. Coverage includes strict parsing, input preservation,
  aliases, invalid/duplicate/conflicting inputs, parent/date isolation, all 15 blocks
  across all five dates, missing data, immutable/checksummed runs, offline default,
  independent district mode, model compatibility and model-version activation.
- Terrain checks verify variation, zero-input rainfall remains zero, ordered
  temperatures, inherited secondary variables and footprint-weighted rainfall
  conservation to 0.0001 mm. These test implementation correctness, not accuracy.
- Live-feed tests cover cached date changes, expiry/current status, malformed
  content, HTML-to-PDF links, corrupt cache and network failure. Archive behavior
  is tested with an injected clock; a future-date browser session was not simulated.
- Real 11 September IST retrieval returned the official district PDF issued
  8 September, valid 9–13 September, with 10/5/2/8/15 mm rainfall. Selecting
  11 September returned 2 mm. This verifies retrieval and date selection only.
  The final browser check fetched a newer bulletin issued 11 September, valid
  12–16 September. Selecting 13 September returned 35 mm district source rainfall
  and was correctly labeled upcoming on 11 September.
- Production React build and local built-asset/API smoke pass. Browser checks
  verified Igatpuri/13 September, polygon source/local detail, restored map layout
  and absence of the Forecast issue selector. District mode loaded its independent
  issue/date range; returning to block mode restored the imported source range.
- Two test dependency deprecation warnings remain. Existing Vite 5 development
  dependencies have two audit findings (one moderate, one high); no forced upgrade
  was applied. Production serves compiled assets through FastAPI.
- Docker is unavailable on this machine. Container configuration is supplied;
  an actual Docker build/run and remote deployment have not been verified.

## Run, refresh, deployment and recovery

See [README](../README.md) for exact environment setup, local run, deployment and
owner refresh commands. Package `data/imported`, `data/derived` and
`data/models/terrain_proxy` plus the named geography/config assets. District cache
must be writable; default block serving needs no writes or training.

- Dataset: `imd-2e3bc1b0c762bd8e15a6`.
- Active model: `terrain-631e5f007f8d4bca7a85`.
- Active run: `block-8ed619637d1bb7d52fa99ed6`.
- Retained unchanged-parent run: `block-323eddcfbdfc3170f83ab941`.

Refresh: manually download CSVs, preserve originals, import/validate, review
conflicts/missing blocks/warnings, build, activate only a valid run, deploy the
complete bundle and check issue/validity in the UI. The build CLI defaults to
`--method terrain`; `--method baseline` explicitly restores parent inheritance.
Prior runs remain accessible through `/api/forecast/runs?mode=block` and
`/api/forecast?mode=block&run_id=<run-id>`, although the issue selector was removed
as requested. To change the default, rerun the documented build/activation command
for a retained dataset and method. Activation records the previous default.
Never edit immutable output or normalized-source JSON in place.

## Same-day comparison extension

The comparison tab and `/api/comparison` pair exact village IDs on intersecting
forecast dates, pin both runs, and separate parent-input and reference-factor
contributions algebraically. It includes equal-village/area-weighted statistics,
date/block/village tables, a paired scatter plot and advisory-trigger sensitivity.
Non-overlapping dates, duplicate IDs, incompatible models and unavailable variables
fail explicitly. Ordinary map startup does not fetch comparison/district data.

The detailed report and complete 7,664-row frozen comparison are in
`reports/comparison-1ba7a9427fa1b01026b3.md` and its companion JSON. See README for
the cache-only report generator. The report compares block issue 10 September
against district issue 11 September for 12–15 September; only rainfall is available
on both current paths. Findings measure disagreement, not observational accuracy.

Eight targeted comparison and API tests passed, including the five new comparison
tests; the prior 53-test baseline remains recorded above. The production frontend
build and running API/report snapshot match passed. No forecast/model/input assets
were modified for this comparison.
