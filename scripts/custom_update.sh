#!/bin/bash
# custom_update.sh - holt Updates aus dem GitHub-Repo (origin) und wendet sie
# SICHER an: nur Vorspulen (fast-forward), nie erzwungen. Vorher wird die
# Konfiguration automatisch gesichert. Laeuft als Benutzer 'pi' (Repo-Besitzer).
#
# Aufruf: custom_update.sh check | apply

REPO="/home/pi/RPi-Jukebox-RFID"
cd "$REPO" || { echo "FEHLER: Repo nicht gefunden"; exit 1; }

# Updates werden ueber die OEFFENTLICHE HTTPS-Adresse geholt -> funktioniert auf jeder
# (auch geklonten) Box OHNE privaten Schluessel. Der SSH-Deploy-Key wird nur fuers
# Pushen auf der Entwickler-Box gebraucht, nicht hier.
PULL_URL="https://github.com/meisteroe/Phoniebox_withPhonieHat.git"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
[ -z "$BRANCH" ] && BRANCH="master"

case "$1" in
  check)
    if ! git fetch "$PULL_URL" "$BRANCH" --quiet 2>/tmp/upd_err; then
      echo "STATUS:error"
      echo "GitHub nicht erreichbar:"; cat /tmp/upd_err 2>/dev/null
      exit 0
    fi
    LOCAL="$(git rev-parse HEAD)"
    REMOTE="$(git rev-parse FETCH_HEAD 2>/dev/null)"
    if [ "$LOCAL" = "$REMOTE" ]; then
      echo "STATUS:uptodate"
      echo "Alles aktuell (Stand $(git rev-parse --short HEAD), Version $(cat VERSION 2>/dev/null))."
    else
      BEHIND="$(git rev-list --count HEAD..FETCH_HEAD 2>/dev/null)"
      echo "STATUS:available"
      echo "$BEHIND neue Aenderung(en) verfuegbar:"
      git log --pretty="  - %s (%an)" HEAD..FETCH_HEAD 2>/dev/null | head -30
    fi
    ;;

  apply)
    # 1) Konfiguration sichern (Netz, falls das Update doch stoert)
    mkdir -p shared/config-backups
    tar czf "shared/config-backups/auto-vor-update-$(date +%Y%m%d-%H%M%S).tar.gz" \
        -C "$REPO" settings components/led_feedback/led_settings.json shared/shortcuts 2>/dev/null

    # 2) Holen (oeffentlich, ohne Schluessel)
    if ! git fetch "$PULL_URL" "$BRANCH" --quiet 2>/tmp/upd_err; then
      echo "FEHLER: GitHub nicht erreichbar."; cat /tmp/upd_err 2>/dev/null; exit 1
    fi

    # 3) Nur vorspulen - niemals erzwungen. Bei Divergenz/lokalen Aenderungen: Abbruch.
    OUT="$(git merge --ff-only FETCH_HEAD 2>&1)"
    if [ $? -ne 0 ]; then
      echo "FEHLER: Update nicht moeglich (lokale Aenderungen oder abweichende Historie)."
      echo "Es wurde nichts veraendert. Details:"
      echo "$OUT"
      exit 1
    fi

    echo "OK: aktualisiert auf $(git rev-parse --short HEAD) (Version $(cat VERSION 2>/dev/null))."
    echo "Starte Dienste neu..."
    sudo systemctl restart led-feedback battery-monitor pn532 phoniebox-gpio-control mpd-autoupdate 2>/dev/null
    echo "Fertig. Bei groesseren Updates ggf. einmal komplett neu starten."
    ;;

  *)
    echo "usage: $0 check|apply"
    exit 1
    ;;
esac
