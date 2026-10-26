# Changes

## 0.2.0-rc.2 — 26 October 2026

- Separate scan action from Items/Unreturned navigation; preserve search on tab reselection.
- Add stock/condition and due-date filters, clearer loan cards and return affordance.
- Compact landscape actions and reflow on rotation to preserve inventory list space.
- Keep primary form actions visible and improve labels/individual-asset quantity controls.
- Explain unavailable issues and consumption; prevent past due-date selection.
- Rename deletion to Archive, correct restore wording and group data/backup actions.
- Clean up dismissed dialog references and reduce repeated custody scans during rendering.
- Add behavior regressions and portrait/landscape/large-text/form simulated previews.
- Preserve schema and release package ID; debug Preview installs separately for testing.
- Physical-device and signing/upgrade gates remain.

## 0.2.0-rc.1 — 26 October 2026

- Native offline Android app with Items, Scan and Unreturned navigation.
- Phone-camera barcode/QR scan, manual entry, unique codes/IDs, item detail/edit/history.
- Issue tools/equipment and borrowed materials with borrower/due date, partial/full return,
  overdue visibility, consumed material workflow and damaged-return hold.
- Archive/restore deletion preserves identities and history; custody prevents deletion.
- Validated CSV add-only import preview and inventory/issue/history exports.
- Android Keystore AES-GCM local storage, device credential gate, screenshot/backup
  exclusions, password-encrypted complete backups and explicit restore/recovery previews.
- Atomic saves, previous-save recovery, pre-restore recovery, tests and CI build workflow.
- Android is a separate data/application baseline; no automatic Windows migration.
