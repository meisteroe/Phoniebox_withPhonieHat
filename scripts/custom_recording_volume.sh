#!/bin/bash
# Lautstaerke-Boost fuer die Wiedergabe von Aufnahme-Karten.
# apply   : merkt den aktuellen Lautstaerke-Wert und hebt um 15 an (max. 100 bzw. Max-Limit).
#           Startet einen ereignisbasierten Waechter (mpc idle -> akkuschonend), der die
#           Lautstaerke am ENDE der Wiedergabe automatisch zuruecksetzt.
# restore : setzt sofort auf den gemerkten Ausgangswert zurueck (bei Kartenwechsel/Stop)
#           und beendet den Waechter.
# Der Ausgangswert wird gemerkt und exakt wiederhergestellt -> auch wenn der Boost am
# Max-Limit gedeckelt wurde, gibt es keine Asymmetrie.

PATHDATA="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BOOST_FILE="/tmp/phoniebox_rec_boost"
BOOST_PID="/tmp/phoniebox_rec_boost_pid"
BOOST_STEP=15

COMMAND="$1"

do_restore() {
    [ -f "$BOOST_FILE" ] || return 0
    local oldvol
    oldvol=$(cat "$BOOST_FILE" 2>/dev/null)
    rm -f "$BOOST_FILE"
    if [ -f "$BOOST_PID" ]; then
        kill "$(cat "$BOOST_PID" 2>/dev/null)" 2>/dev/null
        rm -f "$BOOST_PID"
    fi
    if [ -n "$oldvol" ]; then
        ${PATHDATA}/playout_controls.sh -c=setvolume -v="$oldvol" >/dev/null 2>&1
    fi
}

case "$COMMAND" in
    apply)
        # Nur einmal anheben (falls nicht schon aktiv), damit der gemerkte Ausgangswert stimmt.
        if [ ! -f "$BOOST_FILE" ]; then
            CURVOL=$(${PATHDATA}/playout_controls.sh -c=getvolume 2>/dev/null | tr -dc '0-9')
            if [ -n "$CURVOL" ]; then
                echo "$CURVOL" > "$BOOST_FILE"
                NEWVOL=$((CURVOL + BOOST_STEP))
                [ "$NEWVOL" -gt 100 ] && NEWVOL=100
                ${PATHDATA}/playout_controls.sh -c=setvolume -v="$NEWVOL" >/dev/null 2>&1
            fi
        fi
        # Vorherigen Waechter beenden, neuen starten.
        if [ -f "$BOOST_PID" ]; then
            kill "$(cat "$BOOST_PID" 2>/dev/null)" 2>/dev/null
            rm -f "$BOOST_PID"
        fi
        # Waechter: wartet ereignisbasiert bis MPD stoppt (Aufnahme zu Ende), dann zuruecksetzen.
        (
            sleep 2   # kurz warten, bis die Wiedergabe wirklich laeuft
            while true; do
                STATE=$(echo -e "status\nclose" | nc -w 2 localhost 6600 | grep -oP '(?<=state: ).*')
                if [ "$STATE" = "stop" ] || [ -z "$STATE" ]; then
                    break
                fi
                mpc idle player >/dev/null 2>&1   # blockiert bis zum naechsten Player-Event
            done
            # Wir SIND der Waechter -> inline zuruecksetzen (nicht uns selbst killen).
            if [ -f "$BOOST_FILE" ]; then
                OLDVOL=$(cat "$BOOST_FILE" 2>/dev/null)
                rm -f "$BOOST_FILE" "$BOOST_PID"
                [ -n "$OLDVOL" ] && ${PATHDATA}/playout_controls.sh -c=setvolume -v="$OLDVOL" >/dev/null 2>&1
            fi
        ) &
        echo $! > "$BOOST_PID"
        ;;
    restore)
        do_restore
        ;;
    *)
        echo "Usage: $0 {apply|restore}"
        ;;
esac
