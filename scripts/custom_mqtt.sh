#!/bin/bash
# custom_mqtt.sh — Smart Home (MQTT) aus der WebUI verwalten (Aufruf per sudo).
#
#   custom_mqtt.sh status               -> JSON: Pakete, Dienst, Verbindung
#   custom_mqtt.sh getconf              -> JSON der Einstellungen OHNE Passwort
#   custom_mqtt.sh apply <json> on|off  -> Einstellungen speichern, Dienst an/aus
#                                          (leeres Passwort = bisheriges behalten)
#   custom_mqtt.sh functioncards <file> -> settings/Function_Cards ersetzen
#   custom_mqtt.sh deps                 -> Python-Pakete installieren
#
# Aus = Dienst gestoppt UND deaktiviert: kein Prozess, kein Akkuverbrauch.

PATHDATA="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE="$(dirname "$PATHDATA")"
CONF="$BASE/settings/mqtt_client.json"
CARDS="$BASE/settings/Function_Cards"
COMP="$BASE/components/smart-home-automation/MQTT-protocol"
SERVICE=phoniebox-mqtt-client
UNIT=/etc/systemd/system/$SERVICE.service

deps_ok() { sudo -u pi python3 -c "import paho.mqtt, inotify" >/dev/null 2>&1; }

case "$1" in
    status)
        deps=false; deps_ok && deps=true
        active=$(systemctl is-active $SERVICE 2>/dev/null)
        enabled=$(systemctl is-enabled $SERVICE 2>/dev/null)
        conn=$(cat /tmp/phoniebox-mqtt.status 2>/dev/null)
        [ -n "$conn" ] || conn="{}"
        [ "$active" = "active" ] || conn="{}"
        echo "{\"deps\": $deps, \"active\": \"${active:-unknown}\", \"enabled\": \"${enabled:-disabled}\", \"connection\": $conn}"
        ;;

    getconf)
        python3 - "$CONF" <<'EOF'
import json, sys
try:
    c = json.load(open(sys.argv[1]))
except Exception:
    c = {}
c["hasPassword"] = bool(c.pop("mqttPassword", ""))
print(json.dumps(c))
EOF
        ;;

    apply)
        NEW="$2"; STATE="$3"
        [ -f "$NEW" ] || { echo "FEHLER: keine Einstellungen uebergeben"; exit 1; }
        python3 - "$NEW" "$CONF" <<'EOF' || exit 1
import json, os, sys
new = json.load(open(sys.argv[1]))
old = {}
if os.path.exists(sys.argv[2]):
    try:
        old = json.load(open(sys.argv[2]))
    except Exception:
        pass
if not new.get("mqttPassword"):
    new["mqttPassword"] = old.get("mqttPassword", "")
merged = dict(old)
merged.update(new)
tmp = sys.argv[2] + ".tmp"
with open(tmp, "w") as f:
    json.dump(merged, f, indent=2)
os.replace(tmp, sys.argv[2])
EOF
        chown pi:pi "$CONF"; chmod 600 "$CONF"
        rm -f "$NEW"

        if [ "$STATE" = "on" ]; then
            deps_ok || { echo "FEHLER: Python-Pakete fehlen (paho-mqtt, inotify) – bitte zuerst installieren"; exit 1; }
            if ! cmp -s "$COMP/phoniebox-mqtt-client.service-default.sample" "$UNIT"; then
                cp "$COMP/phoniebox-mqtt-client.service-default.sample" "$UNIT"
                systemctl daemon-reload
            fi
            systemctl enable $SERVICE >/dev/null 2>&1
            systemctl restart $SERVICE
            echo "OK: Smart Home (MQTT) ist eingeschaltet."
        else
            systemctl disable --now $SERVICE >/dev/null 2>&1
            rm -f /tmp/phoniebox-mqtt.status /tmp/phoniebox-mqtt.buttons
            echo "OK: Smart Home (MQTT) ist ausgeschaltet – kein Akkuverbrauch."
        fi
        ;;

    functioncards)
        [ -f "$2" ] || { echo "FEHLER: keine Liste uebergeben"; exit 1; }
        # nur gueltige Karten-IDs (Hex) und Kommentare uebernehmen
        grep -E '^[[:space:]]*(#.*)?$|^[[:space:]]*[0-9A-Fa-f]{4,20}([[:space:]]*#.*)?[[:space:]]*$' "$2" > "$CARDS.tmp"
        mv "$CARDS.tmp" "$CARDS"; rm -f "$2"
        chown pi:www-data "$CARDS"; chmod 664 "$CARDS"
        echo "OK: Funktionskarten gespeichert."
        ;;

    deps)
        pip3 install -q paho-mqtt inotify 2>&1 | tail -3
        deps_ok && echo "OK: Pakete installiert." || { echo "FEHLER: Installation fehlgeschlagen (Internet?)"; exit 1; }
        ;;

    *)
        echo "Usage: $0 status|getconf|apply <json> on|off|functioncards <file>|deps"
        exit 1
        ;;
esac
