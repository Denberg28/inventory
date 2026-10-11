# Verification and hardware procedure

Run the README commands without Python -O. Core tests use disposable data; GUI tests exercise actual Tk widgets and keyboard Return events, not a physical gun. `scripts/fault_checks.py` kills child processes via abrupt exit and measures locked-database copy failure. `scripts/performance.py` imports 10000 synthetic rows and measures 20 searches. Store logs under docs/evidence; no real inventory or credentials belong in Git.

## Gates

A: syntax/configuration/limited secret/network checks and relevant platform build. B: core and GUI user flows/errors. C: compatibility within schema 2; earlier schema-1 migration is BLOCKED. D: atomic audit/import, crash recovery, output preservation and performance. E: actual scanner/target PC and physical-power tests. F: source identity/hash verification and actual package install/upgrade/rollback. Missing E/native F permits a private test candidate only. Control authority/watchdogs/motor outputs are N/A: the app only receives scanner input and commands no hardware.

## Windows/scanner HIL (required before stable)

Use disposable data first. Record OS version, Python/Tk or EXE build/source commit, display/DPI, scanner model/firmware, keyboard language, USB port/hub, configuration and timestamps. Set scanner to USB HID keyboard, Enter suffix. Internet disconnected.

1. Launch at 100%, 125% and 150% scaling. Check 1120x700 and minimum 880x560, keyboard navigation, dropdown contrast, all action buttons and dialogs. PASS only if no required control is clipped/unreachable.
2. Add equipment/tool/material records, duplicate/leading-zero IDs and barcodes. Scan 100 labels, including at least 20 repeated, 10 unknown and five invalid inputs. Correct selection 100/100, zero automatic movements, no old actions after unknown/invalid input. Scan-to-selection target <500 ms; measure 20 trials on target PC.
3. Perform checkout/return and receive/issue. Confirm valid revision/history counts, custodian/state rules, duplicate confirmation prevention and insufficient-stock rejection. F2 must not steal input from a modal dialog.
4. Unplug scanner during idle and mid-entry; reconnect to same/different port; check focus loss, cancel dialogs and keyboard layout. No unintended movement; truncated input must either select its exact matching ID or be rejected. Scanner emits keyboard text and has no app control authority.
5. Import valid/duplicate/malformed CSV; export and open in target spreadsheet to check leading zeros/Unicode/formula guard. Back up, change data, restore; confirm recovery backup, read-only paths, existing-file replacement prompt and closed handles. Try a damaged/unsupported backup and confirm live data unchanged.
6. Open a second instance: must refuse. Restart 20 times. Run source/bundled self-test. On a spare controlled test machine, interrupt power during a disposable stock transaction, then inspect integrity/state/audit; record storage/hardware behavior. Back up real data before any upgrade; do not power-test real inventory.
7. Run 30-minute offline endurance: 10000 synthetic records, mixed searches/pages/scans/dialogs. Zero unhandled exceptions/data disagreement/unintended movements; median search <250 ms. Measure memory responsiveness and repeat after scanner reconnect/suspend/resume.
8. Windows EXE: install build dependencies in a clean Python 3.12 environment, build from a clean checkout, extract ZIP on a separate PC without Python, launch offline, repeat probe and primary UI flows, upgrade preserving schema-2 data, then rollback using matching source/backup. Record unsigned package handling. No installer or stable release exists until this passes.

Report PASS/FAIL/BLOCKED/NOT TESTED with configuration, expected/actual measurements and logs. Failures block stable release and invalidate affected evidence.
