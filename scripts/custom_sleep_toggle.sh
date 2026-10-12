#!/bin/bash
# Sleep Timer mit LED-Feedback
# Zyklus: aus → 20 → 40 → 60 → aus (pro Druck eine LED mehr, 4. Druck = aus)

STATE_FILE="/tmp/phoniebox_sleep_timer_state"
LED_CMD="/tmp/led_command.json"

# Initialisierung
if [ ! -f "$STATE_FILE" ]; then
    echo "0" > "$STATE_FILE"
fi

CURRENT_STATE=$(cat "$STATE_FILE")

# Zyklus durchschalten
case "$CURRENT_STATE" in
    0)
        NEW_TIME=20
        ;;
    20)
        NEW_TIME=40
        ;;
    40)
        NEW_TIME=60
        ;;
    60)
        NEW_TIME=0
        ;;
    *)
        NEW_TIME=0
        ;;
esac

# Status speichern
echo "$NEW_TIME" > "$STATE_FILE"

# Vorherigen Shutdown abbrechen
sudo shutdown -c 2>/dev/null

if [ "$NEW_TIME" -eq 0 ]; then
    # Timer AUS
    echo "Sleep Timer deaktiviert"
    echo '{"command":"sleep","minutes":0}' > "$LED_CMD"
else
    # Timer AN - Shutdown setzen
    echo "Sleep Timer auf $NEW_TIME Minuten gesetzt"
    sudo shutdown -h +$NEW_TIME
    echo "{\"command\":\"sleep\",\"minutes\":$NEW_TIME}" > "$LED_CMD"
fi

# Log
echo "$(date): Sleep Timer auf $NEW_TIME Minuten" >> /tmp/phoniebox_sleep.log