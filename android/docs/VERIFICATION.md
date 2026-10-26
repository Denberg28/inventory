# Verification — 0.2.0-rc.3 development

27 October 2026, Asia/Manila. Tested application source:
`26c615e1277d715fd6034aeb4f034fed1ad9c4ab`.

**PASS:** 48 Android tests, zero failures/errors/skipped; debug and unsigned release
builds; debug/release lint (zero errors, two warnings each). Android CI:
https://github.com/Denberg28/inventory/actions/runs/40386393722.
Windows software, Linux GUI simulation and Windows candidate build also pass:
https://github.com/Denberg28/inventory/actions/runs/40386393806.
Local source checks and 36 Windows core tests pass. Local Android dependency bootstrap
is blocked by restricted network access; it is not the source of Android build evidence.

Lint warnings are retained: `OldTargetApi` for the required pinned target SDK 35, and
heuristic `PluralsCandidate` for a numeric English summary with no inflected noun.
No checks were suppressed. A target-SDK migration needs separate compatibility testing.

Self-review/simulation covers due-date history, invalid/stale/completed-loan rejection,
partial custody, encrypted persistence/recovery, CSV/backup compatibility, live return
summary/cancel, picker cleanup and baseline regressions. The source-kit files were
compared with the local source (apart from a subsequent documentation-only correction).
The downloaded CI archive checksum was verified. Fictitious return/date renders were
visually reviewed at 360 px width. See `evidence/rc3/` and `../DELIVERY.json` for the
exact run, tests, asset hashes, source fingerprint and limits. Later documentation and
evidence commits do not change application/test/build source.

**BLOCKED:** compatible installable APK publication. The rc.2 Preview key is unavailable;
the debug APK uses an ephemeral CI key, and the release variant is unsigned. Neither
is a compatible update. Keep the installed app/data and previous published releases.
No rc.3 GitHub Release or stable readiness is claimed. Physical camera, credentials,
Keystore, providers, accessibility, power loss and installation/upgrade are NOT TESTED.

The following section and older evidence paths document rc.2 only.

---

# Verification — 0.2.0-rc.2

26 October 2026. Tier: controlled Android test candidate. Baseline commit:
`933e8ec04a14c707f0f08bfa4d08166bd1ecd0ac`, published `android-v0.2.0-rc.1`.

Final checks: **PASS**. 41 tests, zero failures/errors/skipped. Debug APK and
unsigned release variant build successfully. Debug and release lint each report zero
errors and warnings. APK metadata and signature verification pass. Runtime permission:
CAMERA only. Final commands: `./gradlew testDebugUnitTest assembleDebug assembleRelease
lintDebug lintRelease`.

Preview package: `ph.dronelab.inventory.preview`; release package remains
`ph.dronelab.inventory`. Version code 2, minimum API 26, target API 35. The Preview app
installs separately; it does not upgrade or modify rc.1 records. Preview changes do not
synchronize back. Physical installation remains NOT TESTED.

APK SHA-256: `a1b2070c75e2f2fe1a6ce6e912f7133338ce827b4261e41a1c3538c836d8b0b2`.

Implementation fingerprint: `3c03569814ff013597030bef6988eb9d1c76763244b25b9359f5414307f9bc41`. Algorithm: ordered main source paths and
contents (NUL-delimited), followed by app/root Gradle configuration.

Full results: `../DELIVERY.json` and `evidence/automated-checks.json`.

Scope: source self-review, Android compilation, unit/domain tests, Robolectric storage
and UI simulation, native-rendered fictitious previews, Android lint and APK metadata /
signature inspection. Simulated layouts: 360 × 720 portrait, 720 × 360 landscape,
130% text and registration dialog. See `UI_REVIEW.md` for findings and design references.

Toolchain: OpenJDK 17, Gradle 8.9, AGP 8.7.3, SDK 35 / Build Tools 35.0.0,
Robolectric 4.14.1 / Android API 28; Linux build host.

The original debug key is absent from source. The local test certificate differs from
rc.1. Preview uses its own package to avoid replacing the working installation.

- rc.1 certificate SHA-256: `a232676e09d307d5905411fe78123673c2b9d349efc50341851667a414fd89b9`.
- rc.2 Preview certificate SHA-256: `df5a504e375d94a473b043c8e903fcee3b3805c9f0cde4c2b5af95c248d67025`.

No signing key is included in source or deliverables. A future in-place release upgrade
still requires signing continuity or a deliberate verified backup migration.

Physical phone camera, credentials, Keystore, file providers, TalkBack, keyboard/large
fonts, power loss/storage full, installation/upgrade and backup migration are NOT TESTED.
These block stable promotion. Robolectric storage tests inject a test key; simulation is
not Android hardware validation. Large-inventory timing is not device-benchmarked.
No remote CI/publication result is claimed for this local revision.

A clean rebuild resolved stale incremental packaging/resource artifacts after the
Preview identity change. The final source was then rebuilt and all tests/lint passed
again after replacing two untranslated dialog labels with the Android system label.
