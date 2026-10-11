# MVP specification and architecture

Windows 10/11 x64, Python 3.12, Tkinter, SQLite. One local workstation; no network or cloud runtime. Minimal UI: one inventory table, scan field, filters, contextual actions, Data menu and small dialogs. Free runtime dependency cost: zero. Dominant costs are the user's Windows PC, barcode gun and backup medium; a keyboard can enter the same IDs if no gun is available.

## Interfaces and flow

USB HID scanner → keyboard text + Enter → exact ID/barcode lookup → selected record → explicit action dialog → validated SQLite transaction → audit snapshot → refreshed view. F2 only focuses the scanner when no modal dialog owns input. Unknown/invalid scans clear the previous target before any prompt. IDs/barcodes are normalized uppercase ASCII strings, 1–64 characters; numeric leading zeros remain intact. IDs and barcodes share one logical namespace.

Equipment/tools represent individual assets (quantity 1, minimum 0). Available → Check out (person required) → In use → Return → Available. Status edit can mark a checked-out asset Lost/Retired without fabricating a return; audit retains prior custody. Materials use whole-unit Receive/Issue and physical Stock count while Available; no negative or overflowing stock. Retired records retain their history and do not request restock. Stock count requires a counter and reason, sets the counted quantity atomically, and records its difference. Positive/negative/zero corrections use existing Receive/Issue/Edit events with an explicit Stock count note; this preserves older schema-2 readers. IDs/category cannot change and stock cannot be edited around the ledger.

Search covers ID/barcode/name/location/custodian, with literal SQL wildcards. Status/category/low-stock filters and 250-row pagination keep the view bounded. Scans use exact queries independent of substring pages. Search timers are cancelled before page/scan/close operations. Notes are bounded in the table footer, fully editable in a multiline dialog. One Save/Confirm callback can commit only once even if the subsequent read fails.

## Persistence and failure behavior

Schema 2: items are current state; events record action, delta, actor, note, UTC time and full snapshot. Each create/edit/movement/import uses BEGIN IMMEDIATE and commits state/audit together. Revisions reject stale editors. The OS file lock enforces one running workstation app; two-second SQLite busy timeout bounds normal contention. WAL + FULL synchronous durability supports crash recovery subject to storage/power characteristics.

CSV template: exact nine fields `item_id,barcode,name,category,status,quantity,min_stock,location,notes`; adds only, 10000 rows/20 MB, all-or-nothing. Export contains additional custody/revision/time fields and formula guards; report CSV is not the import format. IDs remain strings. Output paths cannot target DB/journals/lock/aliases. Atomic temp-write/replace preserves an existing report or backup on write failure.

Backup uses SQLite online copy, explicit handle close before Windows rename, integrity check, five-second copy retry budget checked between chunks. A completed copy always reports success. Restore copies a read-only source into a temp DB, validates schema/objects/integrity, every record and sequential ledger transition, then saves current data as recovery backup before replacing it. Restore limits: 512 MB, 100000 items, 1000000 events. Import/export/backup/restore run in a single non-daemon worker with its own SQLite connection. A modal working dialog blocks overlapping commands and normal shutdown while Tk continues processing events; a bounded one-result queue returns completion to the Tk thread. The app never sends Tk objects or the primary database connection into the worker. Copy retries remain bounded; filesystem I/O and full ledger validation may take longer. Completion errors are distinguished from a committed operation followed by a failed view refresh. Use backups on a local, reliable disk. No automatic deletion, sync, database tooling integration or schema-1 migration.

## Measurable acceptance criteria

- 100 exact/repeated keyboard scan events select the correct item and never change quantity/history; unknown/invalid scans disable movement actions.
- Valid custody/stock operations create exactly one audit revision; invalid amounts/statuses/person/stale edits and simulated audit failures leave both unchanged.
- CSV duplicate/malformed records roll back the full import; text/Unicode/CRLF and leading zeros persist.
- Valid schema-2 backup restores identical state/history and creates recovery data; corrupt/unsupported/inconsistent backups leave live data unchanged.
- 10000-record median search <250 ms on test machine, <=250 rendered rows; repeat target PC before promotion.
- 20 startup/close cycles and abrupt-process faults preserve committed data and release locks.
- At 880x560 with long notes, table and action buttons remain visible; native Windows 100/125/150% DPI must be checked separately.
- Physical count increases/decreases/zero differences create one audit revision; zero counts are valid, missing counter/reason and stale/audit failures leave data unchanged.
- A simulated 200 ms data operation permits a 10 ms Tk heartbeat before completion, blocks duplicate commands/close and releases the modal after failure.
- F5 applies pending search and preserves filters; shortcuts respect modal input, dirty edits and Lost/Retired changes require explicit decisions.
- Source/package manifests match every file; Windows bundle self-test/install/offline launch and real scanner HIL must pass before stable promotion.

Non-goals: multi-workstation writes, fractional units, financial valuation, serial firmware protocols, cloud storage, AI, barcode rendering, label printers, deleting ledger, authentication and physical equipment control.
