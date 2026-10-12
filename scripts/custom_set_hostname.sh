#!/bin/bash
# custom_set_hostname.sh — setzt den System-Hostnamen (Geraetename) sicher.
# Aufruf: sudo custom_set_hostname.sh <neuer-name>
# Validierung nach RFC-1123: a-z 0-9 Bindestrich, 1-63 Zeichen,
# darf nicht mit Bindestrich beginnen/enden. Wird in Kleinbuchstaben gesetzt.

NEW="$1"
NEW="$(echo "$NEW" | tr '[:upper:]' '[:lower:]')"

if ! echo "$NEW" | grep -Eq '^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$'; then
  echo "FEHLER: ungueltiger Hostname"
  exit 1
fi

OLD="$(hostname)"
if [ "$NEW" = "$OLD" ]; then
  echo "OK: Geraetename unveraendert ($NEW)"
  exit 0
fi

# 1) Hostname setzen (schreibt /etc/hostname)
hostnamectl set-hostname "$NEW"

# 2) /etc/hosts: 127.0.1.1-Zeile aktualisieren oder anlegen
if grep -q '^127.0.1.1' /etc/hosts; then
  sed -i "s/^127.0.1.1.*/127.0.1.1\t$NEW/" /etc/hosts
else
  printf '127.0.1.1\t%s\n' "$NEW" >> /etc/hosts
fi

# 3) Avahi neu starten, damit <name>.local sofort gilt
systemctl restart avahi-daemon 2>/dev/null || true

echo "OK: Geraetename geaendert von '$OLD' auf '$NEW'. Erreichbar als $NEW.local"
