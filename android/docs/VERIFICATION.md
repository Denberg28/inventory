# rc.5 final build verification — 27 October 2026 (Asia/Manila)

**PASS — reviewed, build verified and simulator tested.** Source commit:
`466d580a85884fffb8aa2332c3a2fea4faf5352a`.
Main build: https://github.com/Denberg28/inventory/actions/runs/40448909777.

All 52 Android tests passed (zero failures/errors/skipped). Debug, release and Candidate
build/lint passed with zero errors; two retained warnings per variant are OldTargetApi
and PluralsCandidate. APK v2 signature verification, Android 16 (API 36) emulator
installation, initial launch, same-APK reinstall and coexistence with rc.2 Preview passed.
The source kit was compared byte-for-byte with the built Android source; the artifact
archive and every release checksum passed independent verification.

Candidate certificate SHA-256:
`920d8d691dbedc3c2627363b915c78de516486775acc5c6f8b5234ebfa84f5e0`.
APK SHA-256: `03fb8d9a728574142d2944887bc1e571933d3819b9b32e03a4aa3c6c4ec83c7c`.

The actual main-build private key was recovered, validated against this certificate and
retained privately before promotion. No key/password/recovery file is in the public
release or source kit. Promotion pins source, build run, certificate and APK checksum;
it publishes the same tested binary, without rebuilding or changing signing identity.
Future builds must use this retained key and must not bootstrap another Candidate key.

Physical-phone camera, credential/permission lifecycle, Keystore, file providers,
power-loss, accessibility and backup migration remain **NOT TESTED**. This is a test
candidate, not stable. Prior apps/data/releases are preserved. The signed Candidate has
independent records; transfer copies only through verified encrypted .dlinv backups.
GitHub publication is confirmed by the resulting release, not by this source document.

---

# Verification — rc.5 signed installer repair

Required current evidence: SDK apksigner v2 verification, Android 16 package-manager
installation, initial launch, same-APK reinstall and coexistence with the verified rc.2
Preview APK. The exact hash tested on the emulator must be the published signed artifact.
All existing Android regressions and debug/release/candidate build/lint gates also apply.
Private signing recovery must be retained before promotion. The release BUILD-MANIFEST,
SIGNATURE and INSTALL-CHECK assets identify actual results and the built source commit.
Until those gates pass, this is preparation, not an installable published claim.
Physical-phone credentials, camera, Keystore, providers and data migration remain NOT TESTED.

The following sections are historical rc.4/rc.3/rc.2 evidence, not certification of rc.5.

---

# Verification — 0.2.0-rc.4 unsigned rebuild

Current scope is version/build metadata and packaging version validation. The application
Java/resources, UI, schema and runtime dependencies are unchanged from rc.3.
Required checks: testDebugUnitTest, lintDebug, lintRelease, assembleDebug and assembleRelease
with inventoryUnsignedPreview=true, followed by strict unsigned release packaging.

The published release BUILD-MANIFEST.json is authoritative for the rebuilt source commit,
actual test counts, lint findings and asset hashes. SHA256SUMS must match all other assets.
PR checks do not publish; the release workflow rebuilds/verifies the exact main commit.
Physical-device and signed installation checks remain NOT TESTED. Historical evidence
below applies only to the explicitly recorded rc.3 / rc.2 source commits.

---

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
