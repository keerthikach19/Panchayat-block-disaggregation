# Preservation and integration record

The old main commit `e96561eb4188cd8838a73f4080088c64480e7337` is retained on
`codex/preserved-migration-e96561e`. The independently working hybrid release
`49ea992048522dcb389a2a1fbb6d171fa7be24b0` remains on `codex/nashik-hybrid`.

`preserved/migration-e96561e.zip` contains exact Git blob bytes for every one of the
15 files changed by the partial migration relative to the verified district base
`7bcf270e01cf2f8467b6f22d580d59114e40e74c`. Its internal PRESERVATION.json records
paths, lengths and SHA-256 hashes. The archive was read back and every hash checked.

The final branch starts from the verified hybrid release. The partial migration's
serving code is not applied wholesale. Integration records main's history while
retaining the verified final tree; obsolete migration-only paths remain available
in the archive and preservation branch. Main is then advanced normally to the
release merge commit. No reset or force-push is used.

All 15 original block CSVs were compared byte-for-byte with the release inputs
before integration. They match. They are committed on main before the merge so
there is no untracked-file collision or deletion of source inputs.
