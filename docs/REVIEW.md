# Feature and compatibility review — 0.1.0a4

11 October 2026, self-review. Repository: private Denberg28/inventory. Preserved baseline: c65ef374badbf9309f6d81bcb4548273a9e8afaa (v0.1.0a3). Its [CI run](https://github.com/Denberg28/inventory/actions/runs/38153365247) passed software, Linux GUI and Windows Server 2025 x64 build/bundled-probe jobs. Review covers every runtime module, launcher, build/verification script, test, workflow and project document. This is engineering review and bounded verification, not formal standards certification.

## Scope and decisions

Keep the offline, single-workstation application: one table, scanner/search fields, filters, six contextual actions, Data menu and short forms. Use Python 3.12/Tk/SQLite without runtime packages. Add stock counting, visible movement outcomes, edit-loss protection, predictable refresh and responsive data operations. No cloud, accounts, procurement, financial valuation, reservations, label generator, dashboards or device control. Preserve schema 2, the data filename, package name, immutable identities, ledger and explicit confirmation.

## Complete feature inventory

| Feature / interface | Review result and verification |
| --- | --- |
| Startup, offline data path, single instance | PASS: separate schema-2 path, OS lock, failure cleanup, 20 app cycles and three real main-loop restarts; no network runtime imports |
| Add equipment, tool, material | PASS: validated fields, asset quantity 1, material whole units, default ID, duplicate cross-namespace rejection, multiline notes |
| Edit/status/retire | PASS: immutable ID/category/quantity, custody rules, revisions; now protects unsaved edits and asks before Lost/Retired changes; no ledger deletion |
| Exact barcode/ID selection | PASS: leading zeros, normalization, exact result beyond 250-row pages, 100 simulated Return-key scans; unknown/invalid scans clear old actions; no automatic stock change |
| Scanner hardware and keyboard layout | BLOCKED: real gun, reconnect/suspend/resume and target Windows keyboard-language path need HIL; only USB HID + Enter is supported |
| Asset checkout/return | PASS: borrower required, atomic status/custody/history, invalid transitions rejected; fresh record read before opening a dialog |
| Material receive/issue | PASS: positive whole quantities, underflow/overflow prevention, named person fields and outcome preview; invalid preview disables confirmation |
| Physical stock count | PASS: required counter/reason, increases/decreases/zero/no-difference, revision check and audit rollback; Data menu entry only for available materials |
| Search/category/status/low stock | PASS: literal SQL wildcard search, clearly named filters, retired materials excluded from restock, contextual actions |
| Pages and refresh | PASS: 250-row cap, cancelled search timers for scan/page/refresh, F5 applies pending search and retains filters; failed reads clear actionable selection |
| Keyboard and modal input | PASS: F2 scanner, F5 refresh, Ctrl+F search, Ctrl+N add, Ctrl+S item save, Escape cancel; modal guard prevents shortcuts stealing input; Enter in a movement field never confirms |
| Empty results/long notes/layout | PASS on Linux display: guidance, bounded footer, full notes in forms/history, scrollbars, minimum 880x560 retains table/actions. Windows DPI and screen-reader validation BLOCKED |
| History | PASS: complete stored snapshots, custody/stock/location/notes at event time; latest 500 displayed, complete ledger retained; count corrections are explicitly identified |
| CSV template/import | PASS: UTF-8 BOM, exact headers, adds only, 20 MB/10000-row bounds, duplicate/malformed all-or-nothing rollback, Unicode/CRLF/leading zeros |
| CSV report | PASS: separate report format, custody/revisions/times, formula guards, atomic output replacement. Spreadsheet users must import ID/barcode as Text; CSV does not preserve spreadsheet cell typing |
| Backup | PASS: SQLite online snapshot, integrity check, closed Windows destination handles, bounded copy retry, protected outputs and atomic replacement |
| Restore/recovery | PASS: read-only source, snapshot/integrity/schema/complete ledger validation, dated pre-restore recovery, unsupported/damaged data leaves live data intact |
| Data-operation workflow | PASS: one worker/own SQLite connection, bounded result queue, Tk-thread-only UI, responsive working dialog, overlapping commands/shutdown blocked, start/connection/write failures release modal; committed refresh errors distinguished |
| Data folder/About | Reviewed: Windows Explorer uses the local data folder; fallback displays path. About contains version/author/data location/shortcuts. Native Explorer launch is covered by target-PC procedure |
| Source/standalone launch and packaging | PASS locally for source/probe/static checks; baseline native x64 package passed. New exact-commit Windows build/probe must pass private CI; x86/ARM64 builds are rejected rather than mislabeled |
| Upgrade/downgrade | PASS with synthetic schema-2 fixtures: v0.1.0a3 backup opens/restores in v0.1.0a4; unchanged v0.1.0a3 validator restores v0.1.0a4 count/custody backup. Schema-1 migration BLOCKED |
| Crash/locks/performance | PASS: abrupt-process rollback/committed durability/integrity, bounded busy-copy failure, 10000-record searches <250 ms on builder. Physical power loss and target-PC endurance BLOCKED |

## Conventions adopted

[Microsoft keyboard guidance](https://learn.microsoft.com/en-us/windows/apps/develop/input/keyboard-interactions) informs Ctrl+F/Ctrl+S, common-command shortcuts, cancel and modal focus. Standard Tk controls supply tab traversal and explicit activation; no accessibility certification is implied. [Python 3.12 Tk threading guidance](https://docs.python.org/3.12/library/tkinter.html#threading-model) informs the short event loop and worker boundary. [SQLite online backup guidance](https://www.sqlite.org/backup.html) informs snapshot-based backups rather than copying a live database file. Input validation, parameterized SQL, transactional state/audit, stale-revision rejection, bounded imports and recoverable restore remain the persistence conventions.

Stock count is a correction, not a fabricated physical receipt/consumption: its explicit note records old and counted quantities plus reason/person. To preserve existing schema-2 backup readers, the correction's storage action remains Receive/Issue/Edit according to the signed difference; the new History viewer labels it Stock count. A matching count records an Edit with zero difference so the count is auditable. No new event type or schema migration is introduced.

IDs/barcodes are opaque identifiers, not validated GTIN/GS1 data. Case normalization and 1–64 ASCII-character restrictions remain intentional; composite/Unicode scanner formats are unsupported. Local SQLite data is not encrypted or authenticated by the app and relies on Windows account/filesystem permissions. No external writes or concurrent workstations are supported.

## Sanitization and release limits

Reviewed parameterized queries, external file/CSV boundaries, protected output aliases, formula guards, temporary-file cleanup, read-only restore source, handle lifetime, thread ownership and shutdown. Limited secret scanning now covers runtime, tests, scripts, workflows, docs and evidence. Only synthetic fixtures/screenshots are committed. Checks do not establish comprehensive supply-chain security or platform hardening.

Evidence and gate status are in [VERIFICATION.md](VERIFICATION.md). Required native CI failures block candidate delivery; missing physical scanner/Windows target evidence permits a clearly labeled private test candidate only. No known critical/high defect remains within the tested scope. Stable promotion remains blocked.
