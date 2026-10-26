# Verification — 26 October 2026

Tier: **debug-signed Android test candidate**, version 0.2.0-rc.1.

## Passed

- Final build: `testDebugUnitTest assembleDebug lintDebug` — PASS. A clean build also
  completed during verification; a subsequent identifier-validation fix and final manifest
  cleanup were built and tested again.
- **36 tests**, zero failures/errors/skipped — domain, strict backup codec, CSV, crypto,
  storage fault/recovery simulation, phone UI/lifecycle and native-rendered preview checks.
- Android lint: **0 errors, 0 warnings**.
- APK signature verification: PASS, v2 scheme, Android Debug test certificate.
- APK metadata: `ph.dronelab.inventory`, version code 1, min SDK 26, target SDK 35.
- APK manifest permission check: CAMERA only; no INTERNET permission.
- Phone layout reviewed at simulated 360 × 720 dp, Android API 28. Preview images contain
  fictitious sample records and are explicitly labeled simulated.
- Archive checks: source packaging rejects databases, encrypted state/backups, APKs,
  keystores and build caches. APK is delivered separately.

Toolchain: Temurin/OpenJDK JDK 17, Gradle 8.9, AGP 8.7.3, Android SDK platform 35,
Build Tools 35.0.0; Linux build host; Robolectric 4.14.1 (API 28) for Android simulation.

APK: `Inventory-Android-v0.2.0-rc.1-test.apk`

SHA-256: `a9e85306ff38aacf5470a65738d8eaacc389beea215222623bba4d56d367eebd`

Implementation fingerprint (ordered app/src files plus Gradle configuration; each path and
file separated by NUL): `714254d2aefa0887259b382a796c0ed1cf0371cab111172b2c8925b9d3d3bb33`.

## Reviewed scope and compatibility

The Library Windows 0.1.0a2 source was inspected first. The current private
Denberg28/inventory AGENTS.md and store.py were then read; the current repository describes
a rebuilt 0.1.0a3/schema-2 Windows baseline. Current reviewed file SHAs:
AGENTS `a444ef83d18891101072917c799414269d5654ab`,
store `3a5505a3f819e63dd7948cb06e6c88a7740f56a0`.
Android is an independent native implementation, not a claim that the old Windows source
was rebuilt or fully migrated. No Windows source/database was modified, no remote commit
or release was published, and Windows data compatibility is limited to validated new-item
CSV exchange. The Android encrypted-backup format is separate.

## Not tested / stable gates

Physical camera decoding, Android Keystore on real hardware, device credential lifecycle,
real document-provider import/export, actual device power-loss/storage-full behavior,
installation/upgrade across phones, production signing continuity and large-inventory
latency are **NOT TESTED**. Follow `TESTING.md` on a phone before stable promotion.
Robolectric storage tests use an injected test key; they do not validate hardware-backed
Keystore behavior. The CI workflow is included but has not run on GitHub in this task.

## Resolved during verification

Corrected API 26/27 theme/inset compatibility, callback preservation across credential
confirmation, dialog cleanup during locking, invalid-import rollback, strict JSON field
validation and consistent case-insensitive scan/backup identifier uniqueness. A stale
incremental DEX resource collision was cleared by a clean rebuild; final builds pass.

Evidence: `evidence/automated-checks.json`, `lint.txt`, `apk-signature.txt`,
`apk-metadata.txt` and the simulated preview PNGs.
