# Changelog

## 0.1.0a4 — 11 October 2026

Reviewed every runtime, build, test and recovery component. Added audited physical stock counts with required counter/reason; existing schema-2 records and older backup readers remain compatible. Added clear person labels and quantity/status previews, unsaved-edit and Lost/Retired confirmation, fresh dialog reads, named filters, empty-result guidance, F5 refresh, Ctrl+F/Ctrl+N/Ctrl+S shortcuts and failed-read selection clearing. Moved import/export/backup/restore to one background worker with its own SQLite connection, a working dialog, duplicate-operation prevention and guarded shutdown. Preserved the one-table UI, explicit scanner selection and zero runtime dependencies. Windows packaging now rejects non-x64 Python.

36 core and 26 actual-Tk GUI tests pass locally. Added an actual v0.1.0a3 synthetic fixture, reverse-backup compatibility check and worker-failure/keyboard regressions. Linux source/fault/performance/layout checks pass. Native Windows CI must pass on the published commit; physical scanner, target Windows 10/11 installation/DPI/endurance and schema-1 migration remain blocked. Private test candidate only.

## 0.1.0a3 — 11 October 2026

Rebuilt the authorized offline Windows inventory MVP after both prior source archives became inaccessible. Added a separate schema-2 database to retain any previous data unchanged. Reimplemented exact barcode/ID selection, asset custody, material movements, low-stock/status filters, audit snapshots, bounded pagination, atomic CSV, validated backup/restore and single-instance startup. Added independent core/GUI/fault/performance evidence and private Windows build workflow.

This is a new source candidate, not a recovered byte-for-byte v0.1.0a2 or a stable release. Native Windows/HIL and legacy migration remain blocked.

## Historical candidates

0.1.0a1 and 0.1.0a2 were previously produced as local source candidates. Their artifacts cannot currently be retrieved. Historical commit IDs and reported results are recorded in RECOVERY.md for provenance only; they are not present in this repository's reconstructed history.
