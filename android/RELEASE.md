# Inventory Android 0.2.0-rc.3 — development delivery

Baseline: `b7f758d` (main, published rc.2 Preview plus release policy).
Date: 27 October 2026, Asia/Manila. Schema and encrypted-backup format remain version 1.
No runtime dependency, package identity or Windows source/data change.

Changes: audited return-date changes, original issue context and live return summary before
saving. See `docs/FOLLOW_UP.md` and `docs/TESTING.md`.

## Build and publication

Required checks: `./gradlew --no-daemon testDebugUnitTest lintDebug lintRelease
assembleDebug assembleRelease`. CI also produces the matching source kit.
Local Gradle bootstrap is blocked by restricted network access; GitHub Actions supplies
build/test evidence. Check the exact commit's run before using any result.

APK release is **BLOCKED** until the existing signing material is recovered or the user
explicitly authorizes a deliberate signing/identity migration. No key is in source.
Expected published rc.2 Preview certificate SHA-256:
`df5a504e375d94a473b043c8e903fcee3b3805c9f0cde4c2b5af95c248d67025`.
The release configuration remains unsigned; the CI debug key is ephemeral. Neither
an unsigned APK nor a differently signed CI APK is a compatible installable update.
Do not publish such a binary as an rc.2 upgrade or change package identity implicitly.

## Compatibility and rollback

Preserve the working rc.2 Preview/rc.1 app and verified external `.dlinv` backups.
Do not uninstall or clear data to work around a certificate mismatch. Once signing is
available, verify APK certificate, package, version code, source commit and checksum
before candidate publication and test an in-place upgrade on a disposable phone.

No downgrade installation is promised. Use the preserved APK/data or a verified backup
on a deliberate, compatible installation for rollback. Physical camera, credentials,
Keystore, file providers, power loss, accessibility and installation/upgrade gates remain
NOT TESTED. Stable promotion is blocked. Earlier rc.2 evidence is historical only.
