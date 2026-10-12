#!/bin/bash
# ---------------------------------------------------------------------------
# custom_mpd_watch.sh
# Ueberwacht den Audio-Ordner REKURSIV und aktualisiert die MPD-Datenbank
# automatisch, sobald neue Dateien hinzukommen (z.B. per Netzwerkfreigabe
# \\phoniebox\... kopiert).
#
# WARUM: MPDs eingebautes auto_update (inotify) verpasst haeufig Bulk-/SMB-
# Kopien -> neue Alben erscheinen dann zwar in der WebUI, sind fuer den Player
# aber "No such directory". Dieser Watcher loest bei JEDER Aenderung ein volles
# "mpc update" aus und ist damit robust gegen verpasste Einzel-Events.
#
# AKKU: rein ereignisbasiert (inotify), KEIN Polling. Der Prozess schlaeft im
# Kernel und wird nur bei echten Datei-Aenderungen geweckt -> im Ruhezustand
# praktisch kein Verbrauch. Nur beim tatsaechlichen Kopieren laeuft einmal
# "mpc update" (wenige Sekunden).
#
# Gestartet/ueberwacht als systemd-Dienst: mpd-autoupdate.service
# ---------------------------------------------------------------------------

AUDIODIR="/home/pi/RPi-Jukebox-RFID/shared/audiofolders"
DEBOUNCE=10                                   # Sek. Ruhe nach letzter Aenderung
EVENTS="create,close_write,moved_to,moved_from,delete"
EXCLUDE='(/Recordings/|/\.)'                  # Aufnahmen + versteckte/temp-Dateien ignorieren

# Ordner muss existieren, sonst beenden (systemd startet neu)
[ -d "$AUDIODIR" ] || { echo "Audio-Ordner fehlt: $AUDIODIR" >&2; exit 1; }

while true; do
    # 1) Blockierend auf die ERSTE Aenderung warten (kein CPU-Verbrauch, kein Polling).
    inotifywait -q -r --exclude "$EXCLUDE" -e "$EVENTS" "$AUDIODIR" >/dev/null 2>&1

    # 2) Debounce: solange weiter warten, wie innerhalb von $DEBOUNCE noch etwas
    #    passiert (ein Album = viele Dateien nacheinander -> nur EIN Update).
    #    inotifywait -t liefert bei Timeout != 0 -> Schleife bricht bei Ruhe ab.
    while inotifywait -q -q -r --exclude "$EXCLUDE" -t "$DEBOUNCE" -e "$EVENTS" "$AUDIODIR" >/dev/null 2>&1; do
        :
    done

    # 3) Ruhe eingekehrt -> MPD-Datenbank einmal aktualisieren.
    mpc update >/dev/null 2>&1
    logger -t custom_mpd_watch "Aenderung in audiofolders erkannt -> mpc update ausgefuehrt"
done
