#!/usr/bin/env python3
"""
LED Befehlstool v2 — Aufrufe aus Scripts
==========================================
Verwendung in Bash-Scripts:

  # Feedback-Events
  led feedback card_ok            Karte erkannt (grün flash)
  led feedback button_press       Knopfdruck (gelb flash)
  led feedback shutdown           Shutdown gestartet (lila flash)
  led feedback card_unknown       Karte unbekannt (3x blau)
  led feedback record_saved       Aufnahme gespeichert (3x grün)
  led feedback record_error       Aufnahme-Fehler (3x rot)
  led feedback unlink_ok          Verknüpfung gelöscht (3x lila)
  led feedback unlink_error       Löschen fehlgeschlagen (3x rot)
  led feedback headphone_in       Kopfhörer rein (2x gelb)
  led feedback headphone_out      Kopfhörer raus (1x gelb)
  led feedback error              Allgemeiner Fehler (3x rot)
  led feedback record_start       Aufnahme läuft (rot pulsierend)
  led feedback record_stop        Aufnahme beendet
  led feedback volume_min         Min. Lautstärke (lila pulsierend)
  led feedback volume_normal      Lautstärke normal
  led feedback shutdown_warn      Shutdown in 10s (orange pulsierend)

  # Playback-Status
  led playback playing            Musik spielt
  led playback paused             Pausiert
  led playback stopped            Gestoppt

  # Beleuchtung
  led light_cycle                 Nächster Modus
  led light_off                   Beleuchtung aus

  # Sleeptimer
  led sleep 30                    Timer auf 30 Minuten
  led sleep 0                     Timer aus

  # Akku
  led battery 3.7                 Spannung setzen

  # Status
  led status                      Status anzeigen

Bash-Shortcut (ohne Python):
  echo '{"command":"feedback","kind":"card_ok"}' > /tmp/led_command.json
"""

import json
import os
import sys

COMMAND_FILE = "/tmp/led_command.json"
STATUS_FILE = "/tmp/led_status.json"


def send(cmd):
    try:
        with open(COMMAND_FILE, "w") as f:
            json.dump(cmd, f)
    except IOError as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    action = args[0]

    if action == "status":
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE) as f:
                data = json.load(f)
            alive = (time.time() - data.get("timestamp", 0)) < 10 if "timestamp" in data else False
            data["alive"] = alive
            print(json.dumps(data, indent=2))
        else:
            print("Controller läuft nicht")
        return

    if action == "feedback" and len(args) > 1:
        send({"command": "feedback", "kind": args[1]})
    elif action == "playback" and len(args) > 1:
        send({"command": "playback", "state": args[1]})
    elif action == "light_cycle":
        send({"command": "light_cycle"})
    elif action == "light_off":
        send({"command": "light_off"})
    elif action == "sleep" and len(args) > 1:
        send({"command": "sleep", "minutes": int(args[1])})
    elif action == "battery" and len(args) > 1:
        send({"command": "battery", "voltage": float(args[1])})
    elif action == "test_slot" and len(args) > 1:
        send({"command": "test_slot", "index": int(args[1])})
    else:
        print(f"Unbekannt: {action}")
        print("Nutze ohne Argumente für Hilfe")


if __name__ == "__main__":
    import time
    main()
