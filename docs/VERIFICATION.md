# Candidate verification — 0.1.0a4

11 October 2026. Self-review of the complete repository; scoped runtime/workflow changes independently verified. Preserved known-good baseline: remote c65ef374badbf9309f6d81bcb4548273a9e8afaa (v0.1.0a3). Baseline private [CI run 38153365247](https://github.com/Denberg28/inventory/actions/runs/38153365247) passed Linux software/GUI and Windows Server 2025 x64 native build/bundled probe. Earlier lost schema-1 results are not reused. See [complete feature review](REVIEW.md).

Local environment: Linux x86_64, kernel 6.18.44/glibc 2.39, Python 3.12.14, Tk 9.0, SQLite 3.53.1. Actual Tk widgets ran on an authenticated isolated Xvfb desktop with synthetic records and keyboard events. Layouts inspected at 1120x700, 880x560, Add and Stock count dialogs; Linux fallback fonts differ from Windows Segoe UI. Black 26.10.1 was a temporary development formatter, not a runtime dependency.

| Gate / check | Status | Evidence / limits |
| --- | --- | --- |
| A — Source/configuration | PASS locally | Compile/source/version/schema gates; zero runtime pip packages; unchanged package/data identity; Windows build rejects non-x64 Python |
| A — Limited sanitization | PASS | Runtime network/dynamic-execution restrictions and secret-pattern scan across runtime/tests/scripts/workflows/docs/evidence; manual SQL/path/input/thread/handle review, not a comprehensive security audit |
| B — Core/integration | PASS | 36 tests: identifiers, custody, stock, audit rollback, stale revisions, all count directions, CSV/report, backup/restore, handle ordering, probe/lock and actual a3 fixture |
| B — Actual Tk GUI | PASS — simulator tested | 26 tests: baseline flows, 100 simulated scans, counts/previews, dirty/status confirmations, actual keyboard shortcuts, pending-search F5, worker heartbeat/duplicates/close/start/connection/write errors, commit/read-error distinction, layout, data menus, modal focus and lifecycle |
| B — Layout | PASS on Linux | Main controls at minimum size; Add and Stock count layouts inspected; synthetic PNGs retained. Target Windows DPI/accessibility BLOCKED |
| C — Schema-2 upgrade | PASS | Actual unchanged-a3-generated fixture retains IDs/leading zeros/custody/stock/history under a4; a4 backup/restore after movements/count |
| C — Schema-2 downgrade | PASS | Unchanged a3 storage code with verified SHA-256 restores a4 count increases/decreases/no difference/zero and asset custody; compatibility.json |
| C — Legacy schema-1 | BLOCKED | Earlier source/fixture unavailable; separate filename and version rejection retain earlier data unchanged |
| D — Crash/lock integration | PASS — simulator tested | Abrupt-process uncommitted rollback, committed stock/audit retention and integrity; locked copy fails within test budget. Physical power loss BLOCKED |
| D — Performance | PASS on builder | 10000 records/20 searches, median <250 ms and <=250 rows; actual values in performance.json. Target PC repeat BLOCKED |
| D — Worker responsiveness | PASS — simulator tested | 10 ms Tk heartbeat occurs before a simulated 200 ms backup finishes; one worker/own connection, no duplicate, normal close guarded and failure modal released |
| E — Real scanner/target PC | BLOCKED | Physical gun, target Windows 10/11 DPI/offline endurance/reconnect/suspend/resume unavailable; runnable procedure in TESTING.md |
| E — Equipment control | N/A | Scanner input only; no device/motor commands or control authority, watchdogs or output signals |
| F — Native Windows package | Baseline PASS; new commit requires CI | Baseline Windows Server 2025/Python 3.12.10/PyInstaller 6.22.3 built/probed successfully. Local builder cannot execute Windows EXE. Inspect successful private Actions run for exact published a4 commit before using its artifact |
| F — Source identity/archive | Required at delivery | Compare every remote blob to reviewed source; clean-commit ZIP verifier checks all file hashes, safe paths and manifest. Archive results are reported at delivery |
| F — Windows 10/11 clean installation/upgrade/DPI | BLOCKED | CI runner is not a separate user PC without Python, physical scanner or target display. Stable promotion blocked |

**36 core + 26 GUI = 62 tests passed locally.** Actual logs, compatibility result, performance/fault measurements and four rendered screenshots are in docs/evidence. Source identity is the commit containing these files; remote publication compares its complete tree. Each published candidate needs its own successful private CI run. No public/stable release is authorized.

No known critical/high defect remains within the tested scope. Platform security, full accessibility, physical storage behavior and optional build-tool supply-chain auditing are outside the limited gates. Missing HIL/target-install evidence blocks stable promotion. Upgrade/rollback and original-source limitations are in RECOVERY.md.
