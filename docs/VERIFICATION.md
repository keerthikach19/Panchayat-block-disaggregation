# Release verification — 12 September 2026

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
