# Inventory Android 0.2.0-rc.4 — unsigned rebuild

Date: 27 October 2026 (Asia/Manila). Baseline: published `android-v0.2.0-rc.3`,
commit `4625a0aabdcc0ce7ee8962d5c3b0314625579092`.

Scope: rebuild the existing app with version name 0.2.0-rc.4 / code 4. Application
behavior, UI, schema 1 and runtime dependencies are unchanged. Packaging derives the
expected version code from Gradle and checks it against the release request and APK
metadata. Preserve all earlier releases; do not overwrite their tags or assets.

## Build and publication

Use Java 17, Gradle 8.9, AGP 8.7.3, SDK 35 / Build Tools 35.0.0, minimum API 26.
From android/ run:

```sh
./gradlew --no-daemon -PinventoryUnsignedPreview=true testDebugUnitTest lintDebug lintRelease assembleDebug assembleRelease
```

GitHub Actions validates tests/lint, APK package/version, ZIP integrity, absence of JAR
and Android signing blocks, source SHA and artifact checksums. PRs verify/package only;
main publishes the exact verified artifacts as a new unsigned GitHub prerelease. It
refuses an existing release or tag. The release BUILD-MANIFEST records the actual commit,
counts, lint findings, package and asset hashes; SHA256SUMS covers every other asset.
Local dependency downloads remain restricted, so remote CI supplies build evidence.

## Installation and signing

**The Preview APK is unsigned and cannot be installed until signed.** Its package stays
`ph.dronelab.inventory.preview`; no replacement signing identity is generated.
An in-place rc.2 Preview update requires the original key with certificate SHA-256:
`df5a504e375d94a473b043c8e903fcee3b3805c9f0cde4c2b5af95c248d67025`.
The key is unavailable here and is excluded from source/assets. A default CI debug APK
uses an ephemeral key and must not replace the working installation.

Preserve the installed rc.2 Preview/rc.1 app, all prior releases and verified external
`.dlinv` backups. Do not uninstall or clear data to work around signing. CSV is not a
full custody/history backup. No downgrade or physical upgrade is claimed as tested.
Physical camera, credential, Keystore, file-provider, power-loss, accessibility and
installation/upgrade checks remain NOT TESTED; this is not a stable release.
