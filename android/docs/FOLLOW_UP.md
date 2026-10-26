# Loan follow-up — rc.3

27 October 2026 (Asia/Manila). Baseline: `b7f758d`, rc.2 Preview.

Scope: improve day-to-day unreturned-item handling without adding another navigation
destination, runtime dependency or data schema. An operator can correct/extend an open
loan's due date; the history retains the old date and reason. A return has an explicit
live summary to review the borrower, quantity and condition without another modal on
routine returns.

| Acceptance | Check |
| --- | --- |
| Date change preserves borrower, issue timestamp, quantities, notes and stock | Domain and encrypted-storage simulation |
| Old/new dates, loan ID and mandatory reason remain in audit history | Domain; full backup decode and CSV current-date checks |
| Invalid, unchanged, past, stale and completed-loan changes reject without mutation | Domain and storage rollback tests |
| Return summary updates remaining balance and held-condition warning; cancel does not save | Robolectric UI test |
| Excess return fails before confirmation; original form remains | Robolectric UI test |
| Dismissed date picker is removed; chosen date is visible | Robolectric UI test |
| Existing custody/import/crypto/layout behavior remains | Full Android regression and both variant lint/builds |

A reason does not establish an independent staff identity; access still relies on the
phone credential. Dates use the phone's local date. A change may bring an overdue issue
to today or move a future date earlier, but cannot select a past date. The existing
Unreturned filters and all-issues CSV use the resulting current due date. Consumed
materials create no loan and therefore have no return date to edit.

Review evidence: exact-commit GitHub Actions is required. Local Gradle dependency
bootstrap is blocked by the workspace network. Historical rc.2 evidence under
`docs/evidence/` does not verify rc.3. APK publication is blocked until the rc.2 Preview
signer is available; temporary CI debug keys cannot establish upgrade compatibility.

Physical follow-up test: issue eight material units, return three, reschedule with a
reason, restart, verify five outstanding and audit old/new dates; export issue CSV and
encrypted backup. Open return, enter two and inspect the live summary, then Cancel (five still outstanding),
reopen and record two (three outstanding). Reject a fourth-unit return. Restore the backup
on a disposable test installation and verify the due date/history and five outstanding.
No stable claim until applicable physical checks in TESTING.md pass.
