# GitHub candidate publication — 0.2.0-rc.1

Publication authorized by the user on 26 October 2026. Android source is added under
`android/`; the root workflow runs its build/tests/lint from that directory. Windows
source and data remain separate. The owner made the repository public and requested retrying publication on 26 October 2026. Earlier GitHub Actions attempts did not start because of the account billing/spending restriction; a new run verifies the candidate after the visibility change.

The GitHub prerelease attaches the exact previously verified APK. The standalone source
build kit includes the corrected SDK setup workflow; application code is unchanged. Runtime source, resources and Gradle configuration match the delivered
implementation fingerprint in DELIVERY.json. The root README and CI integration do not
change application behavior. The standalone kit's original workflow is retained inside
android/.github for use when the Android directory is extracted as a standalone project.

- APK SHA-256: a9e85306ff38aacf5470a65738d8eaacc389beea215222623bba4d56d367eebd
- Standalone source kit SHA-256: 50604b254a4fd5c9fc34e42801a758584635c724516756b71b4dbffeb32dbcf4
- Prior candidate verification: 36 automated tests; zero lint errors/warnings.
- Original APK signature: Android Debug candidate signer. Uploading the same APK preserves
  its signing identity for users who installed the candidate. CI-generated APKs use the
  runner's debug signer; they are verification artifacts, not replacements for the release
  asset. Production signing continuity remains a stable-release gate.
- Physical camera, device credential, Keystore and document-provider checks remain pending.

Use encrypted backups before clearing data or uninstalling. No private signing key,
real inventory data, phone credentials or passphrases are committed.

Publication complete: tag `android-v0.2.0-rc.1`, source commit `26474ebe6f441a6ec307172fcd59c19c8e26cd76`.
Android and Windows push/PR checks passed before merge/publication. Android check:
https://github.com/Denberg28/inventory/actions/runs/40300545751 .
Release: https://github.com/Denberg28/inventory/releases/tag/android-v0.2.0-rc.1 .
The published tag is retained unchanged; this follow-up documentation records final asset hashes.
