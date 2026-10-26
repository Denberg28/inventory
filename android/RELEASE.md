# Inventory Android 0.2.0-rc.2 — test build

Prepared from `933e8ec04a14c707f0f08bfa4d08166bd1ecd0ac` (published rc.1 baseline).
UI/workflow development and the next build were requested on 26 October 2026.

Changes: separate scan action, stock/condition and due-date filters, clearer item/loan
cards, persistent form actions, individual-asset quantity controls, clearer consumption
and unavailable-issue behavior, accurate archive/restore labels, grouped data actions,
and dialog cleanup. No runtime dependency or database schema change. The release package ID is preserved;
the debug build uses a separate Preview identity for safe testing.

See `docs/UI_REVIEW.md`, `docs/VERIFICATION.md` and `DELIVERY.json` for final evidence.
The source kit contains fictitious preview data only, never user records or signing keys.
Android and Windows stores remain separate; Windows code/data were not modified.

## Installation and rollback

This is a debug-signed **Inventory Preview** app (`ph.dronelab.inventory.preview`).
It installs beside the published Inventory app (`ph.dronelab.inventory`) with separate
records and encryption keys. Do not uninstall or clear the working app. An encrypted
`.dlinv` backup can copy data into Preview for testing. Preview edits are independent;
there is no synchronization or automatic promotion of its records. CSV is not a complete
custody/history backup. Test data and a disposable backup copy are recommended.

The local debug certificate differs from the published rc.1 certificate; it is not an
in-place upgrade. Production/release identity remains unchanged. A signed upgrade still
requires the original key or a deliberate migration with a verified encrypted backup.

Schema and encrypted-backup format remain version 1. Cross-version recovery has model
format compatibility but physical phone migration is NOT TESTED. Keep the original APK
and external backup for rollback. Production signing continuity and physical-device
checks remain stable-release gates. Public GitHub publication is not claimed by this
local build record.
