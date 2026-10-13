#!/bin/bash
# custom_firstboot.sh - EINMALIGE Erstinitialisierung eines geklonten Golden-Image.
#
# Laeuft via systemd beim ersten Start, ABER nur wenn der Marker fehlt. Danach legt
# es den Marker an und laeuft nie wieder. Gibt jeder geklonten Box eine eigene
# Identitaet und entfernt den (nur fuer den Entwickler gedachten) GitHub-Push-Zugang.
#
# WICHTIG: Auf der Entwickler-Box (Adrian) ist der Marker gesetzt -> hier passiert nichts.

MARKER="/var/lib/phoniebox-firstboot.done"
REPO="/home/pi/RPi-Jukebox-RFID"

if [ -f "$MARKER" ]; then
    exit 0                     # schon initialisiert -> nichts tun
fi

echo "[phoniebox-firstboot] Erstinitialisierung laeuft..."

# 1) Eigene SSH-Host-Schluessel (eindeutiger "Ausweis" der Box)
rm -f /etc/ssh/ssh_host_*
ssh-keygen -A

# 2) Eigene machine-id
rm -f /etc/machine-id /var/lib/dbus/machine-id
systemd-machine-id-setup
[ -d /var/lib/dbus ] && ln -sf /etc/machine-id /var/lib/dbus/machine-id

# 3) Entwickler-Push-Zugang entfernen: diese Box darf NICHT als Adrian ins Repo schreiben.
rm -f /home/pi/.ssh/id_phoniebox_github /home/pi/.ssh/id_phoniebox_github.pub
rm -f /home/pi/.git-credentials
#    origin auf oeffentliches HTTPS -> Pushen geht nur noch mit EIGENEM Token (Beitragen-Knopf),
#    Updates-Holen funktioniert ohnehin schluessellos ueber HTTPS.
if [ -d "$REPO/.git" ]; then
    sudo -u pi git -C "$REPO" remote set-url origin https://github.com/meisteroe/Phoniebox_withPhonieHat.git 2>/dev/null
fi

# 4) Marker setzen -> laeuft nie wieder
mkdir -p "$(dirname "$MARKER")"
touch "$MARKER"

# 5) SSH mit den neuen Schluesseln neu starten
systemctl restart ssh 2>/dev/null || systemctl restart sshd 2>/dev/null

echo "[phoniebox-firstboot] fertig - Box hat jetzt eine eigene Identitaet."
exit 0
