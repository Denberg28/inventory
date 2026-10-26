# Acceptance and verification

Candidate gates: compile/package, core custody rules, data import/recovery/cryptography,
phone-size simulated layouts, and lint. Stable additionally requires the physical-device
checks below. Never treat source review or simulation as hardware validation.

## Automated acceptance

Run `./gradlew testDebugUnitTest assembleDebug assembleRelease lintDebug lintRelease` on the final source.

- Register unique inventory, preserve zeros, reject duplicate/ambiguous IDs/codes.
- Tools/equipment are individual records; material quantities may be borrowed or consumed.
- Borrow, partial/full return, available/outstanding balance, consumed material exclusion.
- Reject excessive/zero issues/returns, missing borrower, past due date, invalid status,
  removal under custody, quantity below custody, or category changes.
- Archive/restore retains IDs, custody and audit history. Damaged returns hold the lot.
- Strict backup schema/types/UTF-8/references/stock invariants; malformed inputs reject.
- CSV quoting/newlines/zeros, header validation, formula escaping and atomic import failure.
- AES-GCM randomized nonce, round-trip, wrong passphrase and tamper rejection.
- Atomic file interrupted write, primary corruption, previous-save recovery, rejected write
  rollback and pre-restore recovery (Robolectric simulation with a test key).
- Phone layout, scanned existing/new label paths, unreturned filtering and dialog cleanup.

## UI revision acceptance

Filters must not alter inventory/custody; today and overdue must not overlap. Search
by code must work in Unreturned. Unavailable Issue must be disabled with an explanation;
return/edit remain accessible. Primary form actions stay outside scrolling content.
Dismissal/lock clears dialog registries. Tab reselection keeps search; switching views
clears view-specific filters. Review portrait, landscape, 130% text and register dialog
renders; physical TalkBack/keyboard remain device checks. See `UI_REVIEW.md`.

## Physical Android checks — NOT TESTED

Record phone model, Android version, APK SHA-256 and observations.

1. Install on Android 8+ and current Android; launch with/without a configured screen lock.
   Expected: no inventory access until phone credential confirmation succeeds. Cancel and
   relaunch. Background for >60 s with an item/form open; expected: credentials required
   and the old dialog is not visible. Manual Lock also hides data.
2. Camera: deny permission, cancel scan, grant permission, scan an EAN/Code128 barcode
   and QR text. Test dim light, autofocus, rotation and leading zeros. Expected: existing
   item selected; unknown label asks to register; no automatic stock/custody changes.
   Manual registration remains usable if camera is unavailable/denied.
3. Register one tool and a 10-unit material. Issue the tool and 6 material units to borrower
   A. Expected: available 0 and 4; both loans in Unreturned with dates. Return 2 then 4
   materials: expected 6 then 10 available. Confirm excess/duplicate returns are rejected.
   Mark 3 units consumed: expected owned/available 7 and no new unreturned loan.
4. Issue a tool; try delete and reduce stock below custody: both reject. Return damaged:
   expected held status; future issue blocked until status is reviewed. Delete/archive,
   view history, restore, and verify identity retained.
5. Export items/issues/history to local Downloads using Android's file picker. Open files
   and compare counts/values. Import a new-item CSV; duplicates/one invalid row must reject
   all rows. Cancel both pickers and repeat. Import .dlinv with wrong password/corrupted
   bytes: no state changes. Restore a valid backup only after reviewing preview counts.
6. Verify real Android Keystore encrypt/decrypt across restart. Kill the process around
   repeated saves (20 cycles); after restart expect either full old or full new state,
   with no mixed loan/stock state. Test storage-full error on a disposable test device.
   Previous-save recovery and pre-restore recovery must work without exposing plaintext.
7. Export encrypted backup, transfer it to a different phone and restore. Compare all
   inventory, archives, loans, outstanding quantities and audit counts. Do not uninstall
   the only working copy until the external backup is verified.
8. Test 360 dp portrait, landscape, large fonts and software keyboard on register/issue/
   return/data dialogs. Buttons must remain reachable by scrolling. Tab/search/scan return
   should preserve relevant context; no content can overlap system bars.
9. Verify install/upgrade signing continuity with a deliberately selected release key.
   Candidate uses debug signing; production signing is not established in this delivery.

The camera, device credential, Keystore and native document-provider checks are required
before promotion to stable. A successful APK build does not prove those paths work on
physical phones. No Windows executable or external barcode gun is required by this APK.

## rc.3 loan follow-up

See `FOLLOW_UP.md` for measurable acceptance and the device procedure. Required automated
coverage includes audited due-date changes, partial-custody preservation, past/unchanged/
stale/completed-loan rejection, encrypted persistence/recovery, CSV/backup compatibility,
return review cancellation and invalid quantity handling. APK distribution additionally
requires the existing rc.2 Preview signer; never promote an ephemeral CI debug APK as
a compatible upgrade. Earlier screenshots and evidence are labeled rc.2 only.
