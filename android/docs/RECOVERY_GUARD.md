# Missing-primary recovery repair

27 October 2026 (Asia/Manila). Baseline: `5068b58ab8be91a54c314665e3ff4f93684a5f62`.

When inventory.enc was missing but previous.enc or before-restore.enc survived,
Storage.load opened a new empty model. The next mutation could overwrite the
previous-save copy. Startup now rejects that state and offers explicit previous-save,
pre-restore or external backup recovery. No recovery is applied without operator review.

The same file-presence check protects encryption-key initialization. Existing committed
primary/recovery files, including legacy AtomicFile .bak files, prevent a replacement key
from being generated when the Android Keystore alias is missing. The external backup
error remains explicit. Schema, package identity, signing and backup format are unchanged.

Acceptance: missing primary plus previous-save/pre-restore copy rejects empty startup,
preserves recovery bytes and allows explicit recovery; a legacy atomic backup loads its
saved state; a genuinely new installation starts empty. These are storage simulations
with an injected test key, not real Keystore/power-loss validation.

Local checks: 36 Windows regression tests and repository source/self-test checks pass.
Android build, lint and regression evidence will be supplied by the PR's CI run.
Do not distribute its ephemeral debug APK as an update or publish another unsigned
phone download. The user authorized a separate retained Candidate signing identity on 27 October 2026.
Signed publication requires the new combined build to pass all release checks and private
signing recovery to be retained. Earlier rc.5 preparation evidence does not cover this
additional fix; the combined build must run the 52-test suite again.
