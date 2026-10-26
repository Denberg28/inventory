# GitHub candidate publication — 0.2.0-rc.1

Publication authorized by the user on 26 October 2026. Android source is added under
`android/`; the root workflow runs its build/tests/lint from that directory. Windows
source and data remain separate. The repository stays private.

The GitHub prerelease attaches the exact previously verified APK and standalone source
build kit. Runtime source, resources and Gradle configuration match the delivered
implementation fingerprint in DELIVERY.json. The root README and CI integration do not
change application behavior. The standalone kit's original workflow is retained inside
android/.github for use when the Android directory is extracted as a standalone project.

- APK SHA-256: a9e85306ff38aacf5470a65738d8eaacc389beea215222623bba4d56d367eebd
- Standalone source kit SHA-256: 24062409568d08a5c71762b69c3875e66c97c06eeb79f5bdbe81aea571403560
- Prior candidate verification: 36 automated tests; zero lint errors/warnings.
- Original APK signature: Android Debug candidate signer. Uploading the same APK preserves
  its signing identity for users who installed the candidate. CI-generated APKs use the
  runner's debug signer; they are verification artifacts, not replacements for the release
  asset. Production signing continuity remains a stable-release gate.
- Physical camera, device credential, Keystore and document-provider checks remain pending.

Use encrypted backups before clearing data or uninstalling. No private signing key,
real inventory data, phone credentials or passphrases are committed.
