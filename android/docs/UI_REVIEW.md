# UI and workflow review — 0.2.0-rc.2

26 October 2026. Baseline: published `android-v0.2.0-rc.1`, repository commit
`933e8ec04a14c707f0f08bfa4d08166bd1ecd0ac`.
Scope: native Android UI, issue/return workflow and data-action discoverability.

| Finding | Implemented improvement | Expected result |
| --- | --- | --- |
| Scan looked like a destination | Items/Unreturned navigation; explicit Scan label action | Scanning selects a record; never issues automatically |
| Outstanding loans difficult to triage | Overdue and Due today filters; item ID and Record return hint | Today is excluded from overdue |
| Stock and condition difficult to filter | Available, Issued, Low stock and On hold filters | Low stock uses material quantity remaining after custody |
| Landscape controls left little list space | Compact top actions and combined search/filter row; reflow on rotation | List retains a usable viewport |
| Long forms hid the main action | Save/Confirm in native dialog action row | Action stays outside scrolling content |
| Asset forms exposed invalid quantities | Fixed quantity one and hidden low-stock field for tools/equipment | Individually labelled assets remain consistent |
| Predictably invalid issue attempts | Disable Issue with an explanation when stock/status prevents it | Return and Edit remain accessible |
| Consumption consequences unclear | Explain permanent quantity reduction; hide due date | No return expected for consumed materials |
| Delete concealed archive behavior | Archive item wording and accurate restore confirmation | Identity/history retained, issued items protected |
| Flat eleven-option data menu | Group CSV reports and Backup & recovery | All baseline data actions remain available |
| Old scroll offsets obscured searches | Reset scroll for search/filter; preserve search on tab reselection | Results start in view |
| Dismissed form references accumulated | Remove dialogs/forms from registries on dismiss | Lock/background closes visible forms |
| List updates repeatedly scanned loan history | Temporary balances/item index per render | Same results with fewer repeated scans |

## Design references

Android accessibility recommends 48 dp touch targets, visible labels, readable contrast,
and scalable text. Normal text should reach 4.5:1 contrast. Platform action placement,
clear wording and text status support keyboard/TalkBack and reduce reliance on color.

- https://developer.android.com/guide/topics/ui/accessibility/views/apps-views
- https://developer.android.com/docs/quality-guidelines/core-app-quality
- https://m3.material.io/components/app-bars/guidelines

References guide this small native Views app; this is not a formal accessibility
certification or a migration to the full Material 3 component library.

Measured palette contrast against white / app background: muted text 4.90 / 4.56,
navy 11.15 / 10.39, main text 14.56 / 13.57, warning text 6.93 / 6.46. These normal
text combinations exceed 4.5:1; this check does not cover every system-rendered state.

## Acceptance and boundaries

Required: `./gradlew testDebugUnitTest assembleDebug lintDebug`. Regression coverage:
non-mutating filters/navigation, due-today versus overdue, loan code search, disabled
unavailable issues, fixed primary actions and dismiss cleanup, plus baseline stock,
custody, import, recovery and cryptography tests.

Review simulated 360 × 720 portrait, 720 × 360 landscape, 130% text and register dialog.
The previews use fictitious records. Physical keyboard, TalkBack, camera permission,
Keystore, device credential, document provider, power-loss and install/upgrade checks
remain required before stable promotion. Source review/simulation cannot establish them.

One phone remains authoritative. No schema/runtime dependency change. Release package identity is unchanged; the debug
candidate is a separate Inventory Preview app with independent data.
Encrypted atomic storage, immutable item identity, archive/history, restore preview and
CSV warnings remain. Independent staff identity, multi-phone synchronization, scheduled
notifications and label printing are outside this update.

Original APK signing material is not in source. Compare certificates before installing
an update. A different signer cannot upgrade an existing installation. Preserve the
working app and verify an external encrypted backup before any planned reinstall.
