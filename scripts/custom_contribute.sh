#!/bin/bash
# custom_contribute.sh - Mit-Entwickler-Beitrag (Collaborator-Modell).
# Speichert den GitHub-Zugangs-Token (HTTPS) und reicht lokale Aenderungen
# als Zweig/Pull-Request ein. Laeuft als Benutzer 'pi'.
#
# Aufruf:  status | savetoken "<Name>" (Token kommt ueber STDIN) | submit "<Beschreibung>"

REPO="/home/pi/RPi-Jukebox-RFID"
cd "$REPO" || { echo "FEHLER: Repo nicht gefunden"; exit 1; }

PUSH_URL="https://github.com/meisteroe/Phoniebox_withPhonieHat.git"
CREDFILE="/home/pi/.git-credentials"
export GIT_TERMINAL_PROMPT=0   # niemals interaktiv nach Zugangsdaten fragen

token_configured() { [ -s "$CREDFILE" ] && grep -q "github.com" "$CREDFILE"; }

case "$1" in
  status)
    if token_configured; then echo "STATUS:ready"; else echo "STATUS:notoken"; fi
    echo "name:$(git config user.name 2>/dev/null)"
    ;;

  savetoken)
    NAME="$2"
    TOKEN="$(cat)"                               # Token NUR ueber STDIN, nie als Argument
    TOKEN="$(printf '%s' "$TOKEN" | tr -d '[:space:]')"
    if [ -z "$TOKEN" ]; then echo "FEHLER: leerer Token"; exit 1; fi
    umask 077
    printf 'https://x-access-token:%s@github.com\n' "$TOKEN" > "$CREDFILE"
    chmod 600 "$CREDFILE"
    git config credential.helper store
    if [ -n "$NAME" ]; then
      git config user.name "$NAME"
      SAFE="$(printf '%s' "$NAME" | tr ' ' '.' | tr -cd '[:alnum:].')"
      git config user.email "${SAFE:-phoniebox}@phoniebox.local"
    fi
    echo "OK: Zugang gespeichert. Du kannst jetzt Vorschlaege einreichen."
    ;;

  submit)
    DESC="$2"; [ -z "$DESC" ] && DESC="Vorschlag von der Phoniebox"
    if ! token_configured; then
      echo "FEHLER: Noch kein Zugangs-Token gespeichert - bitte zuerst oben einrichten."
      exit 1
    fi
    if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
      echo "Keine Aenderungen zum Einreichen gefunden."
      exit 0
    fi
    BR="vorschlag/$(date +%Y%m%d-%H%M%S)"
    git stash push -u -q -m "contribute" || { echo "FEHLER: konnte Aenderungen nicht sichern"; exit 1; }
    if ! git checkout -q -b "$BR" master 2>/tmp/contrib_err; then
      echo "FEHLER: $(cat /tmp/contrib_err 2>/dev/null)"; git stash pop -q 2>/dev/null; exit 1
    fi
    git stash apply -q
    git add -A
    git commit -q -m "$DESC"
    if git push -q "$PUSH_URL" "$BR" 2>/tmp/contrib_err; then
      git checkout -q master
      git branch -D "$BR" -q 2>/dev/null
      git stash pop -q 2>/dev/null            # Aenderungen bleiben auf der Box aktiv
      echo "OK: Vorschlag hochgeladen."
      echo "Jetzt den Pull Request oeffnen und abschicken (einmal einloggen):"
      echo "https://github.com/meisteroe/Phoniebox_withPhonieHat/compare/master...$BR?expand=1"
    else
      echo "FEHLER: Hochladen fehlgeschlagen - Token/Rechte pruefen:"
      cat /tmp/contrib_err 2>/dev/null
      git checkout -q master
      git branch -D "$BR" -q 2>/dev/null
      git stash pop -q 2>/dev/null
      echo "(Deine Aenderungen sind unveraendert erhalten.)"
    fi
    ;;

  *) echo "usage: $0 status|savetoken|submit"; exit 1 ;;
esac
