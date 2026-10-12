"""
LED Animationen v2 — SK9822 Treiber + Effekt-Bibliothek
========================================================
Treiber: GPIO Bit-Banging (kein spidev nötig)
Effekte: Jeder ist eine Klasse mit update(buf, frame).
         buf = {led_index: (r,g,b)} — Effekte schreiben nur ihre LEDs.
"""

import gc
import math
import os
import random
import struct
import subprocess
import threading
import time
from typing import Tuple, List, Dict, Optional

from led_config import HW_BRIGHTNESS


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def scale_color(color: Tuple[int, int, int],
                brightness: float) -> Tuple[int, int, int]:
    b = max(0.0, min(1.0, brightness))
    return (min(255, int(color[0] * b)),
            min(255, int(color[1] * b)),
            min(255, int(color[2] * b)))


def hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip('#')
    if len(h) != 6:
        return (255, 255, 255)
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return (255, 255, 255)


def blend(a: Tuple[int, int, int], b: Tuple[int, int, int],
          t: float) -> Tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def wheel(pos: int) -> Tuple[int, int, int]:
    pos = pos % 256
    if pos < 85:
        return (pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return (255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return (0, pos * 3, 255 - pos * 3)


# ============================================================
# SK9822 TREIBER
# ============================================================

class SK9822Strip:
    def __init__(self, num_leds: int, clk_pin: int = 7, data_pin: int = 25):
        self.num_leds = num_leds
        self.clk_pin = clk_pin
        self.data_pin = data_pin
        self._GPIO = None
        self._ready = False
        self._leds = [(0, 0, 0, 0)] * num_leds

    def open(self):
        try:
            import RPi.GPIO as GPIO
            self._GPIO = GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.clk_pin, GPIO.OUT)
            GPIO.setup(self.data_pin, GPIO.OUT)
            GPIO.output(self.clk_pin, 0)
            GPIO.output(self.data_pin, 0)
            self._ready = True
            self._prev = None  # Letzter Frame für Dirty-Check
            print(f"[LED] GPIO OK (CLK={self.clk_pin} DATA={self.data_pin} N={self.num_leds})")
            return True
        except (ImportError, RuntimeError) as e:
            print(f"[LED] GPIO nicht verfügbar: {e}")
            self._ready = False
            return False

    def close(self):
        if self._ready:
            self.clear()
            self.show(force=True)
            self._ready = False

    def _send_byte(self, byte):
        if not self._ready:
            return
        G = self._GPIO
        c, d = self.clk_pin, self.data_pin
        for i in range(8):
            G.output(d, (byte >> (7 - i)) & 1)
            G.output(c, 1)
            G.output(c, 0)

    def set_pixel(self, idx: int, r: int, g: int, b: int):
        if 0 <= idx < self.num_leds:
            hw = max(8, int(HW_BRIGHTNESS * 31))
            self._leds[idx] = (hw, int(r) & 255, int(g) & 255, int(b) & 255)

    def clear(self):
        self._leds = [(0, 0, 0, 0)] * self.num_leds

    def show(self, force=False):
        if not self._ready:
            return
        # Dirty-Check: Nur senden wenn sich Pixel geändert haben
        current = tuple(self._leds)
        if not force and self._prev == current:
            return
        self._prev = current
        # GC waehrend des Bitbang-Sendens aussetzen: verhindert GC-Pausen mitten im Frame,
        # die das Timing stoeren und ein helles Aufblitzen ausloesen koennen.
        gc_was = gc.isenabled()
        gc.disable()
        try:
            for _ in range(4):
                self._send_byte(0x00)
            for hw, r, g, b in self._leds:
                self._send_byte(0xE0 | hw)
                self._send_byte(b)
                self._send_byte(g)
                self._send_byte(r)
            for _ in range(max(4, (self.num_leds + 15) // 16)):
                self._send_byte(0x00)
        finally:
            if gc_was:
                gc.enable()


# ============================================================
# EFFEKT-BASISKLASSE
# ============================================================

class BaseEffect:
    name = "base"

    def __init__(self, leds: List[int], color: Tuple[int, int, int] = (255, 255, 255),
                 brightness: float = 0.5, speed: float = 1.0):
        self.leds = leds
        self.color = color
        self.brightness = max(0.0, min(1.0, brightness))
        self.speed = max(0.1, min(3.0, speed))

    def update(self, buf: Dict[int, Tuple[int, int, int]], frame: int):
        pass

    def cleanup(self):
        pass


# ============================================================
# EFFEKTE
# ============================================================

class OffEffect(BaseEffect):
    """Alle LEDs aus."""
    name = "off"

    def update(self, buf, frame):
        for i in self.leds:
            buf[i] = (0, 0, 0)


class NightlightEffect(BaseEffect):
    """Warmes Licht mit minimalem natürlichem Flackern. Nutzt gewählte Farbe."""
    name = "nightlight"

    def update(self, buf, frame):
        flicker = 0.97 + 0.03 * math.sin(frame * 0.015 * self.speed)
        c = scale_color(self.color, self.brightness * flicker)
        for i in self.leds:
            buf[i] = c


class SolidEffect(BaseEffect):
    """Statische Farbe."""
    name = "solid"

    def update(self, buf, frame):
        c = scale_color(self.color, self.brightness)
        for i in self.leds:
            buf[i] = c


class ChaseEffect(BaseEffect):
    """Lauflicht mit Schweif."""
    name = "chase"

    def update(self, buf, frame):
        n = len(self.leds)
        if n == 0:
            return
        tail = min(4, n - 1)
        pos = int(frame * 0.15 * self.speed) % n
        for idx, led in enumerate(self.leds):
            dist = (idx - pos) % n
            if dist <= tail:
                bright = self.brightness * (1.0 - dist / (tail + 1))
            else:
                bright = 0.0
            buf[led] = scale_color(self.color, bright)


class KnightRiderEffect(BaseEffect):
    """Scanner pendelt hin und her."""
    name = "knightrider"

    def update(self, buf, frame):
        n = len(self.leds)
        if n < 2:
            return
        cycle = (n - 1) * 2
        raw = int(frame * 0.2 * self.speed) % cycle
        pos = raw if raw < n else cycle - raw
        for idx, led in enumerate(self.leds):
            dist = abs(idx - pos)
            if dist == 0:
                bright = self.brightness
            elif dist <= 2:
                bright = self.brightness * (0.3 / dist)
            else:
                bright = 0.0
            buf[led] = scale_color(self.color, bright)


class RainbowEffect(BaseEffect):
    """Regenbogen-Zyklus."""
    name = "rainbow"

    def update(self, buf, frame):
        n = len(self.leds)
        if n == 0:
            return
        off = int(frame * 0.5 * self.speed) % 256
        for idx, led in enumerate(self.leds):
            hue = (idx * 256 // n + off) % 256
            buf[led] = scale_color(wheel(hue), self.brightness)


class TwinkleEffect(BaseEffect):
    """Zufälliges Funkeln wie WLED Color Twinkles."""
    name = "twinkle"

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._sparkles = {}

    def update(self, buf, frame):
        if random.random() < 0.12 * self.speed:
            led = random.choice(self.leds)
            if led not in self._sparkles:
                self._sparkles[led] = [0.0, 0.06 * self.speed]
        done = []
        for led, st in self._sparkles.items():
            st[0] += st[1]
            if st[0] >= 1.0:
                st[0] = 1.0
                st[1] = -0.025 * self.speed
            elif st[0] <= 0.0:
                done.append(led)
        for led in done:
            del self._sparkles[led]
        for led in self.leds:
            if led in self._sparkles:
                buf[led] = scale_color(self.color, self._sparkles[led][0] * self.brightness)
            else:
                buf[led] = (0, 0, 0)


class FireflyEffect(BaseEffect):
    """Glühwürmchen — einzelne LEDs glühen langsam."""
    name = "firefly"

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._flies = {}
        for _ in range(min(3, len(self.leds))):
            led = random.choice(self.leds)
            self._flies[led] = [random.uniform(0, math.pi * 2), random.uniform(0.3, 1.0)]

    def update(self, buf, frame):
        if random.random() < 0.008 * self.speed and self._flies:
            old = random.choice(list(self._flies.keys()))
            info = self._flies.pop(old)
            self._flies[random.choice(self.leds)] = info
        if len(self._flies) < 2 and random.random() < 0.02:
            self._flies[random.choice(self.leds)] = [
                random.uniform(0, math.pi * 2), random.uniform(0.3, 1.0)]
        for led in self.leds:
            buf[led] = (0, 0, 0)
        fly_c = (180, 255, 0)
        for led, (phase, spd) in self._flies.items():
            if led in self.leds:
                t = frame * 0.02 * self.speed * spd + phase
                glow = max(0.0, math.sin(t)) ** 2
                buf[led] = scale_color(fly_c, glow * self.brightness)


class AuroraEffect(BaseEffect):
    """Polarlicht — langsame Farbwellen."""
    name = "aurora"

    def update(self, buf, frame):
        n = len(self.leds)
        if n == 0:
            return
        t = frame * 0.012 * self.speed
        for idx, led in enumerate(self.leds):
            p = idx / max(1, n - 1)
            w1 = math.sin(p * 3.0 + t) * 0.5 + 0.5
            w2 = math.sin(p * 5.0 - t * 0.7) * 0.5 + 0.5
            w3 = math.sin(p * 2.0 + t * 0.3) * 0.5 + 0.5
            r, g, b = int(60 * w3), int(220 * w1), int(180 * w2)
            buf[led] = scale_color((r, g, b), self.brightness * (0.2 + 0.8 * w1 * w2))


class CandleEffect(BaseEffect):
    """Kerzenlicht — warmes natürliches Flackern."""
    name = "candle"

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._flick = [random.uniform(0.6, 1.0) for _ in self.leds]

    def update(self, buf, frame):
        flame = (255, 120, 20)
        for idx, led in enumerate(self.leds):
            target = random.uniform(0.4, 1.0)
            self._flick[idx] += (target - self._flick[idx]) * 0.25 * self.speed
            buf[led] = scale_color(flame, self.brightness * self._flick[idx])


class AudioLevelEffect(BaseEffect):
    """Basis fuer audio-reaktive Effekte: liest den Lautstaerke-Pegel (RMS) INTERN aus dem
    MPD-FIFO (kein Mikrofon, keine Frequenzanalyse). self.speed wirkt als EMPFINDLICHKEIT
    (langsam=unempfindlich ... schnell=empfindlich)."""
    name = "audio_base"
    FIFO_PATH = "/tmp/mpd_led.fifo"

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._level = 0.0
        self._running = True
        self._fd = None
        threading.Thread(target=self._read, daemon=True).start()
        print(f"[LED] {self.name}: Audio-FIFO aktiv")

    def _read(self):
        while self._running:
            # FIFO (von MPD geschrieben) non-blocking oeffnen -> Stille/Stop blockiert nicht.
            if self._fd is None:
                try:
                    self._fd = os.open(self.FIFO_PATH, os.O_RDONLY | os.O_NONBLOCK)
                except OSError:
                    time.sleep(0.5)
                    continue
            try:
                chunk = os.read(self._fd, 4096)
            except (BlockingIOError, OSError):
                chunk = b""
            if chunk:
                n = len(chunk) // 2
                if n > 0:
                    try:
                        samples = struct.unpack(f"<{n}h", chunk[:n * 2])  # 16-bit mono
                        rms = (sum(s * s for s in samples) / n) ** 0.5
                        # self.speed (0.5/1.0/2.0) = Empfindlichkeit, 7000 = Basis-Normalisierung
                        self._level = min(1.0, rms / 7000.0 * max(0.2, self.speed))
                    except struct.error:
                        pass
            else:
                # keine Daten (Pause/Stop/leer) -> Pegel langsam abklingen lassen
                self._level *= 0.75
                time.sleep(0.03)

    def cleanup(self):
        self._running = False
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        print(f"[LED] {self.name}: gestoppt")


class VUMeterEffect(AudioLevelEffect):
    """Lichtorgel — alle LEDs pulsieren in der gewaehlten Farbe mit der Lautstaerke."""
    name = "vu_meter"

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._smooth = 0.0

    def update(self, buf, frame):
        self._smooth += (self._level - self._smooth) * 0.4
        base = 0.03
        bright = base + (self.brightness - base) * self._smooth
        c = scale_color(self.color, bright)
        for led in self.leds:
            buf[led] = c


class VUMeter2Effect(AudioLevelEffect):
    """Lichtorgel 2 — VU-Balken mit Peak-Hold: die LEDs fuellen sich mit der Lautstaerke,
    Farbverlauf gruen -> gelb -> rot; die Spitze bleibt kurz stehen und faellt langsam."""
    name = "vu_meter2"

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._smooth = 0.0
        self._peak = 0.0

    def update(self, buf, frame):
        self._smooth += (self._level - self._smooth) * 0.5
        n = len(self.leds)
        if n == 0:
            return
        lit = int(self._smooth * n + 0.0001)
        # Peak-Hold: Spitze merken, danach langsam fallen lassen
        if self._smooth >= self._peak:
            self._peak = self._smooth
        else:
            self._peak = max(0.0, self._peak - 0.015)
        peak_idx = min(n - 1, int(self._peak * n))

        for i, led in enumerate(self.leds):
            frac = i / max(1, n - 1)
            # Farbverlauf: gruen (unten) -> gelb (Mitte) -> rot (oben)
            if frac < 0.5:
                col = (int(255 * frac / 0.5), 255, 0)
            else:
                col = (255, int(255 * (1.0 - (frac - 0.5) / 0.5)), 0)
            if i < lit:
                buf[led] = scale_color(col, self.brightness)
            elif i == peak_idx and self._peak > 0.05:
                buf[led] = scale_color(col, self.brightness)   # Peak-Punkt
            else:
                buf[led] = (0, 0, 0)


# ============================================================
# EFFEKT-REGISTRY
# ============================================================

EFFECT_CLASSES = {
    "off":          OffEffect,
    "nightlight":   NightlightEffect,
    "solid":        SolidEffect,
    "chase":        ChaseEffect,
    "knightrider":  KnightRiderEffect,
    "rainbow":      RainbowEffect,
    "twinkle":      TwinkleEffect,
    "firefly":      FireflyEffect,
    "aurora":       AuroraEffect,
    "candle":       CandleEffect,
    "vu_meter":     VUMeterEffect,
    "vu_meter2":    VUMeter2Effect,
}


def create_effect(name: str, leds: List[int], color: Tuple[int, int, int],
                  brightness: float, speed: float) -> Optional[BaseEffect]:
    cls = EFFECT_CLASSES.get(name)
    if cls:
        return cls(leds=leds, color=color, brightness=brightness, speed=speed)
    print(f"[LED] Unbekannter Effekt: {name}")
    return None
