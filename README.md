# Drone Laboratory Inventory

**0.1.0a3 — rebuilt private source test candidate.** Simple offline Windows inventory for equipment, tools and materials. Author: MD. No account, server, internet or runtime pip packages required.

The original 0.1.0a1/0.1.0a2 source archives became inaccessible after workspace maintenance. This independently tested reconstruction was explicitly authorized on 11 October 2026. Earlier 59-test results do **not** certify this version. See [recovery and compatibility](docs/RECOVERY.md).

## Run on Windows 10/11 x64

Install Python **3.12 x64** from python.org, including Tcl/Tk. Extract/download the complete repository, then double-click `Start-Inventory.cmd`, or run:

```powershell
py -3.12 run_inventory.py
```

Data is saved outside the program folder at `%LOCALAPPDATA%\DroneLabInventory\inventory-v2.sqlite3`. The reconstructed schema uses a separate database filename; earlier databases are retained and never silently migrated. This is a source candidate, requiring Python. An unsigned standalone EXE build is configured in private CI; its actual result must be checked separately.

## Daily workflow

1. **Add item:** equipment/tools are one asset per record; materials have whole-unit stock and a low-stock threshold. Give each record a unique ID and barcode. Blank barcode uses the ID.
2. **Scan:** configure the gun as USB HID keyboard input with an Enter suffix. Press **F2**, scan the label, then choose an action. Scanning itself never changes stock. Unknown/invalid scans disable old selections.
3. **Record movement:** equipment/tools use Check out / Return; materials use Receive / Issue. Enter a person/custodian and confirm. Status, quantity and history save together. Duplicate/stale saves are rejected.
4. **Monitor:** use Search, category/status filters and Low stock. Clear returns to all items. Pages hold 250 rows. History displays the latest 500 events; the full ledger remains in the database.
5. **Protect data:** Data → Backup makes an integrity-checked SQLite snapshot. Restore validates the complete ledger and saves a pre-restore recovery copy before replacing records.

Use Data → CSV template to add bulk records (maximum 10000 rows / 20 MB). Import adds records atomically; it never updates existing IDs. Export report is a human-readable CSV with formula guards and custody details; it is deliberately distinct from the import template. Retire items instead of deleting history.

## Validate and build

```powershell
python -m unittest discover -s tests -v
python -m unittest discover -s tests_gui -v
python scripts/check_source.py
python scripts/fault_checks.py
python scripts/performance.py
python run_inventory.py --self-test
```

GUI tests require an actual display. Linux CI uses Xvfb; this is keyboard simulation, not scanner HIL. Source runtime uses only the Python standard library. Optional build tooling is pinned in `requirements-build.txt`:

```powershell
python -m pip install -r requirements-build.txt
./scripts/build_windows.ps1
```

Build from a clean Git checkout on Windows with Python 3.12. ZIP output contains the complete bundled application, source identity, checksums, docs and upgrade/rollback instructions. Keep `_internal` next to the EXE. There is no auto-update/download feature or public release job.

## Limits

Single workstation; whole quantities; no cloud sync, authentication, reservations, repair scheduling or automatic hardware control. Printed/manufacturer barcodes can be entered; label generation is outside this MVP. Multi-user direct database access is unsupported. Native Windows install/DPI, real scanner, target-PC endurance, physical power loss and schema-1 migration remain **BLOCKED** until validated using [TESTING.md](docs/TESTING.md). No stable readiness is claimed.
