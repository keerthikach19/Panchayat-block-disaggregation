# PRP: Block-to-Panchayat Weather Downscaling System for Agro-Meteorological Advisory

**Target: Smart India Hackathon PS 26074 — Ministry of Earth Sciences / India Meteorological Department**
**Category:** Software | **Theme:** Agriculture, FoodTech & Rural Development

---

## 0. HOW TO USE THIS DOCUMENT (read this first, agent)

You are being asked to build a complete, working software system, not a demo mockup. Every section below is a real requirement, not a suggestion menu — do not silently drop scope because something looks hard; if a step is genuinely blocked (e.g. a data source is down), stop and report the blocker instead of substituting fake data without saying so. Where this document gives an exact URL, command, or API endpoint, it has been verified to actually exist — use it as given rather than inventing an alternative. Where this document says "verify before committing," it means the correct answer depends on empirical data you don't have yet (e.g. station density in a specific district) — do that verification step first and report the result before building on top of it.

Work in the order the sections are numbered, with one exception: Section 3 (training footprint & target district) is now a **locked decision** (Maharashtra / Nashik, with reasoning included) rather than a task to perform — read it before executing Section 2.7's download steps, since those steps reference Maharashtra and Nashik by name, even though it appears later in document order. Section 2 (external data access) has to be attempted on day one because some sources may turn out to be slower than expected even though none require approval.

**Critical modeling constraint, read before Section 3:** the deviation model (Section 5, Layer B) must NOT be trained on a single district. A single district has too little terrain/land-cover diversity for a model to learn a generalizable elevation/land-cover → weather-deviation relationship — it will overfit to that district's narrow conditions rather than learn real physics. There are two separate spatial scopes in this project and they must not be collapsed into one: a **training footprint** (broad — state or agro-climatic zone, used to train Layer B on many diverse station-grid pairs) and a **target/demo district** (narrow — one district within that footprint, used for the live demo, Layer C local correction, and validation). See Section 3 for how to pick both.

If at any point you are about to fabricate a number, a station reading, a boundary, or a dataset that isn't from the sources listed here — stop and flag it instead. Fabricated data invalidates the entire validation story of this project.

**Who does what:** you (the agent) execute every download, script, and setup step in this document yourself — including Section 2.7's data pulls and the project directory structure — via your own shell/code execution. The human is not expected to manually download files or set up folders; if you cannot execute a step (e.g. no shell access in your environment), say so explicitly rather than silently asking the human to do it instead.

---

## 1. PROBLEM FRAMING (internalize this before writing any code)

**What this is:** IMD currently issues agro-meteorological advisories at block level, generated at ~530 District Agromet Units (DAMUs) hosted at KVKs, following the GKMS (Gramin Krishi Mausam Sewa) SOP. Farmers within a block can experience meaningfully different weather (elevation, land cover, coastal proximity all cause real sub-block variation), but the advisory doesn't reflect that. The task is to disaggregate block-level forecasts down to panchayat level in a way that is physically justified and honestly validated.

**What this is NOT:** This is not image super-resolution and not a black-box deep-learning downscaling problem. There is no true high-resolution ground truth at panchayat scale anywhere in India — IMD's finest gridded product is ~0.1° (~10km), while a panchayat is typically 2-8km across. Do not build or claim a system that "predicts the true panchayat value" — build a system that infers a **physically plausible, uncertainty-quantified panchayat estimate** using elevation, land cover, and station-anchored correction, and validates it the only way that's actually possible: against real point-station observations, not against non-existent panchayat ground truth.

**State this framing explicitly in any generated documentation, pitch materials, or UI copy.** It preempts the single hardest question a judge with meteorological background will ask, and it's honest.

**The train-broad, apply/validate-narrow principle:** the physical relationship this system learns (how elevation, slope, aspect, land cover, and coastal distance translate into local deviation from a coarse grid value) is only learnable from a spatially diverse training set — many station-vs-grid-cell pairs spanning varied terrain and land cover. A single district rarely has that diversity. So: Layer B (Section 5) is trained on a **wide training footprint** (Section 3a), and the resulting model is then **applied and locally corrected** for a **specific target district** (Section 3b) used for the live demo. Do not train a district-specific model from scratch — train once on the footprint, apply everywhere within it. This mirrors how real operational statistical-downscaling systems work (e.g. PRISM-style approaches): learn the terrain-climate relationship broadly, apply it locally.

---

## 2. DATA SOURCES — verified, zero-approval, exact access method

Do not substitute Bhuvan/CartoDEM login-gated sources for the two categories below — the free alternatives are equal or better in quality, already verified to work with no account and no wait.

**Scale note (read before pulling anything):** DEM, land cover, and station data must be pulled for the **training footprint** (Section 3a — a full state or agro-climatic zone), not just the target district — otherwise Layer B has nothing diverse to learn from (see Section 0/1). Gridded rainfall/temperature (IMDLIB, IPED) cost the same to pull regardless of area since they're already national in scope, so pull the footprint's extent for those too, no extra effort. Boundaries should be pulled for the full state containing the target district, so both footprint aggregation and target-district panchayat detail are available from one download.

### 2.1 Elevation (primary: Copernicus DEM GLO-30, fallback: SRTM GL1)
- Copernicus DEM GLO-30 (30m, void-filled, newer than CartoDEM): public S3 bucket `copernicus-dem-30m`, pull with AWS CLI using `--no-sign-request`. No account needed.
- SRTM GL1 (30m) fallback: public S3 bucket via OpenTopography, endpoint `https://opentopography.s3.sdsc.edu`, bucket path `s3://raster/SRTM_GL1/`, also `--no-sign-request`.
- Action: write a scripted, re-runnable pull (not a manual one-time download) for the training footprint's bounding box + buffer.

### 2.2 Land cover (ESA WorldCover 10m — strictly better than Bhuvan LULC)
- Public S3 bucket `s3://esa-worldcover/`, versions v100 (2020) and v200 (2021), Cloud-Optimized GeoTIFFs, Creative Commons Attribution 4.0 license. `--no-sign-request` bulk sync, or restrict to a bounding box via the provided download script pattern.
- 11 standard land-cover classes (tree cover, shrubland, grassland, cropland, built-up, bare/sparse veg, snow/ice, permanent water, herbaceous wetland, mangroves, moss/lichen).

### 2.3 Gridded rainfall & temperature
- **IMD 0.25° daily gridded rainfall (1901-2024)**: via `pip install imdlib` (handles download + conversion to NetCDF/GeoTIFF, no manual `.grd` binary parsing needed).
- **IMD 1° gridded temperature**: same IMDLIB library.
- **IPED — Indian Precipitation Ensemble Dataset** (primary training signal, recommended over raw IMD grid where possible): 30-member ensemble, 0.1°/0.25° resolution, elevation/slope/aspect correction already built in, published *Scientific Data* (2025). Hosted on **Zenodo** — direct download, no account: `10.5281/zenodo.8199138` (check for the newer 2025 release version at `zenodo.org/records/15618220` as well, use whichever is more current at build time).
- **NASA POWER** (secondary/fallback source, and for solar radiation/wind/humidity that IMD/IPED don't cover well): REST API, no auth, `https://power.larc.nasa.gov/docs/services/api/`. Also useful for evapotranspiration-driven irrigation advice.

### 2.4 Administrative boundaries
- **Panchayat/block/district boundaries**: `india-geodata` GitHub repo (github.com/yashveeeeeeer/india-geodata) — direct download, GeoJSON/Shapefile/Parquet formats, sourced from LGD + Bhuvan + eGramSwaraj. Download the full **Maharashtra** subset (not just Nashik), since it's needed both for footprint-wide covariate computation and for Nashik's panchayat detail specifically.
- **LGD (Local Government Directory)**: `lgdirectory.gov.in` — official state→district→block→panchayat→village code hierarchy, open CSV/API download, no boundary shapes but needed to correctly join panchayat polygons to block names.
- **DataMeet Village Boundaries** (backup): `projects.datameet.org/indian_village_boundaries/`, community-maintained GeoJSON by state.

### 2.5 Point-station validation & training data (the one genuinely harder source — no single clean bulk download exists)
This data serves two purposes now, not one: it's the **training set** for Layer B (station location + covariates + observed deviation from its enclosing grid cell, across the whole footprint) AND the **validation backbone** for the target district specifically. There is no one-shot bulk CSV; assemble from multiple no-login sources, prioritizing spatial *diversity* across the footprint (different elevations, coastal vs inland, different land-cover types) over density in any single spot:
- **Maharashtra-specific, high-value: Mahavedh / Maharain.** Maharashtra runs its own state AWS network (Mahavedh, operated via PPP with Skymet Weather Services) at circle level — over 2,000 stations statewide, finer than block resolution. Publicly viewable via the state portal `maharain.maharashtra.gov.in`. Treat this as your primary station source for this project (Section 3 locks Maharashtra as the training footprint specifically in part because of this network's density) — use it alongside, not instead of, the IMD/data.gov.in sources below, since cross-referencing multiple sources strengthens the validation story.
- IMD's public station/district rainfall pages (e.g. under `mausam.imd.gov.in`, "Station Rainfall" / district-wise rainfall monitoring interactive pages) — real daily station observations, viewable and scriptable/scrapable, no login.
- `data.gov.in` IMD-released rainfall resources under the National Data Sharing and Accessibility Policy (NDSAP) — open government CSV/data resources, no-login download for listed catalog resources.
- IMD's public API (`api.imd.gov.in`) — endpoints for district rainfall, district nowcast, current weather. No stated auth requirement. Note: verify exact endpoint names at build time (`districtrainfall`, `districtnowcast`, `current_wx` or similar — confirm actual path from `mausam.imd.gov.in/responsive/apis.php` before hardcoding).
- **Fallback only, not a substitute for validation**: NASA POWER at panchayat centroids — satellite/reanalysis-derived, NOT ground truth. May be used for a physical-plausibility consistency check but must be labeled in all outputs as "modeled estimate, not station observation."
- Treat assembling this as a **day-one task**, not something to timebox alongside modeling work — see Section 3.

### 2.6 Reference document for advisory format
- GKMS SOP: `mausam.imd.gov.in/imd_latest/contents/pdf/gkms_sop.pdf` — defines the exact bulletin structure IMD's own DAMU officers currently use. The advisory generation module (Section 6) must structurally mirror this, not invent its own format.

### 2.7 Exact step-by-step download procedure

Do these in order. Steps 1-2 must complete first since every later step needs the bounding boxes they produce.

**Step 1 — Get the state boundary and compute bounding boxes.**
1. Download **Maharashtra's** boundary + all panchayat/block/district layers within it from `india-geodata` (GeoJSON format is easiest to start with).
2. Load the state boundary in geopandas and compute `.total_bounds` — this gives the training-footprint bounding box (lat/lon min/max).
3. Load **Nashik district's** polygon (filtered from the same state file) and compute its own `.total_bounds` — this gives the target-district bounding box, a subset of the footprint box.
4. Add a small buffer (~0.1-0.2°) to both boxes so edge panchayats/tiles aren't starved of covariate context.

**Step 2 — Download LGD codes.**
Download the state's code-hierarchy CSV from `lgdirectory.gov.in` directly (no login) — used later to join panchayat polygons to block names correctly.

**Step 3 — Download elevation for the footprint bounding box.**
1. Identify which Copernicus DEM GLO-30 tiles intersect the footprint bounding box (tiles are named by 1°×1° lat/lon cell, e.g. `Copernicus_DSM_COG_10_N17_00_E078_00_DEM`).
2. Pull only those tiles: `aws s3 cp s3://copernicus-dem-30m/ <local_dem_folder>/ --recursive --no-sign-request` restricted to the identified tile prefixes (loop over tile names rather than syncing the whole bucket).
3. If any tile is missing/unavailable, pull the equivalent SRTM GL1 tile as fallback from `s3://raster/SRTM_GL1/` via `--endpoint-url https://opentopography.s3.sdsc.edu --no-sign-request`.

**Step 4 — Download land cover for the same footprint bounding box.**
1. Identify which ESA WorldCover 3°×3° tiles intersect the footprint bounding box (check the tile grid reference on the WorldCover site).
2. Pull only those tiles: `aws s3 sync s3://esa-worldcover/v200/2021/map <local_landcover_folder>/ --no-sign-request`, restricted to the identified tile filenames.

**Step 5 — Pull gridded rainfall and temperature.**
1. `pip install imdlib`.
2. Use IMDLIB's data-retrieval function with the footprint's date range and let it handle download + NetCDF conversion; save output to the rainfall/temperature raw folders.

**Step 6 — Download IPED from Zenodo.**
Go to the current IPED Zenodo record page, download the NetCDF file(s) covering the training-footprint years and region directly (plain file download links, no account/login).

**Step 7 — Assemble station data across the footprint.**
1. Pull from Mahavedh/Maharain (`maharain.maharashtra.gov.in`) for as many of Maharashtra's ~2,000+ circle-level AWS as the portal allows for the training period — this should be your largest single source of training rows given the network's density.
2. Query IMD's public API district endpoints for every Maharashtra district that intersects the footprint bounding box (not just Nashik).
3. Cross-check against `data.gov.in`'s IMD rainfall catalog resources for Maharashtra.
4. Manually supplement from IMD's public station/district rainfall pages for any gaps, prioritizing terrain/land-cover diversity over raw count (specifically ensure Konkan coastal, Sahyadri high-elevation, Deccan plateau rain-shadow, and Vidarbha stations are all represented, not just stations near Nashik).
5. Store all of this as one combined CSV with columns: `station_id, lat, lon, date, rainfall_mm, temp_c, source`.

**Step 8 — Sanity check before moving to Section 4.**
Confirm: (a) DEM and land cover rasters actually cover the full Maharashtra bounding box with no gaps, (b) the station CSV has a non-trivial number of stations spread across all four Maharashtra physiographic zones (Konkan, Sahyadri, Deccan plateau, Vidarbha), (c) Nashik specifically has enough stations (IMD/data.gov.in + any Mahavedh circles that fall within it) for the Layer C density check. If any of these fail, resolve before writing the PostGIS ingestion scripts — building Section 4 on top of incomplete data just moves the failure later and makes it harder to diagnose.

---

## 3. TRAINING FOOTPRINT & TARGET DISTRICT SELECTION — FINAL: Maharashtra / Nashik

This decision is now locked, not open for the agent to re-derive. The reasoning is included so the choice can be defended to judges, not because it needs re-verifying.

### 3a. Training footprint: **Maharashtra**

Maharashtra satisfies every diversity criterion with margin, and is large enough to give the model real training volume:
- **Terrain diversity**: spans the Konkan coastal strip (sea level), the Sahyadri/Western Ghats crest (peaks over 1600m, e.g. Kalsubai), the Deccan plateau (semi-arid, rain-shadow), and Vidarbha in the east — four distinct physiographic zones in one state.
- **Rainfall/climate diversity**: annual rainfall within the state ranges from over 3000mm on the Ghats' windward slopes to under 500mm in the rain-shadow belt — one of the sharpest rainfall gradients of any Indian state, and it's driven by the same orographic mechanism the model needs to learn.
- **Land-cover diversity**: dense Western Ghats forest, irrigated sugarcane/grape/onion belts, semi-arid jowar/bajra tracts, coastal Konkan cropping — genuine spread across ESA WorldCover's classes, not a monoculture state.
- **Station density — a major, verified advantage specific to this choice**: beyond the standard IMD AWS/ARG network, Maharashtra runs **Mahavedh** (Maharashtra Agriculture Weather Information Network), a state PPP with Skymet Weather Services that has installed **AWS at the rate of one per revenue circle — over 2,000 stations statewide** (public reporting cites figures from ~2,060 to 2,335 depending on year), publicly viewable via the state's weather data portal (`maharain.maharashtra.gov.in`). This is a materially denser network than a generic IMD-only approach in almost any other state, and it's sub-block (circle-level) resolution — genuinely useful both as extra Layer B training rows and for Layer C's local correction. Treat this as an additional entry under Section 2.5, not a replacement for IMD/data.gov.in sourcing — pull from both.

### 3b. Target/demo district: **Nashik**

Nashik sits inside the Maharashtra footprint and is an unusually strong single-district showcase:
- **Extreme internal rainfall/elevation gradient, documented in multiple independent sources**: Igatpuri taluka (western, Sahyadri crest) records annual average rainfall around 3,000-3,100mm, while Deola/Malegaon taluka (eastern, rain-shadow Deccan plateau) records under 500mm — roughly a 6x difference **within the same district**. This is close to the most dramatic sub-district contrast available anywhere in India, and it makes the "block-level average completely erases this" argument immediate and visual on the map dashboard.
- **Three distinct microclimate zones inside one district**: the western talukas (Igatpuri, Trimbakeshwar, Peth, Surgana) have Konkan-like weather; the central talukas (Niphad, Sinnar, Dindori) resemble Western Maharashtra's plateau climate; the eastern talukas (Yeola, Nandgaon, Chandwad) resemble Vidarbha's drier climate — three physically distinct regimes in one district boundary.
- **Real existing station coverage**: published rainfall studies of Nashik district already work from 15 tehsil-level rain-gauge stations with multi-decade records, which is a solid starting point for both Layer B's local rows and Layer C's district-level correction, before even adding Mahavedh's circle-level AWS on top.
- **Weather-sensitive, well-documented crop for the advisory narrative**: Nashik is India's largest grape-growing district (concentrated in the canal-irrigated southern portion around the Godavari), and grape cultivation is acutely weather-sensitive — humidity and rainfall timing directly drive downy mildew risk, a real, high-stakes decision that maps cleanly onto Section 6's threshold-based advisory logic. The eastern semi-arid talukas' jowar/bajra/onion mix adds a second, contrasting crop-advisory case within the same district.
- **DAMU/KVK presence**: Nashik has an active Krishi Vigyan Kendra network consistent with the standard DAMU-hosting model described in the GKMS SOP (Section 2.6) — verify the current DAMU/KVK contact and bulletin format from the KVK Nashik or imdagrimet.gov.in listing as a first build step, since institutional contact details can change and shouldn't be hardcoded from this document without a live check.

**Second district for the multi-district scalability proof (Section 4, Layer 6)**: pick any other Maharashtra district with a real but less extreme gradient (e.g. Pune or Satara, both of which also span Sahyadri-to-plateau) — this both proves district-agnostic scaling and gives a second, less extreme case to contrast against Nashik's dramatic one.

**Note on effort still required from the build team:** the reasoning above is geographic/climatological and drawn from published sources, not from having already pulled and inspected the actual DEM/WorldCover/station data. Section 2.7's Step 8 sanity check still applies — confirm the real pulled rasters and assembled station CSV match this expected diversity before building Section 4 on top of them, since the final word on data quality is the data itself, not the literature about it.

---

## 4. SYSTEM ARCHITECTURE OVERVIEW

Six layers, all core (no tier system — see Section 8 for what to explicitly exclude instead of what to deprioritize):

1. **Data ingestion layer** — scripted, re-runnable pulls of all Section 2 sources, cached locally (NetCDF/GeoTIFF/shapefile), consistent CRS handling across all sources (get this right early — it is the most common silent-failure point in GIS pipelines under time pressure).
2. **Feature/covariate store** — PostGIS database. Panchayat polygons as anchor geometry, joined attribute table: mean elevation, elevation std/range (terrain heterogeneity proxy), slope, aspect, LULC class fractions, distance to nearest major water body, distance to coast (if relevant), historical climatological deviation from block mean (computable from IPED's historical range). Computed for every panchayat across the **training footprint** (Section 3a), not just the target district, since Layer B needs footprint-wide covariates for training; the target district's subset is what gets served in the application layer. Computed once, reused across every model run and every district within the footprint — this is what makes "any district in this footprint via config" a true claim.
3. **Modeling layer** — bias/anomaly decomposition → deviation model (LightGBM/XGBoost, **trained once on the full training footprint's station-grid pairs**, Section 3a) → kriging-with-external-drift residual correction (**applied locally to the target district**, data-density-permitting; see Section 3b) → ensemble/uncertainty propagation via IPED's 30 members.
4. **Advisory generation layer** — deterministic rule engine, GKMS SOP-structured, crop-calendar aware, historical-normal-anchored. Optional LLM layer strictly for natural-language/regional-language rendering of already-decided structured output — the decision logic itself must stay deterministic and auditable, never LLM-inferred agronomy.
5. **Application layer** — map dashboard, explainability panel, DAMU officer review/approve/edit workflow, feedback logging, mocked dissemination preview.
6. **Multi-district scalability proof** — demonstrate (not just claim) that Layers 1-2 work for a second district by actually running the pipeline against it.

---

## 5. MODELING SPECIFICATION

### Layer A — Decomposition
Applies across the whole training footprint. For each block (or grid cell, where blocks aren't the natural unit), compute the block-mean value (rainfall, temperature separately) for each forecast/observation period. For each station location or panchayat inside that block, define the modeling target as the **local deviation**: `local_value = block_value + local_deviation`. Model the deviation, not the raw value — this is what your covariates actually explain.

### Layer B — Deviation model (trained once, footprint-wide)
Gradient-boosted trees (LightGBM or XGBoost), separately tuned per variable (rainfall and temperature have different dominant covariates — elevation lapse rate matters far more for temperature than rainfall, which is more driven by orographic/coastal effects). **Training set: every AWS/ARG station location across the training footprint (Section 3a), each contributing (covariates at that point, observed local deviation from its enclosing grid cell) as one training row, across all available historical days** — this is what gives the model enough diverse examples to learn a generalizable relationship rather than overfit to one district. Full feature set: elevation, elevation std/range, slope, aspect, LULC class fractions, distance to water body, distance to coast, historical climatological deviation. Produce and retain feature importance output per variable — this becomes the explainability panel content (Section 7). **Do not retrain this model per district** — train once on the footprint, then apply it (inference only) to every panchayat's covariates, in the target district or any other district within the footprint.

### Layer C — Geostatistical residual correction (applied locally, target district only)
Kriging-with-external-drift on the already-trained Layer B model's residuals, anchored to AWS/ARG station residuals found **within and near the target district specifically** (Section 2.5/3b) — this step is inherently local by design, unlike Layer B. **Conditional on station density**: if the target district's confirmed station count is too low for a stable variogram fit, use ordinary kriging or IDW instead and document why — this is a legitimate, defensible design decision, not a shortcut, and must be stated as such in any output-facing documentation.

### Layer D — Ensemble/uncertainty propagation
Using IPED's 30-member ensemble, propagate the spread through Layers A-C to produce a genuine per-panchayat confidence interval, not a single point estimate. This is a real technical differentiator — implement it fully, it is core.

### Validation (run all of these, not a subset)
- Leave-station-out cross-validation against every AWS/ARG station found.
- RMSE/MAE vs. the naive baseline (uniformly assigning the block value to every panchayat inside it) — report % improvement over this baseline as the headline metric.
- Pearson correlation, predicted vs. station-observed.
- POD (Probability of Detection) / FAR (False Alarm Ratio) for rain/no-rain and for the ~20mm agricultural action threshold.
- Spatial plausibility checks (e.g. elevation-rainfall correlation sign matches known orographic behavior for the district).
- Reliability/spread-skill diagram using the Layer D ensemble output.

### Explicitly excluded from this project (do not build these regardless of time available)
- CNN/deep-learning super-resolution downscaling — insufficient training data volume for a hackathon build, fragile to defend under judge questioning about validation.
- Any claim of "true panchayat accuracy" without the station-cross-validation caveat stated alongside it.

---

## 6. ADVISORY GENERATION ENGINE SPECIFICATION

- Deterministic rule table, structured to mirror GKMS SOP bulletin fields (Section 2.6) exactly — same field names/order where feasible, so a DAMU officer recognizes the format immediately.
- Full threshold library, not a partial one: heavy rain (~64.5mm/day IMD categorical threshold), dry spell length threshold, heat stress threshold, ~20mm irrigation/spray decision threshold — plus any other thresholds standard to the district's dominant crop.
- Crop-calendar logic: use the real dominant crop(s) of the selected district (Section 3) across their actual growth stages for the demo season — source real agronomic lookup data (state agriculture department crop calendars, KVK advisories), do not placeholder this.
- Every advisory output must express the forecast as a **deviation from that panchayat's own historical climatology**, not a raw number — this is what makes it actionable rather than just informative.
- LLM layer (optional, for natural-language + regional-language rendering only): input is the fully-decided structured rule-engine output; output is human-readable text. The LLM must never be in the decision-making path.

---

## 7. APPLICATION LAYER SPECIFICATION

- **Map dashboard**: panchayat polygons colored by predicted value; block-boundary overlay showing "before vs after disaggregation" contrast; uncertainty shown as a real visual layer (e.g. opacity/hatching tied to confidence), not just a tooltip number.
- **Explainability panel** (per panchayat, click-through): feature-importance/SHAP-style breakdown of why this panchayat's value differs from its block mean, full advisory text, confidence band, distance to nearest validating station.
- **DAMU officer review workflow**: every generated advisory must pass through an explicit review/edit/approve UI state before being marked "sent" — this is core, not decorative; it mirrors IMD's actual human-in-the-loop process and signals to judges with a meteorological background that the system augments officers rather than replacing them.
- **Feedback/logging table**: real table capturing officer edits/corrections during actual use — this is your visible MLOps feedback-loop evidence, not a claimed feature.
- **Dissemination preview panel**: mocked SMS/WhatsApp/mKisan-style preview showing exactly what would be sent. Do not wire up live SMS/WhatsApp delivery — see Section 8.
- **Multilingual rendering**: actually render generated advisory text in at least one regional language relevant to the selected district, live in the UI.

---

## 8. EXPLICIT NON-GOALS (state these on stage as deliberate choices, not omissions)

- No live/real SMS, WhatsApp, or IVR delivery integration — mocked preview only. Live third-party delivery integrations are a common live-demo failure point and not worth the risk.
- No pan-India coverage claim — single district for the live demo, second-district run only to prove the architecture is genuinely district-agnostic (Section 4, Layer 6).
- No CNN/deep-learning downscaling model.
- No claim of validated "panchayat ground truth accuracy" — only station-cross-validated accuracy, explicitly labeled as such everywhere it's displayed.

---

## 9. TECH STACK

- **Ingestion/processing**: Python (IMDLIB, xarray/rioxarray for NetCDF/GeoTIFF, geopandas for vector data, boto3/AWS CLI for S3 pulls)
- **Feature store**: PostgreSQL + PostGIS
- **Modeling**: LightGBM or XGBoost, PyKrige (or equivalent) for kriging-with-external-drift
- **Model serving**: FastAPI
- **Frontend**: React + Leaflet (or Mapbox GL) for the panchayat map dashboard
- **Advisory rule engine**: plain Python rule table/decision logic (no ML in this layer's decision path)
- **Database for advisory/feedback logging**: same PostGIS/PostgreSQL instance, separate tables

---

## 10. BUILD ORDER (dependency-aware — follow this sequencing, not the section order, for actual execution)

1. **Day 1, in parallel**: (a) read Section 3 (locked: Maharashtra footprint, Nashik target district) and do the Section 2.7 Step 8 empirical sanity check once initial pulls land, (b) kick off scripted pulls for all Section 2 data sources at Maharashtra scale (Section 2.7 steps 1-6), (c) stand up the PostGIS instance and boundary ingestion for Maharashtra.
2. **Day 2-3**: build the feature/covariate store (Section 4, Layer 2) across the full footprint once boundaries + DEM + LULC are in; begin Layer A/B modeling (footprint-wide training set) once gridded weather data + covariates are joined.
3. **Parallel track from Day 1**: begin assembling AWS/ARG station data across the footprint (Section 2.5/2.7 step 7) — this has the least predictable timeline of any component precisely because it's manual/semi-automated, so start early and treat it as an ongoing background task, not a scheduled sprint. Prioritize diversity across the footprint first, then confirm the target district specifically has enough for Layer C.
4. **Day 3-5**: Layer C (kriging, applied to the target district, conditional on its confirmed station density) and Layer D (ensemble propagation) once Layer B is trained and validated against the naive baseline.
5. **Parallel from Day 2**: advisory rule engine + crop-calendar data collection (Section 6) — independent of model completion, can be built against synthetic/placeholder forecast values until Layer B/C/D are ready, then wired together.
6. **Parallel from Day 2**: frontend dashboard shell + DAMU review workflow UI — build against mocked API responses first, wire to real FastAPI serving layer once Section 9's serving layer is up.
7. **Final phase**: full validation suite (Section 5) run and results captured; second-district run (Section 4, Layer 6) executed and results captured for the pitch; multilingual rendering and dissemination-preview mock finished last, as they're the lowest-risk, most cosmetic pieces.

---

## 11. DEFINITION OF DONE

The project is demo-ready when all of the following are true, not just built:
- A live map shows block-level vs. disaggregated panchayat-level values for the selected district, toggleable.
- Clicking any panchayat shows its explainability breakdown, confidence band, and advisory text.
- The full validation metric suite (Section 5) has been run and the results (including the honest station-density-driven kriging-vs-IDW decision) are documented and ready to state verbatim if asked.
- At least one advisory has gone through the DAMU review/edit/approve flow live, with the edit visible in the feedback log table.
- The pipeline has been run end-to-end for a second district **within the same training footprint** and that output is available to show — and it's clear in any explanation that this reuses the one footprint-trained Layer B model, not a retrained one.
- The framing in Section 1 (disaggregation, not prediction of true ground truth; station-validated, not panchayat-validated) is reflected consistently in every piece of UI copy, advisory text, and any prepared pitch material.
