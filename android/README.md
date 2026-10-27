# Inventory for Android — 0.2.0-rc.5 Candidate

A minimal, offline inventory app for a drone laboratory. Register inventory with the
phone camera, issue tools/materials, and follow outstanding returns. This is a new native
Android implementation; the Windows app and its database remain separate.

## Current build status

rc.5 repairs the invalid unsigned installer delivery. **Inventory Candidate** is a signed
app with a separate package (`ph.dronelab.inventory.candidate`) so earlier apps and data
stay installed. Release requires signature verification and Android 16 emulator
installation/launch/coexistence checks. The same installer-tested artifact is published.
It has independent records; use a verified encrypted .dlinv backup to copy old records.
See RELEASE.md. Unsigned rc.3/rc.4 APKs are developer artifacts, not phone installers.

## Use

1. Install the signed Candidate APK on Android 8.0 or newer. Configure a device PIN, pattern or
   password first. Unlock Inventory using that screen lock.
2. Tap **Scan label** to read an item barcode/QR value, or **Register item** to type an entry.
   An existing label opens its item. A new label asks before registration. Scanning never
   issues stock or opens URLs. Camera decoding is bundled and works offline.
3. Register each physical tool/equipment as one item with its own label and quantity 1.
   Materials may use a stock quantity and low-stock threshold. IDs/codes remain text,
   including leading zeros. Labels must identify individual assets, not merely a shared
   manufacturer's product code. Print/attach distinct labels externally when needed.
4. Open an item, choose **Issue**, enter borrower name/ID, quantity and due date, and
   confirm. Borrowed materials and tools appear in **Unreturned**, ordered by due date.
   For consumed materials, explicitly check **Consumed material**; no return is expected.
5. Open a loan to record a complete or partial return. Check the borrower, quantity,
   condition and live remaining-balance summary, then tap **Record return**. Cancel
   closes the form without saving. **Change return date** requires a new date and reason;
   review and confirm it. The original date/reason remain in item history, and CSV reports
   show the current due date. Completed loans cannot be rescheduled.
   Damaged/Maintenance returns hold the entire item/material lot until an operator reviews its status. They do not silently
   return damaged stock to service.
6. **Edit** updates details and owned quantity; quantity cannot fall below outstanding
   custody. Category and ID are fixed after registration. Changes are recorded in history.
   **Archive item** archives a fully returned item and retains all history. **Data → Show archived
   items** lets you inspect or restore it. Archived identifiers cannot be reused.

Items offers Available, Issued, Low stock and On hold filters. Unreturned offers
Overdue and Due today filters. Tap a loan to record a return. Scan label works from
either view. Main form actions stay outside scrolling content. CSV reports and
Backup & recovery are grouped under Data. See `docs/UI_REVIEW.md`.

## Data and security

- One phone is the authoritative database. No account, server, internet permission,
  advertisements, analytics, cloud synchronization or multi-device merging.
- Phone screen-lock confirmation on launch, manual Lock, and after 60 seconds in the
  background. Dialogs dismiss on backgrounding so sensitive forms cannot overlay the
  locked view. Unsaved forms may need to be reopened; submitted records remain saved.
- Local state is encrypted with AES-256-GCM and a key held in Android Keystore. Screenshots
  and recent-app previews are blocked. Android cloud backup/device transfer is excluded.
  Protection assumes a trusted, non-compromised phone; it is not a multi-user role system
  or a tamper-evident institutional audit service. Anyone who knows the device credential
  can operate the app. History records actions, not independently verified staff identity.
- Updates use validated copies, write/sync/atomic rename and file verification before
  showing success. A rejected operation leaves committed inventory unchanged.
- **Create encrypted backup** saves all items (including archived), loans and history in
  a `.dlinv` file, protected by a separate passphrase of at least 12 characters using
  PBKDF2-HMAC-SHA256 (210,000 iterations), random salt and AES-GCM authentication.
  Keep this file outside the phone and retain the passphrase; neither is recoverable.
- **Restore encrypted backup** validates the entire file, previews counts, and requires
  explicit replacement confirmation. It replaces the current inventory. The old state
  is kept in **Recover before last restore** on the same phone. Repeated restores replace
  that one recovery point. Recovery copies are not independent backups.
- **Recover previous save** previews the state before the last successful inventory
  mutation. It can recover a damaged primary file if the recovery file and device key
  still work. This deliberately rolls back that last mutation.
- Uninstall, clear app data, loss of the encryption key or loss of the phone requires an
  external encrypted backup. Export one before those actions. Never rely on CSV alone.

## CSV exchange

**Data** exports inventory, all issue/return balances, or the complete audit history.
CSV is unencrypted; issue/history files can contain borrower information. Formula-like
cells are prefixed with an apostrophe to reduce spreadsheet formula execution. Treat
ID and barcode columns as Text when opening/editing in a spreadsheet to preserve zeros.

Import accepts UTF-8 inventory CSV only, with this exact header:

```csv
item_id,barcode,name,category,status,quantity,min_stock,location,notes
```

Example:

```csv
DL-001,0001234567,Precision screwdriver,Tool,Available,1,0,Cabinet A,Registered individually
MAT-001,0002345678,Cable ties,Material,Available,100,10,Cabinet B,
```

- Import previews the count and adds new records only. It does not overwrite existing
  IDs/codes, clear inventory, merge loans or import history. Any invalid/duplicate row
  rejects the entire import. Maximum CSV size is 8 MB.
- Inventory CSV quantity means **total owned**; it does not convey available stock or
  borrower custody. Issue CSV separately reports quantity, returned and outstanding.
- The nine column names match the current Windows Inventory export contract reviewed
  from Denberg28/inventory. Windows `In use` rows are rejected because CSV lacks reliable
  custody/due-date transfer. Return Windows loans before migrating item records. Windows
  SQLite and JSON backups are not accepted. Android and Windows have different field
  validation/limits; automatic two-way synchronization/migration is not implemented.
- Use `.dlinv` backups for complete Android recovery and phone-to-phone replacement.
  There is no XLSX import or automatic spreadsheet formula evaluation.

## Build and verify

Java **JDK 17** (including javac/jlink), Android SDK platform 35, Build Tools 35.0.0,
Gradle 8.9 (wrapper included), Android Gradle Plugin 8.7.3. Set `ANDROID_HOME` or create a
local `local.properties` with `sdk.dir=/your/android-sdk`.

```sh
./gradlew testDebugUnitTest assembleDebug lintDebug
```

On Windows use `gradlew.bat`. Output: `app/build/outputs/apk/debug/app-debug.apk`.
Tests: `app/build/reports/tests/testDebugUnitTest/index.html`. Lint:
`app/build/reports/lint-results-debug.html`.

The phone download is a **signed Inventory Candidate test release**, with a dedicated
retained key and package `ph.dronelab.inventory.candidate`. Build it with
`./gradlew testDebugUnitTest lintDebug lintRelease lintCandidate assembleDebug assembleRelease assembleCandidate`
and the private signing paths documented in RELEASE.md. The `debug` variant is only a
local developer Preview build; CI debug keys do not provide update compatibility.
The production `release` variant remains unsigned. Never distribute either as a Candidate
update. Future Candidate updates must use the recorded certificate and retained key.
Earlier Inventory/Preview apps have independent data; transfer a copy with an encrypted
.dlinv backup, preserve the old installation, and verify records before relying on it.
Never include signing keys/passwords in source control or public release assets.

Runtime dependencies: JourneyApps ZXing Embedded 4.3.0 (camera scanner) and Gson 2.11.0
(typed serialization). Both use Apache License 2.0. AndroidX libraries arrive through the
scanner. JUnit/Robolectric are test-only. Dependency versions are fixed in Gradle files;
network is needed to resolve build dependencies, not for app operation.

## Limits

Hard limits: 10,000 items, 50,000 issues, 100,000 audit entries, 16 MB decrypted state;
individual quantities 0–999,999. Lists show 200 records at a time with Show more. Encrypted
whole-state saves favor simplicity and small laboratory inventories; this is not a
high-volume warehouse system. Export before approaching limits. No automatic pruning
or deletion of history occurs. Large-inventory latency is not device-benchmarked.

See `docs/TESTING.md`, `docs/VERIFICATION.md` and `docs/KNOWN_ISSUES.md` for evidence and
candidate gates. Real camera/Keystore/device tests remain necessary before stable use.
