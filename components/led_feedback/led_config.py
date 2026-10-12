"""
LED Konfiguration v2 — Praxisnahes Feedback + Beleuchtungssystem
=================================================================
11 LEDs, klar aufgeteilt:
  LED 0      = Akku (immer sichtbar)
  LED 5      = Feedback (überlagert Beleuchtung temporär)
  LEDs 9-10  = Sleeptimer (überlagert Beleuchtung bei Timer aktiv)
  LEDs 1-10  = Beleuchtung (Lichttaster-Modi)
"""

# ============================================================
# HARDWARE
# ============================================================
LED_COUNT = 11
CLK_PIN = 7
DATA_PIN = 25
HW_BRIGHTNESS = 0.5        # SK9822 Hardware-Register (fest)

# ============================================================
# LED-ZONEN
# ============================================================
BATTERY_LED = 0
FEEDBACK_LED = 7              # Feedback auf LED-Position 8 (buf[7])
SLEEP_LEDS = [8, 9, 10]       # Sleeptimer auf LED 9/10/11 (buf[8..10]); [0]=erste aus, [-1]=letzte aus
LIGHTING_LEDS = list(range(1, 11))  # 1-10

# ============================================================
# DATEIPFADE
# ============================================================
COMMAND_FILE = "/tmp/led_command.json"
STATUS_FILE = "/tmp/led_status.json"
SETTINGS_FILE = "/home/pi/RPi-Jukebox-RFID/components/led_feedback/led_settings.json"

# ============================================================
# FEEDBACK-DEFINITIONEN (LED 5)
# ============================================================
# type: "flash" = instant an → langsam ausfaden
#       "blink" = N mal kurz blinken
#       "pulse" = dauerhaft pulsieren (bis gestoppt)
#       "stop"  = pulsieren beenden

FEEDBACK_FADE_SECS = 1.5       # Fade-Dauer bei "flash"
FEEDBACK_BLINK_ON = 0.12       # Blink AN-Zeit
FEEDBACK_BLINK_OFF = 0.12      # Blink AUS-Zeit
FEEDBACK_PULSE_SPEED = 0.06    # Puls-Geschwindigkeit

FEEDBACK_EVENTS = {
    # --- Flash + Fade ---
    "card_ok":        {"type": "flash", "color": (0, 255, 0)},
    "button_press":   {"type": "flash", "color": (255, 200, 0)},
    "shutdown":       {"type": "flash", "color": (180, 0, 255)},

    # --- Blink-Muster ---
    "card_unknown":   {"type": "blink", "color": (0, 100, 255), "count": 3},
    "record_saved":   {"type": "blink", "color": (0, 255, 0),   "count": 3},
    "record_error":   {"type": "blink", "color": (255, 0, 0),   "count": 3},
    "unlink_ok":      {"type": "blink", "color": (180, 0, 255), "count": 3},
    "unlink_error":   {"type": "blink", "color": (255, 0, 0),   "count": 3},
    "headphone_in":   {"type": "blink", "color": (255, 200, 0), "count": 2},
    "headphone_out":  {"type": "blink", "color": (255, 200, 0), "count": 1},
    "error":          {"type": "blink", "color": (255, 0, 0),   "count": 3},

    # --- Dauerhaftes Pulsieren ---
    # "persistent": True -> dieser Dauerzustand wird nach einem kurzen Feedback
    # (flash/blink, z.B. Tastendruck oder platzierte Karte) automatisch wiederhergestellt.
    "record_start":   {"type": "pulse", "color": (255, 0, 0), "persistent": True},
    # Aufnahme pausiert: pulsiert rot (REC=beenden) <-> gruen (Play/Pause=fortsetzen).
    "record_pause":   {"type": "pulse", "color": (255, 0, 0), "color2": (0, 255, 0), "persistent": True},
    "volume_min":     {"type": "pulse", "color": (180, 0, 255)},
    "shutdown_warn":  {"type": "pulse", "color": (255, 120, 0)},

    # --- Pulsieren stoppen ---
    "record_stop":    {"type": "stop"},
    "volume_normal":  {"type": "stop"},
    "shutdown_cancel": {"type": "stop"},
}

# --- Playback-Basisfarbe (sehr dunkel auf LED 5 wenn nichts los ist) ---
PLAYBACK_COLORS = {
    "playing": (0, 30, 0),      # Kaum sichtbar grün
    "paused":  (30, 25, 0),     # Kaum sichtbar gelb
    "stopped": (0, 0, 0),       # Aus
}

# ============================================================
# AKKU (LED 0)
# ============================================================
BATTERY = {
    "voltage_full":     4.1,
    "voltage_warn":     3.5,
    "voltage_low":      3.3,
    "voltage_critical": 3.25,
    "brightness":       0.3,
    "critical_speed":   0.06,
}

# ============================================================
# SLEEPTIMER (LEDs 9-10)
# ============================================================
SLEEP_COLOR = (255, 0, 0)
SLEEP_BRIGHTNESS = 0.6

# ============================================================
# BELEUCHTUNGS-EFFEKTE (Registry)
# ============================================================
AVAILABLE_EFFECTS = {
    "off":          "Aus",
    "nightlight":   "Warmes Nachtlicht",
    "solid":        "Einfache Farbe",
    "chase":        "Lauflicht",
    "knightrider":  "Knight Rider",
    "rainbow":      "Regenbogen",
    "twinkle":      "Color Twinkles",
    "firefly":      "Glühwürmchen",
    "aurora":       "Polarlicht",
    "candle":       "Kerzenlicht",
    "vu_meter":     "Lichtorgel (VU)",
}

SPEED_MAP = {"slow": 0.5, "medium": 1.0, "fast": 2.0}

# ============================================================
# STANDARD-EINSTELLUNGEN
# ============================================================
DEFAULT_SETTINGS = {
    "feedback_enabled":       True,
    "feedback_brightness":    70,
    "lighting_enabled":       True,
    "lighting_brightness":    50,
    "playback_status_enabled": False,   # Standardmäßig aus (Nachtbetrieb)
    "battery_brightness":     30,       # Helligkeit der Akku-Anzeige in % (0-100)
    "battery_threshold":      100,      # Akku-Anzeige leuchtet erst UNTER diesem Ladestand in %; 100 = immer
    "slots": [
        {"effect": "nightlight",  "color": "#FFC878", "brightness": 40, "speed": "medium"},
        {"effect": "rainbow",     "color": "#FFFFFF", "brightness": 50, "speed": "medium"},
        {"effect": "knightrider", "color": "#FF0000", "brightness": 50, "speed": "medium"},
        {"effect": "candle",      "color": "#FF6600", "brightness": 40, "speed": "medium"},
        {"effect": "firefly",     "color": "#88FF00", "brightness": 30, "speed": "slow"},
        {"effect": "aurora",      "color": "#00FFAA", "brightness": 40, "speed": "slow"},
    ],
}
