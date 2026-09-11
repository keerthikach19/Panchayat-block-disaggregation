# Baseline and preservation

Original checkout: `main`, `e96561eb4188cd8838a73f4080088c64480e7337`.
Only untracked user inputs were `Block-level data/` (15 CSV files, issue 2026-09-10).
No repository AGENTS.md was found. Original checkout, migration, inputs and model artifacts are preserved.
Implementation checkout: `.worktrees/nashik-hybrid`, branch `codex/nashik-hybrid`,
based on district implementation `7bcf270e01cf2f8467b6f22d580d59114e40e74c`.
Input copies and model hashes are recorded in baseline-input-hashes.json.

The baseline's three IMD parser tests pass. The default Python lacks pytest and
scientific/API packages; an isolated .venv is being used for further verification.
Tests that write forecasts are run with CSV writes intercepted and training disabled.
No baseline check trains or replaces artifacts.

Further verification of 7bcf270: six collected IMD/Layer C tests passed (2.93s),
existing dynamic-advisory assertions passed during collection, and the original
three-step API smoke script passed (forecast, explanation, dissemination preview).
The packaged model loaded with 40 cached LOSO station predictions; no training ran.
CSV writes were intercepted. This verifies the district baseline's software paths,
not its scientific claims. Frontend esbuild requires sandbox escalation on Windows.

Migration diff: 15 files, 1,903 insertions / 2,073 deletions. Reviewed block_live,
Layer A/B/C/D, pipeline, validation, feature builder, API, App, MapDashboard,
ExplainabilityPanel, ValidationView, metadata, covariates and boundaries.
Do not reuse the Open-Meteo/ratio fallback, default taluka training, mutable output
CSV or heuristic dissolved block boundaries. Reuse only the explicit per-parent
input association concept and single-station zero-deviation regression case,
implemented with strict district/block identities and no silent fallback.

Geography: 1,953 Nashik village polygons; all GP code fields blank. Covariates
contain 37 Central rows with ambiguous block membership. Four features share the
placeholder identifier MH_487_999999. Do not claim these IDs are GP/LGD codes.
Raw village properties retain subdistrict labels, but they do not establish a
village-to-GP crosswalk or verified development-block membership.

Known defects: cached IMD requests retain the previously selected date; HTML is
sent straight to a PDF reader; expired bulletins lack honest freshness labels;
unknown district can select all covariates; normal inference can train/write;
fixed ensemble noise is presented as confidence; API/UI have fabricated fallback
values and old metrics. Existing covariates include heuristic terrain/LULC values.
These are not evidence of independently validated local forecast skill.
