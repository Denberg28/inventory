# Known issues and limits

- Original source/fixtures are inaccessible. This reconstruction isolates schema-2 data; automatic migration and legacy backup restore are unsupported and deliberately rejected.
- Native Windows/DPI, EXE/install and scanner/power-loss/endurance HIL have not been verified locally. Stable promotion is blocked.
- One workstation, whole-unit material quantities, no authentication or cloud sync. Store backups separately from the PC.
- History viewer shows latest 500 events; full history stays in SQLite. Long notes are abbreviated in the footer, fully available in Edit/History.
- Large CSV/restore operations run synchronously. Copies have a five-second retry budget checked between pages; schema/ledger validation and filesystem I/O can take longer. Do not close/power off during a save/restore.
- CSV export is a formula-guarded report, not the import template or a full recovery backup.
- UI/scanner keyboard simulation does not prove every scanner/keyboard/Windows combination. Software checks are limited to their documented scope.
