# Release verification — 12 September 2026

Final merged-main verification: **71 tests passed**. Production frontend built successfully;
Start-Project.ps1 launched main on port 8000. Health reports block_demo_ready=true;
model evidence endpoint serves the completed benchmark. Browser zoom/tab-switch
regression was rechecked with no console errors. The test run reports two upstream
deprecation warnings and one sandbox-only pytest cache-write warning.

All 15 original CSVs, 13 indexed benchmark files and 15 archived migration blobs
retain their original hashes in main. Benchmark files use Git -text attributes to
preserve original bytes, including their existing line endings.


- Full regression suite: 68 passed (two third-party deprecation warnings).
- After the run-list optimization: API, hybrid service and full-weather subset, 15 passed.
- After stricter rainfall-row parsing: district parser, full-weather and cache subset, 20 passed (includes three added malformed-rainfall cases).
- Frontend production build: Vite 6.4.3, successful; npm install/audit reports zero known vulnerabilities in 71 installed packages.
- Browser: block date/filter and village selection, source/local temperature values, district full-weather propagation, all-weather comparison, training report and five-day bulletin verified.
- Narrow viewport: moved map controls and legend outside the map canvas; keyboard village selector added.
- Browser zoom/unmount callback error found during QA: animated fit/zoom disabled to avoid callbacks against a removed map.
- Original CSV preservation: all 15 files hash-identical to the original workspace inputs.
- Migration archive: all 15 changed Git blobs read back and checked against SHA-256 manifest.
- Training: five lead models completed; reports include temporal/spatial holdouts and heavy-rain failures. Models were not promoted because evidence does not support operational use.

These checks establish software behavior. Forecast accuracy is experimental. Docker is configured but was not executed because Docker is not installed on this machine. Two test dependency deprecation warnings do not affect current execution.
## Weather display update

Cloud cover and wind direction were removed from the displayed map choices,
village details, comparison table and generated bulletin. Original inputs and API
provenance are preserved. Wind speed and humidity are explicitly source forecasts;
the Before/After toggle is hidden for them, and uniform selections show their
single source value. Rainfall and temperature retain their local-adjustment views.
Validation: production frontend build passed; all 9 full-weather tests passed.
