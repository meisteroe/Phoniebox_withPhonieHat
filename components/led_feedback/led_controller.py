#!/usr/bin/env python3
"""
LED Controller v2 — Zonen-basiertes Rendering
===============================================
Rendering pro Frame:
  1. Beleuchtungseffekt → buf[1..10]
  2. Akku → überschreibt buf[0]
  3. Sleeptimer → überschreibt buf[9,10] wenn aktiv
  4. Feedback → überschreibt buf[5] wenn aktiv
  5. buf → Strip → LEDs

Feedback-Priorität auf LED 5 (hoch → niedrig):
  Pulse (Aufnahme/Lautstärke/Shutdown) > Blink > Flash+Fade > Playback-Status > Beleuchtung
"""

import json
import math
import os
import signal
import sys
import time
from typing import Optional, Dict, Tuple

from led_config import (
    LED_COUNT, CLK_PIN, DATA_PIN,
    BATTERY_LED, FEEDBACK_LED, SLEEP_LEDS, LIGHTING_LEDS,
    COMMAND_FILE, STATUS_FILE, SETTINGS_FILE,
    FEEDBACK_FADE_SECS, FEEDBACK_BLINK_ON, FEEDBACK_BLINK_OFF,
    FEEDBACK_PULSE_SPEED, FEEDBACK_EVENTS, PLAYBACK_COLORS,
    BATTERY, SLEEP_COLOR, SLEEP_BRIGHTNESS, SPEED_MAP,
    DEFAULT_SETTINGS,
)
from led_animations import SK9822Strip, scale_color, hex_to_rgb, create_effect


# ============================================================
# EINSTELLUNGEN
# ============================================================

def load_settings() -> Dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                s = json.load(f)
            for k, v in DEFAULT_SETTINGS.items():
                if k not in s:
                    s[k] = v
            return s
        except (json.JSONDecodeError, IOError):
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings: Dict):
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        tmp = SETTINGS_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(settings, f, indent=2)
        os.replace(tmp, SETTINGS_FILE)
    except IOError as e:
        print(f"[LED] Settings-Fehler: {e}")


# ============================================================
# CONTROLLER
# ============================================================

class LEDController:

    def __init__(self):
        self.strip = SK9822Strip(LED_COUNT, CLK_PIN, DATA_PIN)
        self.settings = load_settings()
        self._running = False
        self._frame = 0

        # --- Beleuchtung ---
        self._lighting_on = False
        self._current_slot = -1     # -1 = aus
        self._current_effect = None

        # --- Feedback-State-Machine ---
        self._fb_mode = "none"      # none / flash / blink / pulse
        self._fb_color = (0, 0, 0)
        self._fb_color2 = None      # zweite Farbe fuer Farbwechsel-Puls (Aufnahme-Pause)
        self._fb_start = 0.0
        self._fb_blink_count = 0
        self._fb_persistent = None  # Dauerzustand (kind), der nach kurzem Feedback wiederkehrt

        # --- Playback-Status ---
        self._playback_state = "stopped"

        # --- Akku ---
        self._batt_voltage = 0.0

        # --- Sleeptimer ---
        self._sleep_active = False
        self._sleep_minutes = 0
        self._sleep_start = 0.0
        self._sleep_remaining = 0.0

        # --- Settings reload ---
        self._settings_mtime = 0

    # ============================================================
    # HAUPTSCHLEIFE
    # ============================================================

    def run(self):
        self.strip.open()
        self._running = True
        save_settings(self.settings)
        print(f"[LED] Controller v2 gestartet ({LED_COUNT} LEDs)")
        self._write_status()

        while self._running:
            t0 = time.monotonic()
            self._check_commands()
            self._check_settings_reload()
            self._update_sleep()
            self._render_frame()

            fps = 20 if self._needs_fast() else 10
            dt = time.monotonic() - t0
            time.sleep(max(0, 1.0 / fps - dt))

    def stop(self):
        self._running = False
        if self._current_effect:
            self._current_effect.cleanup()
        self.strip.clear()
        self.strip.show()
        self.strip.close()
        for f in [COMMAND_FILE, STATUS_FILE]:
            try:
                os.remove(f)
            except FileNotFoundError:
                pass
        print("[LED] Controller gestoppt")

    def _needs_fast(self) -> bool:
        if self._fb_mode != "none":
            return True
        if self._batt_voltage > 0 and self._batt_voltage <= BATTERY["voltage_critical"]:
            return True
        if self._lighting_on and self._current_effect:
            from led_animations import SolidEffect, OffEffect, NightlightEffect
            if not isinstance(self._current_effect, (SolidEffect, OffEffect, NightlightEffect)):
                return True
        return False

    # ============================================================
    # FRAME RENDERING
    # ============================================================

    def _render_frame(self):
        buf = {}

        # 1. Beleuchtung (LEDs 1-10)
        if (self._lighting_on and self._current_effect
                and self.settings.get("lighting_enabled", True)):
            self._current_effect.update(buf, self._frame)

        # 2. Akku (LED 0) — immer
        buf[BATTERY_LED] = self._calc_battery()

        # 3. Sleeptimer (LEDs 9-10)
        if self._sleep_active:
            for sl in SLEEP_LEDS:
                pixel = self._calc_sleep(sl)
                if pixel != (0, 0, 0):
                    buf[sl] = pixel
                # Wenn (0,0,0) → Beleuchtung durchscheinen lassen

        # 4. Feedback (LED 5)
        fb = self._calc_feedback()
        if fb is not None:
            buf[FEEDBACK_LED] = fb
        elif not self._lighting_on or not self.settings.get("lighting_enabled", True):
            # Kein Feedback, keine Beleuchtung → Playback-Status zeigen
            pb = self._calc_playback_base()
            if pb != (0, 0, 0):
                buf[FEEDBACK_LED] = pb

        # 5. An Strip senden
        for i in range(LED_COUNT):
            r, g, b = buf.get(i, (0, 0, 0))
            self.strip.set_pixel(i, r, g, b)
        self.strip.show()
        self._frame += 1

        # Feedback-Timeouts prüfen
        self._check_feedback_done()

    # ============================================================
    # AKKU (LED 0)
    # ============================================================

    def _calc_battery(self) -> Tuple[int, int, int]:
        v = self._batt_voltage
        cfg = BATTERY
        # Helligkeit aus den Einstellungen (WebUI-Schieberegler), 0-100% -> 0.0-1.0
        br = max(0, min(100, self.settings.get("battery_brightness", 30))) / 100.0

        if v <= 0 or br <= 0:
            return (0, 0, 0)

        # Einschalt-Schwelle: Anzeige leuchtet erst UNTER diesem Ladestand (%).
        # Ladestand wie battery_monitor.py: 3.1 V = 0 %, 4.2 V = 100 %.
        threshold = max(0, min(100, self.settings.get("battery_threshold", 100)))
        if threshold < 100:
            percent = max(0, min(100, (v - 3.1) / (4.2 - 3.1) * 100))
            if percent > threshold:
                return (0, 0, 0)

        if v <= cfg["voltage_critical"]:
            # Schnelles Blinken: 0.2s an, 0.2s aus
            blink_on = (self._frame // 15) % 2 == 0
            if blink_on:
                return scale_color((255, 0, 0), br)  # Voll hell
            else:
                return (0, 0, 0)  # Komplett aus
        if v >= cfg["voltage_full"]:
            return scale_color((0, 255, 0), br)
        elif v >= cfg["voltage_warn"]:
            t = (v - cfg["voltage_warn"]) / (cfg["voltage_full"] - cfg["voltage_warn"])
            return scale_color((int(255 * (1 - t)), 255, 0), br)
        elif v >= cfg["voltage_low"]:
            t = (v - cfg["voltage_low"]) / (cfg["voltage_warn"] - cfg["voltage_low"])
            return scale_color((255, int(255 * t), 0), br)
        else:
            return scale_color((255, 0, 0), br)

    # ============================================================
    # FEEDBACK (LED 5)
    # ============================================================

    def trigger_feedback(self, kind: str):
        """Feedback-Event auslösen."""
        if not self.settings.get("feedback_enabled", True):
            # Auch wenn deaktiviert: Pulse (Aufnahme etc.) trotzdem erlauben
            ev = FEEDBACK_EVENTS.get(kind, {})
            if ev.get("type") not in ("pulse", "stop"):
                return

        ev = FEEDBACK_EVENTS.get(kind)
        if not ev:
            print(f"[LED] Unbekanntes Feedback: {kind}")
            return

        fb_bright = self.settings.get("feedback_brightness", 70) / 100.0
        etype = ev["type"]

        if etype == "flash":
            self._fb_mode = "flash"
            self._fb_color = scale_color(ev["color"], fb_bright)
            self._fb_color2 = None
            self._fb_start = time.monotonic()
            print(f"[LED] Feedback: {kind} (flash)")

        elif etype == "blink":
            self._fb_mode = "blink"
            self._fb_color = scale_color(ev["color"], fb_bright)
            self._fb_color2 = None
            self._fb_blink_count = ev.get("count", 3)
            self._fb_start = time.monotonic()
            print(f"[LED] Feedback: {kind} ({self._fb_blink_count}x blink)")

        elif etype == "pulse":
            self._fb_mode = "pulse"
            self._fb_color = scale_color(ev["color"], fb_bright)
            self._fb_color2 = scale_color(ev["color2"], fb_bright) if "color2" in ev else None
            self._fb_start = time.monotonic()
            # Dauerzustand merken, damit er nach kurzen Feedbacks wiederkehrt
            if ev.get("persistent"):
                self._fb_persistent = kind
            print(f"[LED] Feedback: {kind} (pulse)")

        elif etype == "stop":
            self._fb_persistent = None
            if self._fb_mode == "pulse":
                self._fb_mode = "none"
                print(f"[LED] Feedback: Pulse gestoppt ({kind})")

        self._write_status()

    def _calc_feedback(self) -> Optional[Tuple[int, int, int]]:
        """Feedback-Pixel berechnen. None = kein Override."""
        if self._fb_mode == "none":
            return None

        now = time.monotonic()
        elapsed = now - self._fb_start

        if self._fb_mode == "pulse":
            pulse = (math.sin(elapsed * 4.0) + 1) / 2
            if self._fb_color2 is not None:
                # Farbwechsel-Puls (z.B. Aufnahme-Pause: rot <-> gruen)
                c1, c2 = self._fb_color, self._fb_color2
                return (int(c1[0] * (1 - pulse) + c2[0] * pulse),
                        int(c1[1] * (1 - pulse) + c2[1] * pulse),
                        int(c1[2] * (1 - pulse) + c2[2] * pulse))
            # Helligkeits-Puls einer Farbe
            return scale_color(self._fb_color, 0.15 + 0.85 * pulse)

        elif self._fb_mode == "blink":
            period = FEEDBACK_BLINK_ON + FEEDBACK_BLINK_OFF
            total = self._fb_blink_count * period
            if elapsed >= total:
                return None  # Wird in _check_feedback_done aufgeräumt
            phase = elapsed % period
            if phase < FEEDBACK_BLINK_ON:
                return self._fb_color
            else:
                return (0, 0, 0)

        elif self._fb_mode == "flash":
            if elapsed >= FEEDBACK_FADE_SECS:
                return None
            # Quadratisches Ausfaden (schnell hell → langsam dunkel)
            t = 1.0 - (elapsed / FEEDBACK_FADE_SECS)
            t = t * t
            return scale_color(self._fb_color, t)

        return None

    def _check_feedback_done(self):
        """Abgelaufene Feedbacks aufräumen."""
        if self._fb_mode == "none" or self._fb_mode == "pulse":
            return
        elapsed = time.monotonic() - self._fb_start
        done = False
        if self._fb_mode == "flash" and elapsed >= FEEDBACK_FADE_SECS:
            done = True
        elif self._fb_mode == "blink":
            period = FEEDBACK_BLINK_ON + FEEDBACK_BLINK_OFF
            if elapsed >= self._fb_blink_count * period:
                done = True
        if done:
            if self._fb_persistent:
                # Nach einem kurzen Feedback den Dauerzustand wiederherstellen
                # (z.B. Aufnahme laeuft = rot-Puls / Aufnahme pausiert = rot<->gruen).
                self._restore_persistent()
            else:
                self._fb_mode = "none"

    def _restore_persistent(self):
        """Dauerzustand (Aufnahme/Pause) nach einem kurzen Feedback wieder aktivieren."""
        ev = FEEDBACK_EVENTS.get(self._fb_persistent)
        if not ev:
            self._fb_mode = "none"
            self._fb_persistent = None
            return
        fb_bright = self.settings.get("feedback_brightness", 70) / 100.0
        self._fb_mode = "pulse"
        self._fb_color = scale_color(ev["color"], fb_bright)
        self._fb_color2 = scale_color(ev["color2"], fb_bright) if "color2" in ev else None
        self._fb_start = time.monotonic()

    def _calc_playback_base(self) -> Tuple[int, int, int]:
        """Playback-Status als sehr dunkle Farbe auf LED 5."""
        if not self.settings.get("playback_status_enabled", False):
            return (0, 0, 0)
        return PLAYBACK_COLORS.get(self._playback_state, (0, 0, 0))

    # ============================================================
    # SLEEPTIMER (LEDs 9-10)
    # ============================================================

    def start_sleep(self, minutes: int):
        if minutes <= 0:
            self._sleep_active = False
            self._sleep_minutes = 0
            print("[LED] Sleep: AUS")
        else:
            self._sleep_active = True
            self._sleep_minutes = minutes
            self._sleep_start = time.monotonic()
            self._sleep_remaining = float(minutes)
            print(f"[LED] Sleep: {minutes} min")
        self._write_status()

    def _update_sleep(self):
        if not self._sleep_active:
            return
        elapsed = (time.monotonic() - self._sleep_start) / 60.0
        self._sleep_remaining = max(0, self._sleep_minutes - elapsed)
        if self._sleep_remaining <= 0:
            self._sleep_active = False
            self._sleep_minutes = 0
            self._write_status()

    def _calc_sleep(self, led_idx: int) -> Tuple[int, int, int]:
        # Sleeptimer-Anzeige: pro 20 Minuten eine LED.
        #   20 min -> 1 LED (SLEEP_LEDS[-1] = LED 11)
        #   40 min -> 2 LEDs (LED 11 + 10)
        #   60 min -> 3 LEDs (LED 11 + 10 + 9)
        # Mit ablaufender Zeit sinkt die Helligkeit; die LEDs erloeschen von innen
        # (SLEEP_LEDS[0] = LED 9) nach aussen (SLEEP_LEDS[-1] = LED 11) nacheinander.
        if self._sleep_minutes <= 0:
            return (0, 0, 0)
        ratio = self._sleep_remaining / self._sleep_minutes
        units = self._sleep_minutes / 20.0      # 20->1, 40->2, 60->3
        current = units * ratio                 # verbleibende Einheiten

        # Stufe dieser LED: 0 = laengste (LED 11), hoeher = erlischt frueher
        order = list(reversed(SLEEP_LEDS))      # [10, 9, 8] -> buf-Index LED 11, 10, 9
        try:
            stufe = order.index(led_idx)
        except ValueError:
            return (0, 0, 0)

        bright = max(0.0, min(1.0, current - stufe))
        # Frueh schnell verblassen: quadratische Kurve -> die LED wird schon in der
        # ersten Haelfte des 20-Min-Abschnitts deutlich dunkler (statt linear/spaet).
        bright = bright * bright
        if bright <= 0.01:
            return (0, 0, 0)
        return scale_color(SLEEP_COLOR, bright * SLEEP_BRIGHTNESS)

    # ============================================================
    # BELEUCHTUNG
    # ============================================================

    def cycle_light(self):
        """Nächster Modus. Nach letztem Slot → aus → wieder Slot 0."""
        if not self.settings.get("lighting_enabled", True):
            return
        slots = self.settings.get("slots", [])
        if not slots:
            return

        if not self._lighting_on:
            self._current_slot = 0
            self._activate_slot(0)
        else:
            next_slot = self._current_slot + 1
            if next_slot >= len(slots):
                # Nach letztem Slot → aus
                self.light_off()
                return
            self._current_slot = next_slot
            self._activate_slot(next_slot)
        self._write_status()

    def light_off(self):
        if self._current_effect:
            self._current_effect.cleanup()
            self._current_effect = None
        self._lighting_on = False
        self._current_slot = -1
        print("[LED] Beleuchtung: AUS")
        self._write_status()

    def _activate_slot(self, idx: int):
        slots = self.settings.get("slots", [])
        if idx >= len(slots):
            return
        slot = slots[idx]
        name = slot.get("effect", "off")
        color = hex_to_rgb(slot.get("color", "#FFFFFF"))
        br = slot.get("brightness", 50) / 100.0
        max_br = self.settings.get("lighting_brightness", 50) / 100.0
        spd = SPEED_MAP.get(slot.get("speed", "medium"), 1.0)

        if self._current_effect:
            self._current_effect.cleanup()

        if name == "off":
            self._current_effect = None
            self._lighting_on = False
            print(f"[LED] Slot {idx + 1}: Aus")
        else:
            self._current_effect = create_effect(name, LIGHTING_LEDS, color,
                                                  br * max_br, spd)
            self._lighting_on = True
            print(f"[LED] Slot {idx + 1}: {name}")

    # ============================================================
    # BEFEHLE
    # ============================================================

    def _check_commands(self):
        if not os.path.exists(COMMAND_FILE):
            return
        try:
            with open(COMMAND_FILE, "r") as f:
                cmd = json.load(f)
            os.remove(COMMAND_FILE)
        except (json.JSONDecodeError, IOError, FileNotFoundError):
            return
        self._handle_command(cmd)

    def _handle_command(self, cmd: dict):
        action = cmd.get("command", "")

        # --- Feedback ---
        if action == "feedback":
            self.trigger_feedback(cmd.get("kind", "button_press"))

        # --- Playback-Status ---
        elif action == "playback":
            state = cmd.get("state", "stopped")
            if state in PLAYBACK_COLORS:
                self._playback_state = state
                self._write_status()

        # --- Beleuchtung ---
        elif action == "light_cycle":
            self.cycle_light()
        elif action == "light_off":
            self.light_off()
        elif action == "light_slot":
            idx = int(cmd.get("slot", 0))
            self._current_slot = idx
            self._activate_slot(idx)
            self._write_status()

        # --- Sleeptimer ---
        elif action == "sleep":
            self.start_sleep(int(cmd.get("minutes", 0)))

        # --- Akku ---
        elif action == "battery":
            self._batt_voltage = float(cmd.get("voltage", 0))

        # --- Einstellungen ---
        elif action == "set_feedback_brightness":
            val = max(0, min(100, int(cmd.get("value", 70))))
            self.settings["feedback_brightness"] = val
            save_settings(self.settings)
            self._write_status()
        elif action == "set_lighting_brightness":
            val = max(0, min(100, int(cmd.get("value", 50))))
            self.settings["lighting_brightness"] = val
            save_settings(self.settings)
            # Laufenden Effekt live updaten (NICHT neu erstellen → kein Flash)
            if self._lighting_on and self._current_effect and self._current_slot >= 0:
                slots = self.settings.get("slots", [])
                if self._current_slot < len(slots):
                    slot_br = slots[self._current_slot].get("brightness", 50) / 100.0
                    self._current_effect.brightness = slot_br * (val / 100.0)
            self._write_status()
        elif action == "toggle_feedback":
            self.settings["feedback_enabled"] = bool(cmd.get("enabled", True))
            save_settings(self.settings)
            self._write_status()
        elif action == "toggle_lighting":
            self.settings["lighting_enabled"] = bool(cmd.get("enabled", True))
            if not self.settings["lighting_enabled"]:
                self.light_off()
            save_settings(self.settings)
            self._write_status()
        elif action == "toggle_playback_status":
            self.settings["playback_status_enabled"] = bool(cmd.get("enabled", True))
            save_settings(self.settings)
            self._write_status()
        elif action == "set_battery_brightness":
            val = max(0, min(100, int(cmd.get("value", 30))))
            self.settings["battery_brightness"] = val
            save_settings(self.settings)
            self._write_status()
        elif action == "set_battery_threshold":
            val = max(0, min(100, int(cmd.get("value", 100))))
            self.settings["battery_threshold"] = val
            save_settings(self.settings)
            self._write_status()

        # --- Slot speichern ---
        elif action == "save_slot":
            idx = int(cmd.get("index", 0))
            data = cmd.get("data", {})
            slots = self.settings.get("slots", [])
            while len(slots) <= idx:
                slots.append({"effect": "off", "color": "#FFFFFF",
                              "brightness": 50, "speed": "medium"})
            old_slot = dict(slots[idx]) if idx < len(slots) else {}
            slots[idx] = data
            self.settings["slots"] = slots
            save_settings(self.settings)
            if self._lighting_on and self._current_slot == idx:
                # Nur neu erstellen wenn Effekt-Typ gewechselt
                if data.get("effect") != old_slot.get("effect"):
                    self._activate_slot(idx)
                elif self._current_effect:
                    # Parameter live updaten (kein Flash)
                    max_br = self.settings.get("lighting_brightness", 50) / 100.0
                    self._current_effect.color = hex_to_rgb(data.get("color", "#FFFFFF"))
                    self._current_effect.brightness = data.get("brightness", 50) / 100.0 * max_br
                    self._current_effect.speed = max(0.1, min(3.0,
                        SPEED_MAP.get(data.get("speed", "medium"), 1.0)))
            self._write_status()

        # --- Test ---
        elif action == "test_slot":
            idx = int(cmd.get("index", 0))
            self._current_slot = idx
            self._activate_slot(idx)
            self._write_status()

        else:
            print(f"[LED] Unbekannt: {action}")

    # ============================================================
    # SETTINGS HOT-RELOAD
    # ============================================================

    def _check_settings_reload(self):
        try:
            mt = os.path.getmtime(SETTINGS_FILE)
            if mt != self._settings_mtime:
                self._settings_mtime = mt
                self.settings = load_settings()
        except FileNotFoundError:
            pass

    # ============================================================
    # STATUS
    # ============================================================

    def _write_status(self):
        status = {
            "feedback_enabled": self.settings.get("feedback_enabled", True),
            "feedback_brightness": self.settings.get("feedback_brightness", 70),
            "lighting_enabled": self.settings.get("lighting_enabled", True),
            "lighting_brightness": self.settings.get("lighting_brightness", 50),
            "playback_status_enabled": self.settings.get("playback_status_enabled", False),
            "battery_brightness": self.settings.get("battery_brightness", 30),
            "battery_threshold": self.settings.get("battery_threshold", 100),
            "lighting_on": self._lighting_on,
            "current_slot": self._current_slot,
            "playback_state": self._playback_state,
            "fb_mode": self._fb_mode,
            "battery_voltage": round(self._batt_voltage, 2),
            "sleep_active": self._sleep_active,
            "sleep_remaining": round(self._sleep_remaining, 1),
            "slots": self.settings.get("slots", []),
            "timestamp": time.time(),
        }
        try:
            tmp = STATUS_FILE + ".tmp"
            with open(tmp, "w") as f:
                json.dump(status, f)
            os.replace(tmp, STATUS_FILE)
        except IOError:
            pass


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("=== LED v2 Test ===")
        ctrl = LEDController()
        ctrl.strip.open()

        print("→ Akku grün/gelb/rot")
        for v in [4.2, 3.7, 3.3, 3.0]:
            ctrl._batt_voltage = v
            for _ in range(30):
                ctrl._render_frame()
                time.sleep(1/30)

        print("→ Feedback: button_press (gelb flash)")
        ctrl.trigger_feedback("button_press")
        for _ in range(60):
            ctrl._render_frame()
            time.sleep(1/30)

        print("→ Feedback: card_ok (grün flash)")
        ctrl.trigger_feedback("card_ok")
        for _ in range(60):
            ctrl._render_frame()
            time.sleep(1/30)

        print("→ Feedback: card_unknown (3x blau blink)")
        ctrl.trigger_feedback("card_unknown")
        for _ in range(45):
            ctrl._render_frame()
            time.sleep(1/30)

        print("→ Feedback: record_start (rot pulse)")
        ctrl.trigger_feedback("record_start")
        for _ in range(90):
            ctrl._render_frame()
            time.sleep(1/30)
        ctrl.trigger_feedback("record_stop")

        print("→ Nachtlicht")
        ctrl._activate_slot(0)
        for _ in range(90):
            ctrl._render_frame()
            time.sleep(1/30)

        print("→ Cycle")
        ctrl.cycle_light()
        for _ in range(90):
            ctrl._render_frame()
            time.sleep(1/30)

        print("→ Sleep 30min")
        ctrl.start_sleep(30)
        for _ in range(30):
            ctrl._render_frame()
            time.sleep(1/30)

        ctrl.light_off()
        ctrl.strip.clear()
        ctrl.strip.show()
        ctrl.strip.close()
        print("=== Test fertig ===")
        sys.exit(0)

    # Service
    print("[LED] Service v2 startet...")
    ctrl = LEDController()

    def shutdown_handler(sig, frame):
        print(f"\n[LED] Signal {sig} — Shutdown")
        ctrl.trigger_feedback("shutdown")
        for _ in range(50):
            ctrl._render_frame()
            time.sleep(1/30)
        ctrl.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    ctrl.run()
