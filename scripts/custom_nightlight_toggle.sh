#!/bin/bash
# Nachtlicht Toggle - Cycle durch programmierbare Slots
# Cycle: Slot 1 → 2 → 3 → 4 → 5 → 6 → aus → Slot 1

LED_CMD="/tmp/led_command.json"

# LED Controller macht das State-Tracking
# Wir senden einfach light_cycle Command
echo '{"command":"light_cycle"}' > "$LED_CMD"

# Log
echo "$(date): Nightlight Cycle" >> /tmp/phoniebox_nightlight.log