#!/bin/bash
# custom_firstboot.sh - EINMALIGE Erstinitialisierung eines geklonten Golden-Image.
#
# Laeuft via systemd beim ersten Start, ABER nur wenn der Marker fehlt.
# Der Marker liegt auf der FAT-Boot-Partition (/boot) und ist damit unter Windows
# sichtbar: Auf einem frisch geflashten KLON loescht man ihn einmal -> beim Boot
# richtet sich die Box selbst ein. Danach legt das Skript den Marker neu an und
# laeuft nie wieder.
#
# WICHTIG: Auf der Entwickler-Box (Adrian) ist der Marker gesetzt -> hier passiert NICHTS.

MARKER="/boot/phoniebox-firstboot.done"
REPO="/home/pi/RPi-Jukebox-RFID"

if [ -f "$MARKER" ]; then
    exit 0                     # schon initialisiert / Entwickler-Box -> nichts tun
fi

echo "[phoniebox-firstboot] Erstinitialisierung laeuft..."

# 1) Eigene SSH-Host-Schluessel (eindeutiger "Ausweis" der Box)
rm -f /etc/ssh/ssh_host_*
ssh-keygen -A

# 2) Eigene machine-id
rm -f /etc/machine-id /var/lib/dbus/machine-id
systemd-machine-id-setup
[ -d /var/lib/dbus ] && ln -sf /etc/machine-id /var/lib/dbus/machine-id

# 3) Entwickler-Push-Zugang entfernen (Klon darf NICHT als Adrian ins Repo schreiben)
rm -f /home/pi/.ssh/id_phoniebox_github /home/pi/.ssh/id_phoniebox_github.pub
rm -f /home/pi/.git-credentials
if [ -d "$REPO/.git" ]; then
    sudo -u pi git -C "$REPO" remote set-url origin https://github.com/meisteroe/Phoniebox_withPhonieHat.git 2>/dev/null
fi

# 4) Fremde WLAN-Zugangsdaten entfernen -> Klon startet im Hotspot, Empfaenger traegt
#    sein eigenes WLAN ueber die WebUI ein. Laendercode wird uebernommen.
WPA="/etc/wpa_supplicant/wpa_supplicant.conf"
if [ -f "$WPA" ]; then
    CC="$(grep -i '^country=' "$WPA" 2>/dev/null | head -1)"
    [ -z "$CC" ] && CC="country=DE"
    cat > "$WPA" <<EOF
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
$CC
EOF
    chmod 600 "$WPA"
fi

# 5) Persoenliche Spuren entfernen
rm -f /home/pi/.bash_history /root/.bash_history

# 6) Marker setzen -> laeuft nie wieder
touch "$MARKER"

# 7) SSH mit den neuen Schluesseln neu starten
systemctl restart ssh 2>/dev/null || systemctl restart sshd 2>/dev/null

echo "[phoniebox-firstboot] fertig - Box hat jetzt eine eigene, saubere Identitaet."
exit 0
