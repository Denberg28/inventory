# 0.2.0-rc.3 — development, 27 October 2026 (Asia/Manila)

- Audited due-date changes for open issues, with mandatory reason, stale-date rejection
  and no change to original issue time, borrower, quantities or return history.
- Return review displays item, borrower, quantity, condition and remaining balance
  before committing; cancel preserves the form.
- Return forms show original issue date and issue notes.
- Date pickers remove dismissed dialog references and open overdue dates at today.
- Source-kit filenames follow the configured app version; CI builds/lints both variants.
- No schema/dependency change. APK publication is blocked by unavailable rc.2 signing
  material; CI debug APKs are temporary test builds, not compatible app updates.

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
