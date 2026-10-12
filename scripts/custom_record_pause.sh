#!/bin/bash
# Pausiert bzw. setzt eine laufende Aufnahme fort (Play/Pause-Taste waehrend Aufnahme).
# Wird von function_calls.py (functionCallPlayerPause) aufgerufen, wenn eine Aufnahme
# aktiv ist. Arbeitet Segment-basiert: Pause = aktuelles arecord-Segment beenden,
# Fortsetzen = neues Segment starten. custom_record_toggle.sh fuegt am Ende alle
# Segmente nahtlos zusammen.

STATE_FILE="/tmp/phoniebox_recording_state"
PID_FILE="/tmp/phoniebox_recording_pid"
LED_CMD="/tmp/led_command.json"

REC_DEVICE="hw:0,0"
REC_FORMAT="S32_LE"
REC_RATE="48000"
REC_CHANNELS="2"
REC_MAXSEC="300"

# Nur sinnvoll, wenn ueberhaupt eine Aufnahme aktiv ist
[ -f "$STATE_FILE" ] || exit 0

CARD_ID=$(cat "$STATE_FILE")

if [ -f "${STATE_FILE}.paused" ]; then
    # ============ FORTSETZEN ============
    rm -f "${STATE_FILE}.paused"

    SEGNUM=$(cat "${STATE_FILE}.segnum" 2>/dev/null)
    [ -z "$SEGNUM" ] && SEGNUM=1
    SEGNUM=$((SEGNUM + 1))
    echo "$SEGNUM" > "${STATE_FILE}.segnum"

    SEG_WAV="/tmp/recording_${CARD_ID}_seg$(printf '%02d' $SEGNUM).wav"
    arecord -D "$REC_DEVICE" -f "$REC_FORMAT" -r "$REC_RATE" -c "$REC_CHANNELS" -d "$REC_MAXSEC" "$SEG_WAV" 2>/dev/null &
    echo $! > "$PID_FILE"

    echo '{"command":"feedback","kind":"record_start"}' > "$LED_CMD"
    echo "Aufnahme fortgesetzt (Segment $SEGNUM)."
else
    # ============ PAUSIEREN ============
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        kill $PID 2>/dev/null
        wait $PID 2>/dev/null
        rm -f "$PID_FILE"
    fi
    touch "${STATE_FILE}.paused"

    # record_pause = rot<->gruen pulsierend (rot=REC beenden, gruen=Play/Pause fortsetzen)
    echo '{"command":"feedback","kind":"record_pause"}' > "$LED_CMD"
    echo "Aufnahme pausiert (Play/Pause = fortsetzen, REC = beenden)."
fi
