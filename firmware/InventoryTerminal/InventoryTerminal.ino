/* Diversify Inventory terminal 0.1.0-rc.1
 * Arduino ESP32 2.0.17; ESP32-WROOM-32E ONLY (Classic Bluetooth SPP).
 * Phone is the database authority. Terminal holds only a volatile summary.
 * Every issue/return requires phone confirmation. No unattended/offline mutations.
 */
#include <Arduino.h>
#include <BluetoothSerial.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include "BoardDisplay.h"
#if !defined(CONFIG_BT_SPP_ENABLED)
#error This firmware requires ESP32 Classic Bluetooth SPP
#endif

BoardDisplay screen;
BluetoothSerial bt;
Preferences prefs;
String input, session, borrower, day, mode;
int warnings = 0;
uint64_t issued = 0, returned = 0, outstanding = 0, overdue = 0;
uint32_t lastSeen = 0, seq = 0, pairStarted = 0, pressedAt = 0;
bool active = false, overflow = false, dirty = true, touched = false, bootWasDown = false;
portMUX_TYPE pairMux = portMUX_INITIALIZER_UNLOCKED;
volatile bool pairPending = false;
volatile uint32_t pairPin = 0;
constexpr uint16_t BG = 0x0841, CARD = 0x18e4, FG = 0xef7d, ACCENT = 0x4639;

void forgetState() {
  active = false; borrower = ""; day = ""; mode = "";
  warnings = 0; issued = returned = outstanding = overdue = 0; dirty = true;
}

void sendReady() {
  if (!session.length() || !bt.hasClient()) return;
  StaticJsonDocument<192> o;
  o["v"] = 1; o["type"] = "ready"; o["session"] = session;
  serializeJson(o, bt); bt.println();
}

void requestAction(const char* action) {
  if (!active || session.length() == 0 || millis() - lastSeen > 6000) return;
  StaticJsonDocument<256> o;
  o["v"] = 1; o["type"] = "request"; o["session"] = session;
  o["seq"] = ++seq; o["action"] = action;
  serializeJson(o, bt); bt.println();
}

void consumeLine() {
  StaticJsonDocument<2048> o;
  if (deserializeJson(o, input) || o["v"].as<int>() != 1) return;
  const char* type = o["type"] | "";
  const char* incoming = o["session"] | "";
  if (!strcmp(type, "hello")) {
    if (strlen(incoming) != 36) return;
    if (session != incoming) { forgetState(); session = incoming; seq = 0; }
    lastSeen = millis(); sendReady(); return;
  }
  if (session.length() == 0 || session != incoming) return;
  if (!strcmp(type, "ping")) { lastSeen = millis(); sendReady(); return; }
  if (strcmp(type, "state") || !o["active"].is<bool>()) return;
  if (!o["active"].as<bool>()) { forgetState(); lastSeen = millis(); sendReady(); return; }
  const char* b = o["borrower"] | "";
  const char* d = o["day"] | "";
  const char* m = o["mode"] | "";
  if (strlen(b) > 480 || strlen(d) != 10 || (strcmp(m, "issue") && strcmp(m, "return"))) return;
  for (const char* key : {"issued", "returned", "outstanding", "overdue"})
    if (!o[key].is<uint64_t>() || o[key].as<uint64_t>() > 100000000000ULL) return;
  bool changed = warnings != (o["warnings"] | 0) || !active || borrower != b || day != d || mode != m
      || issued != o["issued"].as<uint64_t>() || returned != o["returned"].as<uint64_t>()
      || outstanding != o["outstanding"].as<uint64_t>() || overdue != o["overdue"].as<uint64_t>();
  warnings = o["warnings"] | 0;
  active = true; borrower = b; day = d; mode = m;
  issued = o["issued"]; returned = o["returned"];
  outstanding = o["outstanding"]; overdue = o["overdue"];
  lastSeen = millis(); if (changed) dirty = true; sendReady();
}

void textAt(const String& value, int x, int y, int size = 1, uint16_t color = FG) {
  screen.setTextSize(size); screen.setTextColor(color, BG);
  screen.drawString(value, x, y);
}

void buttonAt(const char* title, int x, int y, uint16_t color = CARD) {
  screen.fillRoundRect(x, y, 222, 48, 8, color);
  screen.setTextColor(FG, color); screen.setTextSize(2);
  screen.drawCentreString(title, x + 111, y + 15);
}

String countText(uint64_t n) {
  char result[24]; snprintf(result, sizeof(result), "%llu", (unsigned long long)n); return String(result);
}

void drawScreen() {
  dirty = false; screen.fillScreen(BG);
  textAt("DIVERSIFY INVENTORY", 16, 10, 2, ACCENT);
  if (pairPending) {
    textAt("Bluetooth pairing", 16, 60, 2);
    char pin[7]; snprintf(pin, sizeof(pin), "%06lu", (unsigned long)pairPin);
    textAt(pin, 16, 100, 4, ACCENT);
    textAt("Compare this code on your phone.", 16, 160, 2);
    textAt("Press BOOT to accept. 30s timeout.", 16, 190, 2);
    buttonAt("Reject", 16, 250); return;
  }
  if (!active) {
    textAt(bt.hasClient() ? "Phone locked / scanner open" : "Bluetooth disconnected", 16, 65, 2);
    textAt("Open Inventory on your paired phone.", 16, 110, 2);
    textAt("Data > Borrower / Bluetooth station", 16, 145, 2);
    textAt("Pair: Diversify-Inventory", 16, 190, 2, ACCENT);
    textAt("No offline issue or return is recorded.", 16, 270, 1);
    return;
  }
  textAt(day + "  /  " + mode, 16, 40, 2);
  String shown = borrower.length() ? borrower : "Scan borrower ID";
  if (shown.length() > 32) shown = shown.substring(0, 29) + "...";
  textAt(shown, 16, 72, 2);
  textAt("ISSUED TODAY", 16, 101); textAt(countText(issued), 16, 116, 2);
  textAt("RETURNED TODAY", 250, 101); textAt(countText(returned), 250, 116, 2);
  textAt("OUTSTANDING", 16, 145); textAt(countText(outstanding), 16, 160, 2);
  textAt("OVERDUE", 250, 145); textAt(countText(overdue), 250, 160, 2, overdue ? 0xfaa0 : FG);
  buttonAt("Borrower ID", 12, 190); buttonAt("Summary", 246, 190);
  buttonAt("Issue item", 12, 250, 0x03b0); buttonAt("Return item", 246, 250, 0x22ac);
  if (warnings) textAt("Review imported audit history on phone", 16, 305, 1, 0xfaa0);
}

void confirmPair(bool accepted) {
  portENTER_CRITICAL(&pairMux);
  bool pending = pairPending; pairPending = false;
  portEXIT_CRITICAL(&pairMux);
  if (pending) bt.confirmReply(accepted);
  dirty = true;
}

void setup() {
  Serial.begin(115200);
  pinMode(0, INPUT_PULLUP);
  pinMode(4, OUTPUT); digitalWrite(4, HIGH); // Disable onboard audio amplifier.
  screen.init(); screen.setRotation(1); screen.setBrightness(180);
  prefs.begin("inv-display", false);
  uint16_t cal[8];
  if (prefs.getBytesLength("touch") == sizeof(cal)) {
    prefs.getBytes("touch", cal, sizeof(cal)); screen.setTouchCalibrate(cal);
  } else {
    screen.fillScreen(BG); screen.setTextColor(FG, BG); screen.setTextSize(2);
    screen.drawString("Touch calibration", 16, 10);
    screen.calibrateTouch(cal, ACCENT, BG, 12);
    prefs.putBytes("touch", cal, sizeof(cal));
  }
  // Calibration is the only data stored by this firmware; no borrower/stock journal.
  bt.enableSSP();
  bt.onConfirmRequest([](uint32_t number) {
    portENTER_CRITICAL(&pairMux);
    pairPin = number; pairPending = true;
    portEXIT_CRITICAL(&pairMux);
  });
  bt.onAuthComplete([](boolean success) { Serial.println(success ? "Pair accepted" : "Pair failed"); });
  if (!bt.begin("Diversify-Inventory")) {
    screen.fillScreen(BG); textAt("Bluetooth startup failed", 16, 70, 2);
    while (true) delay(100);
  }
  input.reserve(2048); drawScreen();
}

void loop() {
  bool pairing = pairPending;
  if (pairing && !pairStarted) { pairStarted = millis(); dirty = true; }
  if (!pairing) pairStarted = 0;
  if (pairing && millis() - pairStarted > 30000) confirmPair(false);
  bool down = digitalRead(0) == LOW;
  if (down && !bootWasDown) {
    if (pairing) confirmPair(true);
    pressedAt = millis();
  }
  if (down && !pairing && millis() - pressedAt > 5000) {
    prefs.remove("touch"); ESP.restart(); // Long BOOT: recalibrate at next startup.
  }
  bootWasDown = down;
  if (!bt.hasClient()) {
    if (session.length()) { session = ""; input = ""; overflow = false; forgetState(); }
  } else {
    for (int budget = 256; budget > 0 && bt.available(); --budget) {
      char c = bt.read();
      if (c == '\n') {
        if (!overflow) consumeLine();
        input = ""; overflow = false;
      } else if (c != '\r' && !overflow) {
        if (input.length() >= 2048) { overflow = true; input = ""; }
        else input += c;
      }
    }
    if (active && millis() - lastSeen > 6000) forgetState();
  }
  uint16_t x = 0, y = 0;
  bool touchDown = screen.getTouch(&x, &y);
  if (touchDown && !touched) {
    if (pairPending) confirmPair(false);
    else if (y >= 190 && y < 238) requestAction(x < 240 ? "borrower" : "summary");
    else if (y >= 250 && y < 298) requestAction(x < 240 ? "issue" : "return");
  }
  touched = touchDown;
  if (dirty) drawScreen();
  delay(5);
}
