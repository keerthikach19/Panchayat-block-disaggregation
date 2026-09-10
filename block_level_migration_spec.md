# Migration Spec: District→Panchayat → Block(Taluka)→Panchayat Downscaling

**Repo:** `github.com/keerthikach19/Panchayat-block-disaggregation`
**Goal:** Change the live input layer of the downscaling pipeline from district-level (IMD Agromet district bulletin) to taluka/block-level, per PS 26074's block-level framing.
**Non-goal:** Rewriting Layer B/C/D model families, rebuilding the frontend from scratch, or adding real authentication.

---

## 0. Current Architecture (verified against code)

| Component | File | Current behavior |
|---|---|---|
| Live ingestion | `src/ingestion/imd_live.py` | Scrapes `https://imdagrimet.gov.in/Services/DistrictBulletin.php?state=Maharashtra&district=<D>&language=English`, parses PDF bulletin, caches per district. District-level ONLY. |
| Layer A decomposition | `src/modeling/layer_a_decomposition.py` | `decompose_station_observations(stations_df, obs_df)` groups stations by `district` column, computes daily district spatial mean via `groupby([dist_col, "date"]).transform("mean")`, targets = station deviation from that mean. `reconstruct_panchayat_prediction(block_value, deviation, residual)` = `max(0, block_value + deviation + residual)`. |
| Layer B model | `src/modeling/layer_b_deviation.py` | LightGBM (`import lightgbm as lgb`) predicting rainfall/temp deviation from block mean using panchayat/station covariates (elevation, distance-to-coast, historical_rain_bias). Serialized to `data/models/layer_b_models.pkl`. |
| Pipeline orchestrator | `src/modeling/downscaling_pipeline.py` | `DownscalingPipeline(footprint_name="Maharashtra", target_district="Nashik")` — state-agnostic by design. |
| Layer C/D | `src/modeling/layer_c_kriging.py`, `layer_d_ensemble.py` | Kriging of residuals; ensemble + uncertainty propagation. Unaffected by this migration. |
| Station metadata | `data/stations/maharashtra_stations_metadata.csv` | Columns: `id,name,lat,lon,elev,zone,district` — 40 stations. **No taluka column.** |
| Station observations | `data/stations/maharashtra_station_observations.csv` | Station-day rows joined to metadata; feeds Layer A decomposition. |
| Boundaries | `data/boundaries/` | `nashik_district.geojson`, `nashik_panchayats_covariates.geojson` (1,953 features), `pune_panchayats_covariates.geojson` (1,918 features), `maharashtra_state.geojson`. **No taluka polygons.** |
| Config | `config/bounding_boxes.json` | District-level bounding boxes for fetching. |
| API | `src/api/main.py` (FastAPI) | Endpoints serve downscaled forecasts + a **hardcoded fallback validation JSON** (lines ~420-470) that must be kept in sync with `data/validation_report.json`. |
| Validation | `src/validation/validate.py`, `data/validation_report.json` | Segmented LOOCV. Report on disk says: Seg1 (6,120 station-days): RMSE 4.75 vs baseline 4.75 (+0.16%), MAE worse than baseline (−27.7%), r=0.95, elev-rain corr 0.697, spread-skill 0.57. Seg2 (3,213): RMSE 6.44 vs 6.56 (+1.9%), r=0.89, MAE −12.3%. |
| Frontend | `frontend/src/components/MapDashboard.jsx` + panels | District→panchayat choropleth, explainability, officer review modal, audit view, dissemination preview. No login/role gate. |

### Known pre-existing defects (fix in Phase 0, before any migration work)
1. **README misrepresents `validation_report.json`.** README (~lines 245-287 and badge on line 9) quotes "the report" with RMSE 4.67mm/+1.78%/r=0.951/elev-corr 0.784/spread-skill 0.79. The actual file on disk says 4.75mm/+0.16%/r=0.95/0.697/0.57. A judge opening both will catch this immediately.
2. **API fallback JSON in `src/api/main.py` is also stale** relative to `data/validation_report.json`.
3. **MAE regresses vs baseline in both segments** — prepare the talking point: LightGBM optimizes RMSE; the value proposition is 20mm-threshold POD/CSI and calibrated uncertainty, not MAE.

---

## Phase 0 — Metric reconciliation (half a day, do first)

1. Re-run `python -m src.validation.validate` (check exact entrypoint in `run_demo.py` / README) to regenerate `data/validation_report.json` from scratch.
2. Replace the README's JSON block with the **verbatim contents** of the regenerated file (README must quote, not paraphrase).
3. Update the README badge (line 9) to whatever r the regenerated report actually produces.
4. Update the hardcoded fallback dict in `src/api/main.py` to match the regenerated numbers exactly (all three segments + spatial plausibility + spread-skill).
5. Commit. Acceptance: `grep` of any metric value in README and `main.py` returns a match in `validation_report.json`.

---

## Phase 1 — Acquire taluka/block data

Maharashtra has ~350-360 talukas (Census 2011: 355 sub-districts). Target: the talukas covering Nashik and Pune districts first (Nashik ~15 talukas, Pune ~14), then all-MH config if time permits.

### 1a. Taluka boundary polygons
- Sources to try, in order:
  - **Census of India sub-district shapefiles** (censusindia.gov.in → spatial data / administrative boundaries).
  - **Bhuvan** (bhuvan.nrsc.gov.in) — ISRO geoportal, has administrative boundary layers.
  - **LGD (Local Government Directory, lgdirectory.gov.in)** — the repo already has `data/lgd_codes/maharashtra_hierarchy_reference.csv`; LGD maps village→panchayat→taluka→district and may have boundary links. Extend the existing LGD download script (`scripts/02_download_lgd_codes.py`) rather than starting fresh.
  - GitHub mirrors: search `"maharashtra taluka geojson"` / `"MH subdistrict shapefile"` (several community mirrors of Census 2011 boundaries exist — verify against a known district's taluka list before trusting).
- Output: `data/boundaries/maharashtra_talukas.geojson` with properties at minimum `{taluka_name, district_name, taluka_code}`. Clip to Nashik + Pune for the demo if all-MH is slow.

### 1b. Taluka historical rainfall (for the climatological correction layer)
- **Maharashtra Dept. of Agriculture taluka-wise rainfall**: district collector/agriculture sites publish per-tahsils tables (e.g., Solapur district site has tahsil-wise annual series back to 2010); India Water Portal aggregates state agri-dept taluk-level data (`www.indiawaterportal.org`).
- Use this to compute, per taluka: `taluka_rain_ratio = taluka_annual_normal / district_annual_normal` (and a monsoon-season variant). Store as `data/corrections/taluka_climatology_ratios.json` keyed by taluka name.
- This is the honest interim fix for "IMD publishes district-level only": Layer A applies `district_value × taluka_ratio` before Layer B runs. No Layer B retrain needed (rainfall input is not a training feature).

### 1c. Live block-level forecast sources (integration paths)
Priority order for the live fetcher:
1. **IMD Mausamgram** (`mausamgram.imd.gov.in`) — IMD's hyperlocal portal: state→district→**block**→village selection; hourly forecast to 36h, 3-hourly to 5 days. No documented public API → requires network-call inspection (same technique as `scripts/inspect_ajax_feeds.py`). **Build as proof-of-concept only; do not make the demo depend on it.**
2. **Open-Meteo** (`api.open-meteo.com/v1/forecast?latitude=..&longitude=..&hourly=precipitation,temperature_2m&forecast_days=5`) — free, key-less, elevation-corrected. Query one call per **taluka centroid** from the Phase 1a polygons. This is the working live fallback.
3. **KSNDMC** (Karnataka only) — open taluk + hobli CSVs. Not for MH live data; only relevant if you add a portability slide for a second state.

### 1d. Station→taluka assignment
- Geocode all 40 stations into talukas: spatial join of station points against `maharashtra_talukas.geojson` (geopandas `sjoin`), or reverse-geocode via LGD hierarchy.
- Add `taluka` column to `data/stations/maharashtra_stations_metadata.csv`. Do this programmatically and commit the script (`scripts/09_assign_stations_taluka.py`).

---

## Phase 2 — Layer A changes (`src/modeling/layer_a_decomposition.py`)

Make the block column a parameter instead of hardcoding district:

```python
def decompose_station_observations(stations_df, obs_df, block_col="district"):
    ...
    block_means = merged.groupby([block_col, "date"])[["rainfall_mm", "temp_mean_c", ...]].transform("mean")
```

- Default stays `"district"` for backward compatibility; pipeline passes `block_col="taluka"` when station metadata has it.
- Verify: with 40 stations across ~29 talukas in Nashik+Pune, many talukas will have 0 or 1 station. **Handle this explicitly:**
  - Talukas with ≥2 stations → true taluka mean (same as today's district logic).
  - Talukas with 1 station → that station IS the taluka mean (deviation = 0 for training rows; document).
  - Talukas with 0 stations → excluded from training decomposition; covered at inference by the climatology-ratio layer (Phase 1b) which needs no stations.
- Add `apply_taluka_climatology(district_value, taluka, ratios_json)` helper: `return district_value * ratios[taluka]`. Round-trip test against known district sums.

**Live-input path** (new module `src/ingestion/block_live.py`, mirror `imd_live.py` structure — cache dir, `LiveDataUnavailable`, `_write_cache`):
- `fetch_block_forecast(taluka, district, target_date)` → Open-Meteo at taluka centroid, returns same dict shape as `imd_live.fetch_forecast` so downstream code is untouched.
- Optional PoC: `fetch_mausamgram_block(district, block)` with a big docstring warning that the endpoint is undocumented.

---

## Phase 3 — Pipeline + config (`downscaling_pipeline.py`, `config/bounding_boxes.json`)

- Keep signature `DownscalingPipeline(footprint_name, target_district)` but add optional `target_taluka=None`. When set:
  - Live input resolves taluka→district (for bulletin fetch), applies climatology ratio, then proceeds.
  - Layer A decomposition uses `block_col="taluka"`.
- `config/bounding_boxes.json`: add per-taluka entries `{taluka: {bbox, centroid, district}}` for all talukas in the demo districts; keep district entries for fallback.
- **Layer B model decision:** The saved `layer_b_models.pkl` was trained on deviations-from-**district**-mean. Applying it to deviations-from-**taluka**-mean is semantically consistent (both are "local deviation from enclosing block mean") but not identical. Two acceptable options:
  - **(A — preferred if time allows)** Retrain Layer B with `block_col="taluka"` decomposition, re-run `validate.py`, regenerate report. This makes every number describe the shipped system.
  - **(B — acceptable fallback)** Keep the existing model; run validation in BOTH groupings and report both, explicitly stating which model serves live inference. Never mix: the README must state which model the numbers belong to.
- Layer C (kriging) and Layer D (ensemble) require no changes — they operate on residuals/fields, independent of block definition.

---

## Phase 4 — Validation (`src/validation/validate.py`)

- Parameterize validate.py's decomposition call with `block_col` (same default-backward-compat rule).
- Re-run and regenerate `data/validation_report.json`. Segment definitions stay (Seg1 = statewide footprint generalization, Seg2 = multi-station disaggregation benchmark), but Seg2's "block mean is a true spatial average" criterion must now group by taluka — expect the set of qualifying talukas to shrink (fewer multi-station talukas than districts). Document the counts in the report metadata.
- After regeneration, repeat Phase 0 steps 2-4 (README verbatim quote, badge, API fallback sync). **This is mandatory — the current README/report mismatch is the project's biggest stage risk.**

---

## Phase 5 — API + frontend

- `src/api/main.py`: add `GET /forecast/{district}/{taluka}` alongside the existing district endpoint; reuse the same response schema; fallback chain: Mausamgram PoC → Open-Meteo → climatology-corrected district bulletin → stale cache (existing pattern).
- `frontend/src/components/MapDashboard.jsx`:
  - Add a taluka polygon layer (GeoJSON, between district and panchayat in z-order). Color it by the raw input value; panchayat layer keeps showing downscaled output. This gives the judge the visual "block input → panchayat output" story in one glance.
  - Taluka selector in the district dropdown flow (district → taluka → panchayat).
- **Optional, only if Phase 0-5 are done:** role-selector screen (Officer / Citizen) as frontend state gating officer-only components (`OfficerReviewModal`, `FeedbackAuditView`). Label it "role-based access demonstration" in the pitch. Do NOT build real auth.
- `ValidationView.jsx`: pulls from the API — verify it renders the regenerated numbers without hardcoding.

---

## Phase 6 — Docs (README + PRP.md)

- Update the architecture diagram and the "input layer" description: district bulletin → **block-level input via Open-Meteo centroids (demo) / Mausamgram (integration path) / IMD DAMU block-level MRWF (operational target)**.
- State the honest limitation explicitly: "IMD's public agromet bulletin is district-level today; the architecture accepts block-level input, demonstrated via per-taluka centroid forecasts, with taluka climatological correction as the interim layer."
- Add a "Data sources" section listing every source with URL and license/access note.
- Update all metrics by quoting `validation_report.json` verbatim (again: quote, don't paraphrase).

---

## Acceptance criteria (checklist for the agent)

- [ ] `maharashtra_talukas.geojson` exists with taluka+district names, validated against a known taluka list for Nashik/Pune.
- [ ] `maharashtra_stations_metadata.csv` has a populated `taluka` column with a reproducible assignment script.
- [ ] `layer_a_decomposition.py` accepts `block_col`; defaults unchanged (all existing tests/`run_demo.py` pass).
- [ ] Taluka climatology ratios JSON built from a cited source, applied in the live path, unit-tested.
- [ ] `block_live.py` fetches Open-Meteo per taluka centroid, caches, and fails over gracefully to district bulletin × ratio.
- [ ] Pipeline runs end-to-end for at least 2 talukas in each demo district via `run_demo.py`.
- [ ] `validate.py` regenerated report; README badge + JSON block + `src/api/main.py` fallback all byte-consistent with the report.
- [ ] Map shows taluka input layer + panchayat output layer.
- [ ] No fabricated numbers anywhere in README/PRP/API (grep-check every metric against the report).

## Explicit "do not" list

- Do NOT swap LightGBM for another model family.
- Do NOT pull a second state's data (KSNDMC is a talking point, not a build task).
- Do NOT build real authentication (hashed passwords/sessions/JWT).
- Do NOT hardcode or hand-edit any validation metric — every number must flow from `validate.py`.
- Do NOT let the demo depend on Mausamgram scraping (undocumented endpoint; PoC only, behind a flag).

## Stage talking points unlocked by this migration

1. "Block-level input exists in IMD's operational DAMU pipeline (district **and block** 5-day MRWF); we demonstrate the consumption layer with public proxies."
2. "Mausamgram is IMD's own block/village-level product — here's our working PoC integration."
3. "Where IMD publishes district-only today, we apply a taluka climatological correction derived from Maharashtra Agriculture Dept. taluka rainfall normals — the same data DAMUs use operationally."
4. Validation now honestly describes the shipped system; every README number matches the generated report.
