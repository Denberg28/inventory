#pragma once
#include <LovyanGFX.hpp>

// LCDWIKI E32R40T resistive profile. Confirm rear PCB marking against vendor manual.
// Do not use this profile on a different board just because its module says 32E.
class BoardDisplay : public lgfx::LGFX_Device {
  lgfx::Panel_ST7796 panel;
  lgfx::Bus_SPI bus;
  lgfx::Light_PWM light;
  lgfx::Touch_XPT2046 touch;
public:
  BoardDisplay() {
    auto b = bus.config();
    b.spi_host = HSPI_HOST; b.spi_mode = 0;
    b.freq_write = 27000000; b.freq_read = 16000000;
    b.pin_sclk = 14; b.pin_mosi = 13; b.pin_miso = 12; b.pin_dc = 2;
    b.spi_3wire = false; b.use_lock = true;
    bus.config(b); panel.setBus(&bus);
    auto p = panel.config();
    p.pin_cs = 15; p.pin_rst = -1; p.pin_busy = -1;
    p.panel_width = 320; p.panel_height = 480;
    p.memory_width = 320; p.memory_height = 480;
    p.offset_x = 0; p.offset_y = 0;
    p.invert = false; p.rgb_order = false; p.bus_shared = true;
    panel.config(p);
    auto l = light.config(); l.pin_bl = 27; l.invert = false; l.freq = 44100; l.pwm_channel = 7;
    light.config(l); panel.setLight(&light);
    auto t = touch.config();
    t.x_min = 0; t.x_max = 4095; t.y_min = 0; t.y_max = 4095;
    t.pin_int = 36; t.bus_shared = true; t.offset_rotation = 0;
    t.spi_host = HSPI_HOST; t.freq = 1000000;
    t.pin_sclk = 14; t.pin_mosi = 13; t.pin_miso = 12; t.pin_cs = 33;
    touch.config(t); panel.setTouch(&touch);
    setPanel(&panel);
  }
};
