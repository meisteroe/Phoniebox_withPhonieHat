#!/bin/bash
# Entfernt Recording-Verknüpfung von Karte
# Datei bleibt erhalten!

#!/bin/bash
# Entfernt Recording-Verknüpfung
# Wird nur bei Recording-Karten ausgeführt

#!/bin/bash
# Recording-Verknüpfung entfernen mit LED-Feedback v2

#!/bin/bash
# Recording entknüpfen - KOMPLETT (Shortcut + Archiv + MPD Stop)

LAST_CARD_FILE="/home/pi/RPi-Jukebox-RFID/settings/Latest_RFID"
SHORTCUTS_DIR="/home/pi/RPi-Jukebox-RFID/shared/shortcuts"
RFID_CONFIG="/home/pi/RPi-Jukebox-RFID/settings/rfid_trigger_play.conf"
RECORD_BASE="/home/pi/RPi-Jukebox-RFID/shared/audiofolders/Recordings"
ARCHIVE_BASE="/home/pi/RPi-Jukebox-RFID/shared/audiofolders/Recordings/Archiv"
LED_CMD="/tmp/led_command.json"

# === LED FEEDBACK ===
led_unlink_ok() {
    echo '{"command":"feedback","kind":"unlink_ok"}' > "$LED_CMD"
}

led_unlink_error() {
    echo '{"command":"feedback","kind":"unlink_error"}' > "$LED_CMD"
}

# Karte vorhanden?
if [ ! -f "$LAST_CARD_FILE" ]; then
    echo "FEHLER: Keine Karte erkannt!"
    led_unlink_error
    exit 1
fi

CARD_ID=$(cat "$LAST_CARD_FILE" | tr -d '[:space:]')

if [ -z "$CARD_ID" ]; then
    echo "FEHLER: Keine Karte erkannt!"
    led_unlink_error
    exit 1
fi

# Shortcut existiert?
if [ ! -f "$SHORTCUTS_DIR/$CARD_ID" ]; then
    echo "FEHLER: Karte ist nicht verknüpft!"
    led_unlink_error
    exit 1
fi

# Shortcut-Inhalt lesen
TARGET=$(cat "$SHORTCUTS_DIR/$CARD_ID" 2>/dev/null | tr -d '[:space:]')

# Prüfen ob gültiger Shortcut (nicht nur Platzhalter)
if [ -z "$TARGET" ] || [ "$TARGET" = "$CARD_ID" ] || [[ "$TARGET" != *"/"* ]]; then
    echo "FEHLER: Karte hat keine gültige Verknüpfung (nur Platzhalter)!"
    led_unlink_error
    exit 1
fi

# Prüfen ob es ein Recording ist
if [[ "$TARGET" != *"Recordings/"* ]] && [[ "$TARGET" != *"recordings/"* ]]; then
    echo "FEHLER: Karte ist kein Recording!"
    echo "Nur Recording-Verknüpfungen können entfernt werden."
    echo "Verknüpft mit: $TARGET"
    led_unlink_error
    exit 1
fi

echo "=== Entknüpfe Recording-Karte $CARD_ID ==="

# 1. MPD STOPPEN (falls diese Aufnahme gerade spielt)
echo "Stoppe Wiedergabe..."
mpc stop 2>/dev/null
# NEU: evtl. aktiven Aufnahme-Lautstaerke-Boost zuruecknehmen
/home/pi/RPi-Jukebox-RFID/scripts/custom_recording_volume.sh restore 2>/dev/null

# 2. Shortcut löschen
echo "Lösche Verknüpfung..."
rm "$SHORTCUTS_DIR/$CARD_ID"

# 3. Aus rfid_trigger_play.conf entfernen
sed -i "/CARDID=\"$CARD_ID\"/d" "$RFID_CONFIG" 2>/dev/null

# 4. Recording-Ordner komplett ins Archiv verschieben
FOLDER_NAME="Recording_${CARD_ID}"
FOLDER_PATH="${RECORD_BASE}/${FOLDER_NAME}"

if [ -d "$FOLDER_PATH" ]; then
    echo "Verschiebe Aufnahme ins Archiv..."
    
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    ARCHIVE_FOLDER="${ARCHIVE_BASE}/${FOLDER_NAME}_${TIMESTAMP}"
    
    mkdir -p "$ARCHIVE_FOLDER"
    
    # Verschiebe ALLES (inkl. folder.conf)
    mv "$FOLDER_PATH"/* "$ARCHIVE_FOLDER"/ 2>/dev/null
    
    # Lösche leeren Ordner
    rmdir "$FOLDER_PATH" 2>/dev/null
    
    echo "✓ Archiviert: Archiv/${FOLDER_NAME}_${TIMESTAMP}/"
else
    echo "⚠ Kein Recording-Ordner gefunden (nur Shortcut gelöscht)"
fi

# 5. MPD Database aktualisieren
echo "Aktualisiere MPD Database..."
mpc update Recordings 2>/dev/null

# Erfolg!
led_unlink_ok

echo "════════════════════════════════════════"
echo "✓ Karte entknüpft!"
echo "✓ Aufnahme archiviert"
echo "✓ Karte kann neu besprochen werden"
echo "════════════════════════════════════════"