#!/bin/bash
# Record System v8 - Multi-Recording + Pause (Segment-basiert)
# ------------------------------------------------------------------
# REC-Taste (dieses Skript, Toggle):
#   - keine Aufnahme aktiv  -> Aufnahme STARTEN (Segment 1)
#   - Aufnahme aktiv/pausiert -> Aufnahme BEENDEN (alle Segmente zusammenfuegen,
#     konvertieren, als neueste Aufnahme speichern)
# Play/Pause-Taste (custom_record_pause.sh): pausiert/setzt fort (neues Segment).
#
# NEU ggü. v7:
#  - Bereits besprochene Karten koennen ERNEUT besprochen werden. Die neue Aufnahme
#    wird die aktuellste (Praefix 01_), alte ruecken nach hinten (02_, 03_, ...).
#    Beim Abspielen laeuft so immer zuerst die neueste, dann die aelteren.
#  - Aufnahme kann pausiert werden (Segmente werden am Ende nahtlos zusammengefuegt).
#  - REC beendet die Aufnahme auch waehrend einer Pause.

RECORD_BASE="/home/pi/RPi-Jukebox-RFID/shared/audiofolders/Recordings"
ARCHIVE_BASE="/home/pi/RPi-Jukebox-RFID/shared/audiofolders/Recordings/Archiv"
STATE_FILE="/tmp/phoniebox_recording_state"
PID_FILE="/tmp/phoniebox_recording_pid"
LAST_CARD_FILE="/home/pi/RPi-Jukebox-RFID/settings/Latest_RFID"
SHORTCUTS_DIR="/home/pi/RPi-Jukebox-RFID/shared/shortcuts"
RFID_CONFIG="/home/pi/RPi-Jukebox-RFID/settings/rfid_trigger_play.conf"
LED_CMD="/tmp/led_command.json"

# arecord-Parameter (unveraendert ggü. bisher)
REC_DEVICE="hw:0,0"
REC_FORMAT="S32_LE"
REC_RATE="48000"
REC_CHANNELS="2"
REC_MAXSEC="300"   # max. Sekunden pro Segment

mkdir -p "$RECORD_BASE"
mkdir -p "$ARCHIVE_BASE"
mkdir -p "$SHORTCUTS_DIR"

# === LED FEEDBACK ===
led_recording_start() { echo '{"command":"feedback","kind":"record_start"}' > "$LED_CMD"; }
led_recording_stop() { echo '{"command":"feedback","kind":"record_stop"}' > "$LED_CMD"; }
led_record_saved() { echo '{"command":"feedback","kind":"record_saved"}' > "$LED_CMD"; }
led_record_error() { echo '{"command":"feedback","kind":"record_error"}' > "$LED_CMD"; }

# === KARTEN-STATUS PRÜFEN ===

is_placeholder() {
    local card_id=$1
    if [ ! -f "$SHORTCUTS_DIR/$card_id" ]; then
        return 0
    fi
    local content=$(cat "$SHORTCUTS_DIR/$card_id" 2>/dev/null | tr -d '[:space:]')
    if [ -z "$content" ] || [ "$content" = "$card_id" ]; then
        return 0
    fi
    return 1
}

get_link_type() {
    # "album", "recording" oder "none"
    local card_id=$1
    if is_placeholder "$card_id"; then
        echo "none"; return
    fi
    local content=$(cat "$SHORTCUTS_DIR/$card_id" 2>/dev/null)
    if [[ "$content" == *"Recordings/"* ]] || [[ "$content" == *"recordings/"* ]]; then
        echo "recording"; return
    fi
    echo "album"
}

update_rfid_config() {
    local card_id=$1
    local folder_name=$2
    sed -i "/CARDID=\"$card_id\"/d" "$RFID_CONFIG" 2>/dev/null
    echo "CARDID=\"$card_id\" CMDID=\"PLAY\" FOLDER=\"Recordings/$folder_name\" FILENAME=\"\"" >> "$RFID_CONFIG"
}

link_card() {
    local card_id=$1
    local folder_name=$2
    echo "Recordings/$folder_name" > "$SHORTCUTS_DIR/$card_id"
    update_rfid_config "$card_id" "$folder_name"
}

# === NEU: bestehende Aufnahmen im Ordner eine Position nach hinten schieben ===
# Damit die neue Aufnahme als "01_" die aktuellste wird und alte nachruecken.
# Zweiphasig (ueber temporaere Namen) -> kollisionsfrei. Lesbarer Namensteil bleibt.
shift_recordings_back() {
    local folder="$1"
    [ -d "$folder" ] || return 0

    local files=()
    while IFS= read -r f; do
        [ -n "$f" ] && files+=("$f")
    done < <(ls -v "$folder"/*.mp3 2>/dev/null)

    local n=${#files[@]}
    [ "$n" -eq 0 ] && return 0

    local i
    # Phase 1: alle auf eindeutige temporaere Namen
    for ((i=0; i<n; i++)); do
        mv -f "${files[$i]}" "$folder/.shifttmp_$i" 2>/dev/null
    done
    # Phase 2: temporaere Namen -> finale Nummer (+1), lesbaren Rest behalten
    for ((i=0; i<n; i++)); do
        local base rest newnum
        base=$(basename "${files[$i]}")
        rest=$(echo "$base" | sed -E 's/^[0-9]{2}_//')   # evtl. vorhandenen NN_-Praefix entfernen
        newnum=$(printf '%02d' $((i + 2)))               # 01->02, 02->03, ...
        mv -f "$folder/.shifttmp_$i" "$folder/${newnum}_${rest}" 2>/dev/null
    done
}

# === HAUPTLOGIK ===

if [ -f "$STATE_FILE" ]; then
    # ========================================================
    # AUFNAHME BEENDEN (funktioniert auch waehrend einer Pause)
    # ========================================================
    echo "=== Aufnahme wird beendet ==="
    led_recording_stop

    CARD_ID=$(cat "$STATE_FILE")
    FOLDER_NAME=$(cat "${STATE_FILE}.folder" 2>/dev/null)
    FILENAME=$(cat "${STATE_FILE}.filename" 2>/dev/null)
    SEGNUM=$(cat "${STATE_FILE}.segnum" 2>/dev/null)
    [ -z "$SEGNUM" ] && SEGNUM=1

    # laufendes arecord stoppen (bei Pause laeuft keins mehr)
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        kill $PID 2>/dev/null
        wait $PID 2>/dev/null
        rm -f "$PID_FILE"
    fi
    rm -f "${STATE_FILE}.paused"

    # Segmente einsammeln
    SEGMENTS=()
    for ((s=1; s<=SEGNUM; s++)); do
        seg="/tmp/recording_${CARD_ID}_seg$(printf '%02d' $s).wav"
        [ -f "$seg" ] && SEGMENTS+=("$seg")
    done

    if [ ${#SEGMENTS[@]} -gt 0 ]; then
        echo "Segmente: ${#SEGMENTS[@]} -> zusammenfuegen + konvertieren..."
        FOLDER_PATH="${RECORD_BASE}/${FOLDER_NAME}"
        mkdir -p "$FOLDER_PATH"

        COMBINED="/tmp/recording_${CARD_ID}_combined.wav"
        if [ ${#SEGMENTS[@]} -eq 1 ]; then
            cp "${SEGMENTS[0]}" "$COMBINED"
        else
            # gleiche arecord-Parameter -> sox fuegt sie nahtlos aneinander
            sox "${SEGMENTS[@]}" "$COMBINED" 2>/dev/null
        fi

        # Mono + Normalisierung + 6dB (wie bisher)
        sox "$COMBINED" -c 1 /tmp/mono.wav remix 1 norm 0 gain 6 2>/dev/null

        # bestehende Aufnahmen nach hinten schieben, neue wird 01_
        shift_recordings_back "$FOLDER_PATH"

        NEWNAME="01_${FILENAME}"
        if command -v lame &> /dev/null; then
            lame -V2 /tmp/mono.wav "${FOLDER_PATH}/${NEWNAME}" 2>/dev/null
            rm -f /tmp/mono.wav
        else
            mv /tmp/mono.wav "${FOLDER_PATH}/${NEWNAME%.mp3}.wav"
            NEWNAME="${NEWNAME%.mp3}.wav"
        fi

        # Aufraeumen
        rm -f "${SEGMENTS[@]}" "$COMBINED"

        echo "Aktualisiere MPD Database..."
        mpc update Recordings 2>/dev/null
        sleep 2

        link_card "$CARD_ID" "$FOLDER_NAME"
        led_record_saved

        echo "=== Aufnahme gespeichert ==="
        echo "Ordner: Recordings/$FOLDER_NAME"
        echo "Datei:  $NEWNAME"
        echo "Karte:  $CARD_ID"
        echo "=========================="
    else
        echo "FEHLER: Keine Aufnahme-Segmente gefunden!"
        led_record_error
    fi

    rm -f "$STATE_FILE" "${STATE_FILE}.folder" "${STATE_FILE}.filename" "${STATE_FILE}.segnum"

else
    # ========================================================
    # AUFNAHME STARTEN
    # ========================================================
    if [ ! -f "$LAST_CARD_FILE" ]; then
        echo "FEHLER: Keine Karte erkannt!"
        led_record_error
        exit 1
    fi

    CARD_ID=$(cat "$LAST_CARD_FILE" | tr -d '[:space:]')
    if [ -z "$CARD_ID" ]; then
        echo "FEHLER: Keine Karte erkannt!"
        led_record_error
        exit 1
    fi

    LINK_TYPE=$(get_link_type "$CARD_ID")
    echo "Karte: $CARD_ID (Typ: $LINK_TYPE)"

    # Album-Karten bleiben gesperrt (die sollen nicht ueberschrieben werden)
    if [ "$LINK_TYPE" = "album" ]; then
        echo "════════════════════════════════════════"
        echo "FEHLER: Diese Karte ist mit einem Album verknüpft!"
        echo "Album-Karten können nicht besprochen werden."
        echo "════════════════════════════════════════"
        led_record_error
        exit 1
    fi

    # NEU: Recording-Karten sind jetzt ERLAUBT (weitere Aufnahme moeglich).
    # Falls die Karte gerade abgespielt wird -> Wiedergabe stoppen.
    if [ "$LINK_TYPE" = "recording" ]; then
        echo "Karte hat bereits Aufnahme(n) - neue Aufnahme wird die aktuellste."
        mpc stop 2>/dev/null
    fi

    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    FOLDER_NAME="Recording_${CARD_ID}"
    FILENAME="aufnahme_${TIMESTAMP}.mp3"

    echo "=== Starte Aufnahme ==="
    echo "Karte:  $CARD_ID"
    echo "Ordner: $FOLDER_NAME"
    echo "======================="

    led_recording_start

    mpc pause 2>/dev/null
    sleep 0.5

    # Zustand ablegen (Segment 1)
    echo "$CARD_ID" > "$STATE_FILE"
    echo "$FOLDER_NAME" > "${STATE_FILE}.folder"
    echo "$FILENAME" > "${STATE_FILE}.filename"
    echo "1" > "${STATE_FILE}.segnum"
    rm -f "${STATE_FILE}.paused"

    SEG_WAV="/tmp/recording_${CARD_ID}_seg01.wav"
    arecord -D "$REC_DEVICE" -f "$REC_FORMAT" -r "$REC_RATE" -c "$REC_CHANNELS" -d "$REC_MAXSEC" "$SEG_WAV" 2>/dev/null &
    echo $! > "$PID_FILE"

    echo "Aufnahme läuft... (Play/Pause = pausieren, REC = beenden)"
fi
