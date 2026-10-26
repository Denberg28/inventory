# Candidate limits

- rc.3 lint reports two low-severity warnings in each variant: the pinned target SDK 35
  is older than current lint metadata, and the live numeric summary triggers the plural
  heuristic. No checks are suppressed; see VERIFICATION.md.

- rc.3 signed APK publication is BLOCKED: rc.2 Preview signing material is not available.
  CI-generated debug keys do not preserve installed-app upgrade compatibility. The
  unsigned build prerelease cannot be installed until signed with the original key. See RELEASE.md.

- rc.2 debug builds install as Inventory Preview, with an independent package/data store.
  The original rc.1 app stays installed. Preview changes do not synchronize back. The
  local test signer differs from rc.1; in-place upgrades require the original signer.

- Physical phone camera, credential/permission lifecycle, Keystore, document-provider,
  power-loss and signing upgrade behavior remain NOT TESTED. Do not label stable.
- One phone; no simultaneous operators, roles, cloud synchronization or offline merge.
- No independent staff identity or institutional tamper-evident audit. Device credential
  authorizes the operator; a privileged/compromised device is outside the protection model.
- CSV is item exchange/reporting, not full recovery. Windows SQLite/JSON, active Windows
  custody and XLSX import are unsupported. Long/unusual Android codes may not satisfy
  Windows token rules if exported back to the Windows application.
- A damaged return holds the whole material lot. Split damaged inventory into separately
  registered lots after reviewing the quantity and documenting the change in notes.
- Forms close when the app is backgrounded. Unsaved input may be lost; saved operations
  are retained. An export interrupted by process death may leave an empty/partial external
  document; retry it. Local inventory is not changed by an export failure.
- Whole-state encrypted saves are intended for a small lab. Hard record/file caps are
  enforced. There is no automatic history pruning, warehouse-scale performance validation,
  printing of labels, borrower/quantity editing or loan deletion, or notification scheduler.
- Debug-signed candidate. Stable signing continuity and distribution are future gates.
