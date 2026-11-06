# Diversify Inventory Bluetooth station

Android 0.3.0-rc.1 + terminal 0.1.0-rc.1; wire protocol 1. Extends the existing
Android app at baseline 368e81f. Existing Windows source and Android schema 1 stay intact.

## Workflow

1. Install the matching signed Inventory Candidate update; export an encrypted backup first.
2. Flash the terminal; complete touch calibration. Pair `Diversify-Inventory` in Android
   Bluetooth settings. Compare the numeric code on both displays and press the board's
   BOOT button to approve. Reject mismatched codes; pairing expires after 30 seconds.
3. Unlock Inventory. Open **Data > Borrower / Bluetooth station > Connect Bluetooth terminal**.
   Allow Nearby devices and select the paired board. No Wi-Fi or Internet is used.
4. Scan borrower ID (or type it), choose Issue or Return, scan the registered item label.
   Review quantity/due date or return condition and confirm on the phone.
5. Repeat item scans for the selected borrower. Use Clear borrower for the next person.
   Borrower IDs are exact, single-line values, maximum 120 characters. No student-name
   directory is implied: the ID is the borrower identifier in the existing custody records.
6. Daily summary shows borrowed units issued/returned today and all currently outstanding/
   overdue units. Days use the phone's timezone (set Asia/Manila for Philippine operations).
   Consumed materials remain in audit history and are excluded from borrowed-unit counts.

Scan selection never changes stock. Terminal buttons only request phone navigation.
Unknown labels must be registered in Items. Returns match borrower ID and item; multiple
open issues require selecting the intended loan. Partial returns and damaged conditions
use the existing atomic encrypted save path. Manual phone operation works without a terminal.

## Transport and recovery

Bluetooth Classic SPP/RFCOMM, service UUID `00001101-0000-1000-8000-00805f9b34fb`.
Newline-delimited UTF-8 JSON, maximum 2048 bytes excluding newline. One paired peer.
Phone sends `hello` with `v:1` and a new UUID `session`; terminal replies `ready` with
matching version/session. Subsequent `state` and `ping` frames carry that session;
terminal acknowledges both with `ready`. Only `request` with monotonic `seq` and action
`borrower`, `issue`, `return`, or `summary` is accepted. Unknown/stale/repeated messages
never grant mutation authority. New connections require explicit selection; no queued
stock changes or automatic transaction replay. Outbound state is a single replaceable
slot, sent every 250ms at most; phone recomputes its display snapshot every 2 seconds.
Requests are rate-limited to 2/second and discarded after 2 seconds in the main queue.

App background/scanner/lock sends an inactive state; board clears the private summary.
Board independently hides stale state after 6 seconds. Phone closes an unresponsive link
at 15 seconds; initial connection/handshake timeout is 12 seconds. A connected socket
alone does not mean protocol-ready. No stored inventory, borrower journal, or autonomous
checkout exists on this terminal. Only touch calibration is stored in ESP32 NVS. Phone
storage/backup remains the authority; microSD transaction sync is not implemented.

## Board profile and build

`firmware/InventoryTerminal/BoardDisplay.h` uses the **LCDWIKI E32R40T resistive** reference:
ST7796, LCD CS15/DC2/SCK14/MOSI13/MISO12, backlight27; XPT2046 CS33/IRQ36 on shared
HSPI, LCD reset tied to EN. The user's LAFVIN board is reported as 4-inch WROOM-32E,
ST7796S/XPT2046. Its PCB revision/profile match is **NOT hardware verified**. Compare
its rear PCB marking and supplier pinout before flashing; adapt this one profile if different.
Source: https://www.lcdwiki.com/res/E32R40T/4.0inch_E32R40T_E32N40T_Arduino_Demo_Instructions.pdf

PlatformIO: `python -m pip install platformio==6.1.19`, then `pio run -d firmware`.
Target pins/toolchains are fixed by `firmware/platformio.ini`. Arduino core 2.0.17;
LovyanGFX 1.2.7; ArduinoJson 6.21.5. Arduino IDE: install ESP32 core 2.0.17 and the
same libraries; open InventoryTerminal.ino, select ESP32 Dev Module, 4MB flash,
Huge APP partition, PSRAM disabled, 240MHz, upload at 115200. No library-global edits.
Hold BOOT 5 seconds after startup to erase calibration and recalibrate on restart.
Do not hold BOOT during power-on unless entering the ESP32 bootloader intentionally.

## Acceptance and hardware checks

Automated: Android tests/build/lint; firmware compile; unit tests reject stale sessions,
duplicates and mutation commands; summary test crosses midnight UTC/Manila; UI simulation
checks borrower prefill, wrong-borrower rejection, confirmation guard, and lock clearing.

Required real hardware procedure (BLOCKED until board + phone available):

- Record PCB marking, phone Android version, both software versions and power supply.
- Calibrate all corners; verify 480x320 layout and all four buttons without swapped axes.
- Pair with matching code; reject wrong code and test 30s timeout; verify bonded reconnect.
- Borrower A: issue 1 asset and 5 material units, return 2; expect 1 asset + 3 material units open.
- Borrower B cannot return A's selected loan. Cancel confirmation; counts must not change.
- Disconnect during scanning and saving. Reconnect; phone saved state is authoritative.
- Stop/background/lock app; board must clear immediately on received inactive state and
  within 6s if that frame is lost. Terminal buttons must never bypass phone unlock/confirmation.
- Repeat 50 connect/disconnect cycles and run 2 hours; no duplicate custody, stalled touch,
  unbounded memory growth, or automatic issue/return on reconnect. Measure rather than infer.
- Test at local midnight, denied Nearby devices/camera permission and empty inventory.

Do not promote stable until touchscreen, SPP pairing, camera, storage and upgrade checks pass.
Rollback: keep the prior APK/firmware; back up inventory before app upgrades. Schema remains
1; do not uninstall/clear app data or substitute a different signing key. No destructive
migration or flash erase is required. Terminal reflashing affects calibration, not phone data.
