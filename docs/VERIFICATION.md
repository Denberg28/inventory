# Candidate verification — 0.1.0a3

11 October 2026. Reconstructed source self-review and independent software validation; original archives/fixtures were inaccessible. No earlier results are reused. Current Git commit is the source identity; delivery verification compares every remote Git blob against the reviewed local files.

Environment: Linux x86_64, kernel 6.18.44/glibc 2.39, Python 3.12.14, Tk 9.0, SQLite 3.53.1. Actual Tk widgets ran on an authenticated isolated Xvfb desktop with synthetic test data/keyboard events. Rendered layouts were inspected at 1120x700 and 880x560 and in Add dialog; Linux bitmap fallback fonts are not native Windows typography. Formatter: Black 26.10.1, used as a temporary development tool, not a runtime dependency.

| Gate / check | Status | Evidence / limits |
| --- | --- | --- |
| A — Syntax/configuration | PASS | Compile and source checks, version/schema agreement; runtime standard library only |
| A — Limited security checks | PASS | Runtime import/dynamic execution/secret-pattern gates and manual path/SQL/input review; not a comprehensive security audit |
| A — Build dependency availability | PASS | All seven pinned Windows build wheels resolved/downloaded for CPython 3.12 win_amd64; PyInstaller 6.22.3 verified against official release |
| B — Core/integration | PASS | 32 tests: custody, stock, identifiers, input, audit rollback, stale edits, CSV, report guards, backup/restore, locked handle simulation, probe and instance lock |
| B — Actual Tk GUI | PASS — simulator tested | 19 tests: add/edit, 100 Return-key scans, unknown/invalid/cancel, asset/material actions, timers/pages, historical snapshots, data menus, saved-but-refresh-failed, long notes, About/modal focus, startup failure/lock cleanup and 20 app restart cycles plus three real main-loop restarts |
| B — Layout | PASS on Linux display | All required main controls visible at minimum size; PNGs retained. Native Windows/DPI BLOCKED |
| C — Schema-2 compatibility | PASS | Same-version backup restores stock/custody/history with a recovery copy |
| C — Legacy schema-1 migration | BLOCKED | Original source/fixture unavailable; separate DB filename preserves old data, unsupported versions rejected unchanged |
| D — Crash/lock integration | PASS — simulator tested | Uncommitted abrupt-exit rollback; committed stock/audit retained; integrity after both. Locked copy fails in approximately 0.15 s with a 0.15 s test budget; physical power loss BLOCKED |
| D — Performance | PASS on builder | 10000 records / 20 queries; median about 4 ms against <250 ms criterion. Actual values in performance.json; target PC repeat BLOCKED |
| E — Scanner/target PC HIL | BLOCKED | No scanner/Windows hardware available; runnable procedure in TESTING.md |
| E — Equipment control | N/A | Scanner input only; app commands no motor/device, so authority/watchdogs/output safety do not apply |
| F — Windows EXE / install | BLOCKED locally | Windows-only build/private CI configured and self-reviewed; no local EXE or clean target installation tested |
| Remote CI / publication | NOT TESTED at source preparation | Push may start private CI; inspect its actual status separately. No public or stable release authorized |

32 core + 19 GUI = **51 tests passed**. Actual logs/measurements/rendered screenshots are in docs/evidence. Dependency audit for runtime third-party libraries is N/A: none are required. SQLite/Tk/Python platform security and the optional build tool supply chain are outside the limited static gate. No known critical/high defect remains within the tested scope. Missing native/HIL/legacy evidence blocks stable promotion.

## Review resolutions

- Stock/custody transactions begin before reads and commit audit/state together, preventing cross-namespace races and lost revisions.
- Exact scan queries are independent of 250-row substring pages; unknown/invalid scans disable previous actions.
- Deferred search timers cannot reset explicit pages or scans. Modal input owns F2 until it closes.
- Successful item/movement/import/restore commits are distinguished from subsequent read errors; dialogs cannot repeat a save, and stale actions are cleared.
- Online backup explicitly closes its destination before Windows rename; bounded retries cannot report an already committed copy as failed.
- Restore checks expected schema/objects, full sequential revisions, snapshot/state agreement, custody, deltas and UTC times before recovery/replace.
- Text and CSV boundaries reject missing/noncanonical input, normalize CRLF, guard report formulas and reject active DB/journal/lock outputs.
- Preserved immutable IDs/category, separate report/import formats, one asset per record, retired records and full ledger retention keep the MVP workflow predictable.

Rollback and source-loss limitations are explicit in RECOVERY.md. This is a rebuilt private source test candidate, not the lost v0.1.0a2 and not a stable release.
