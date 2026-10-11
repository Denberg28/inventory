# Known issues and limits

- Original source/fixtures are inaccessible. This reconstruction isolates schema-2 data; automatic migration and legacy backup restore are unsupported and deliberately rejected.
- Native Windows Server 2025 x64 CI built and probed v0.1.0a3 successfully. Each newer source needs its own successful private CI run. Windows 10/11 no-Python installation/DPI, physical scanner/power-loss/endurance and suspend/resume checks are still blocked; stable promotion is blocked.
- One workstation, whole-unit material quantities, no authentication or cloud sync. Store backups separately from the PC.
- History viewer shows latest 500 events; full history stays in SQLite. Long notes are abbreviated in the footer, fully available in Edit/History.
- Large data operations run in a worker and show a working dialog. They cannot be cancelled halfway; normal shutdown and overlapping commands are blocked until completion. Copies have a five-second retry budget checked between pages; full ledger validation and filesystem I/O can take longer. Do not power off during writes.
- CSV export is a formula-guarded report, not the import template or a full recovery backup.
- UI/scanner keyboard simulation does not prove every scanner/keyboard/Windows combination. Software checks are limited to their documented scope.

- No screen-reader/accessibility certification, encryption, GTIN/GS1 validation or automatic barcode-label generation is claimed. Barcodes are opaque uppercase ASCII identifiers, with the documented length/character restrictions. Local data relies on Windows account/file permissions; use a trusted workstation.
