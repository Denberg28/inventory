# Inventory Android 0.2.0-rc.5 — signed installation repair

The rc.3/rc.4 APKs were unsigned build artifacts and Android rejected installation.
The phone deliverable is now a signed **Inventory Candidate** APK, package
`ph.dronelab.inventory.candidate`. It coexists with Inventory and Inventory Preview;
keep the old app/data. No silent uninstall, data replacement or signer substitution.

The user authorized establishing the new retained Candidate signing identity on
27 October 2026 (Asia/Manila). A dedicated Candidate key signs the new variant. Its plaintext keystore/password stay
outside checkout, are encrypted to a recovery certificate, and are removed before the
emulator tools run. Only the public recovery certificate is committed. Private signing
recovery must be retained before promotion. Future builds require the same Candidate
key via the documented CI secrets; generating another key is blocked once its expected
certificate is recorded. Keys/passwords/encrypted recovery are never public release assets.

Prepare runs the full regression suite (52 tests for this revision), all three build/lint variants, SDK apksigner v2
verification and a real package-manager install/initial-launch test in an Android 16
emulator. It checks coexistence with rc.2 Preview and same-APK reinstall. It records the
exact APK hash, certificate and source. Promotion downloads that immutable artifact,
checks the passed main build, checksums, expected certificate and unchanged app/test
source, then publishes the same artifact. It never rebuilds with a different key.

The new app starts with independent local records. To copy data, create an encrypted
.dlinv backup in the old app, preserve it, then restore a copy in Candidate. CSV is not
a full recovery backup. Real phone camera, credentials, Keystore, providers, power-loss
and data migration remain NOT TESTED; this is a prerelease, not a stable release.

User-facing releases must contain signed installers. An unsigned artifact may be kept
for developer use but must never be offered as the phone installation download again.
Build commands: Java 17 / Gradle 8.9 / AGP 8.7.3 / SDK 35 / Build Tools 35.0.0;
`./gradlew testDebugUnitTest lintDebug lintRelease lintCandidate assembleDebug assembleRelease assembleCandidate`.
Candidate signing needs INVENTORY_CANDIDATE_KEYSTORE and INVENTORY_CANDIDATE_PASSWORD_FILE
in the build environment (paths only; never put secret contents in command arguments).

## Recovery reliability fix

Includes the verified recovery guard merged in PR #7. A missing primary inventory file
with a surviving local recovery copy now opens recovery choices instead of initializing
empty inventory. Previous-save/pre-restore copies and legacy atomic backups are detected
before key initialization. Package, schema and backup format otherwise remain unchanged.

Private key recovery is retained separately from GitHub. Restore the Candidate PKCS12 key
and password from the private recovery bundle to configure `INVENTORY_CANDIDATE_KEYSTORE_BASE64`
and `INVENTORY_CANDIDATE_STORE_PASSWORD` in repository secrets for later CI builds. Never
create a replacement key to work around missing secrets. The published certificate is
the reference for all future updates.
