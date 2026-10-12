#!/usr/bin/env python3
from __future__ import annotations
"""
Dual RFID Reader – modular, mit wählbarem oberen (SPI) Reader.

  Vorderer Slot : IMMER PN532 (I²C)  → ISO14443A (Karten/Sticker)
  Oberer Slot   : WÄHLBAR (SPI)      → siehe SPI_READER unten

  Alle Reader liefern dieselbe ROHE UID als Hex-String (z.B. "A1A53BB4").
  Dadurch ergibt dieselbe Karte auf JEDEM Reader dieselbe ID – Verknüpfungen
  bleiben beim Reader-Wechsel gültig.

  Treibermodule (gleiche Schnittstelle: .read() -> Hex-UID|None, .name, .cleanup()):
      reader_pn532.py    (PN532, I²C oder SPI)
      reader_mfrc522.py  (MFRC522, SPI)
      reader_pn5180.py   (PN5180, SPI – experimentell, kann auch ISO15693/Tonies)

  Reader wechseln: unten SPI_READER ändern, dann:
      sudo systemctl restart pn532.service
"""

# ════════════════════════════════════════════════════════════════════════
#   HIER DEN VERBAUTEN OBEREN (SPI) READER WÄHLEN:
#       1 = MFRC522
#       2 = PN532       (Standard, zuverlässig für MIFARE)
#       3 = PN5180      (EXPERIMENTELL – ISO15693/Tonies, noch nicht stabil)
SPI_READER = 2
# ════════════════════════════════════════════════════════════════════════

import time
import sys
import signal
import json
import os
import subprocess
import RPi.GPIO as GPIO

from reader_pn532 import PN532Reader

GPIO.setwarnings(False)

print("=== Dual RFID Reader (modular) ===")

def _init_reader(make, tries=3, delay=0.5):
    """Reader-Init mit Wiederholung. Der PN532 (I²C) wirft beim Start gelegentlich
    einen transienten 'Did not receive expected ACK'-Fehler (z.B. direkt nach einem
    Service-Neustart) – ein zweiter Versuch genügt dann meist."""
    last = None
    for _ in range(tries):
        try:
            return make()
        except Exception as e:
            last = e
            time.sleep(delay)
    raise last


# --- Front-Reader: immer PN532 (I²C) ---
front = None
try:
    front = _init_reader(lambda: PN532Reader(bus="i2c", address=0x24, name="PN532-I2C"))
    print(f"✓ Front {front.name} bereit – vorderer Slot")
except Exception as e:
    print(f"⚠ Front PN532 (I²C) fehlt: {e}")

# --- Top-Reader: per SPI_READER gewählt (Imports bewusst bedingt, damit ein
#     fehlendes Paket/Treiber nur den jeweils gewählten Reader betrifft) ---
_READER_NAMES = {1: "MFRC522", 2: "PN532", 3: "PN5180 (experimentell)"}


def _make_top():
    if SPI_READER == 1:
        from reader_mfrc522 import MFRC522Reader
        return MFRC522Reader()
    if SPI_READER == 2:
        return PN532Reader(bus="spi", name="PN532-SPI")
    if SPI_READER == 3:
        from reader_pn5180 import PN5180Reader
        return PN5180Reader()
    return None


top = None
try:
    top = _init_reader(_make_top)
    if top:
        print(f"✓ Top {top.name} bereit – oberer Slot")
    else:
        print(f"⚠ Ungültiger SPI_READER={SPI_READER} (erlaubt: 1/2/3)")
except Exception as e:
    print(f"⚠ Top-Reader ({_READER_NAMES.get(SPI_READER, '?')}) fehlt: {e}")
    top = None

if front is None and top is None:
    print("❌ Kein Reader verfügbar!")
    sys.exit(1)

# === SETTINGS / REMOVAL DETECTION ===
LAST_CARD = None
REMOVAL_COUNTER = 0
REMOVAL_THRESHOLD = 4            # 4x None hintereinander = Karte weg (war 5 → schnelleres Stop)
SETTINGS_LAST_CHECK = 0

# Konstante Poll-Pause (Energiesparen). BEWUSST nicht adaptiv: im Normalbetrieb
# liegt meistens eine Karte – genau dann soll NICHT schneller gepollt werden, sonst
# steigt die CPU-Last im Dauerbetrieb. Das Stoppen wird stattdessen über die
# kleinere Removal-Schwelle (4 statt 5) beschleunigt, ohne mehr zu pollen.
POLL_INTERVAL = 0.5


def check_removal_setting() -> bool:
    try:
        with open('/home/pi/RPi-Jukebox-RFID/settings/Swipe_or_Place') as f:
            return f.read().strip() == "PLACENOTSWIPE"
    except Exception:
        return True                 # Fallback: Place-Mode


def reload_settings_if_needed():
    global REMOVAL_ENABLED, SETTINGS_LAST_CHECK
    now = time.time()
    if now - SETTINGS_LAST_CHECK > 10:
        old = REMOVAL_ENABLED
        REMOVAL_ENABLED = check_removal_setting()
        SETTINGS_LAST_CHECK = now
        if old != REMOVAL_ENABLED:
            print(f"[SETTINGS] Removal Detection → {'AN (Place)' if REMOVAL_ENABLED else 'AUS (Swipe)'}")


REMOVAL_ENABLED = check_removal_setting()
print(f"=== Removal Detection: {'AN (Place-Mode)' if REMOVAL_ENABLED else 'AUS (Swipe-Mode)'} ===")
print(f"=== Removal Threshold: {REMOVAL_THRESHOLD} None-reads ===")


def is_valid_link(cardid: str) -> bool:
    path = f"/home/pi/RPi-Jukebox-RFID/shared/shortcuts/{cardid}"
    if not os.path.exists(path):
        return False
    try:
        with open(path) as f:
            content = f.read().strip()
        return bool(content) and content != cardid
    except Exception:
        return False


def led_feedback(kind: str):
    try:
        with open("/tmp/led_command.json", "w") as f:
            json.dump({"command": "feedback", "kind": kind}, f)
    except Exception:
        pass


def trigger_card_placed(cardid: str, reader_name: str):
    global LAST_CARD, REMOVAL_COUNTER
    if cardid == LAST_CARD:
        return
    print(f"[PLACED] {reader_name}: {cardid} ({len(cardid) // 2} Byte UID)")
    led_feedback("card_ok" if is_valid_link(cardid) else "card_unknown")
    subprocess.run([
        "/home/pi/RPi-Jukebox-RFID/scripts/rfid_trigger_play.sh",
        f"-i={cardid}",
    ])
    LAST_CARD = cardid
    REMOVAL_COUNTER = 0


def trigger_card_removed():
    global LAST_CARD, REMOVAL_COUNTER
    if not REMOVAL_ENABLED:
        print("[REMOVED] Ignoriert (Swipe-Mode)")
        LAST_CARD = None
        REMOVAL_COUNTER = 0
        return
    print(f"[REMOVED] {REMOVAL_THRESHOLD} None-reads → Stop")
    subprocess.run(["mpc", "stop"])
    LAST_CARD = None
    REMOVAL_COUNTER = 0


# === Sauberes Beenden (FLAG-basiert!) ===
# systemd stoppt mit SIGTERM. Wir brechen NICHT mitten in einer SPI-Transaktion
# ab (das hinterließ den PN5180 in 0xFF), sondern setzen ein Flag und beenden die
# laufende Leserunde sauber, danach cleanup().
_running = True


def _handle_term(signum, frame):
    global _running
    _running = False


signal.signal(signal.SIGTERM, _handle_term)
signal.signal(signal.SIGINT, _handle_term)

# === MAIN LOOP ===
print("=== Warte auf Karten ===")
if front:
    print(f"    {front.name} (vorne) → ISO14443A")
if top:
    print(f"    {top.name} (oben)")

while _running:
    reload_settings_if_needed()

    current_card = None
    current_reader = None

    # 1. Front (PN532 I²C) hat Priorität
    if front:
        uid = front.read()
        if uid:
            current_card, current_reader = uid, front.name

    # 2. Oberer Reader nur prüfen, wenn vorne nichts liegt
    if not current_card and top:
        uid = top.read()
        if uid:
            current_card, current_reader = uid, top.name

    if current_card:
        REMOVAL_COUNTER = 0
        if current_card != LAST_CARD:
            trigger_card_placed(current_card, current_reader)
            time.sleep(2)
    else:
        if LAST_CARD:
            REMOVAL_COUNTER += 1
            if REMOVAL_COUNTER >= REMOVAL_THRESHOLD:
                trigger_card_removed()
                time.sleep(1)

    time.sleep(POLL_INTERVAL)

# === Aufräumen (läuft NACH der aktuellen Leserunde, nicht mittendrin) ===
print("\n=== Gestoppt – räume auf ===")
for r in (top, front):
    if r:
        try:
            r.cleanup()
        except Exception:
            pass
try:
    GPIO.cleanup()
except Exception:
    pass
