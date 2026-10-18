# Changelog – Phoniebox Custom HAT Edition

## 1.0.2 (2026-10-18)

### Verbessert
- Komplettanleitung liegt jetzt im Repo und wird ueber den Update-Knopf mitverteilt (kuenftige Funktionen landen automatisch in der Anleitung).
- Anleitung: Abschnitt zur Ordnerstruktur ergaenzt - gleiche Pfade sorgen dafuer, dass verliehene Karten boxuebergreifend funktionieren.

## 1.0.1 (2026-10-18)

### Verbessert
- WLAN-Laendercode DE (Client und Hotspot) gesetzt: zuverlaessigerer Verbindungs- und Hotspot-Start.
- Hotspot bleibt bei fehlendem WLAN 4 Minuten offen und schaltet dann ab (Akku sparen, kein Wieder-Aufgehen bis Neustart).

## 1.0.0 (2026-10-12)

Erste eigenständige Version für die PhonieHat-Hardware (Pi Zero 2W, PN532/MFRC522, SK9822-LEDs, Akku).

### Enthalten
- **LED-System** (SK9822): Feedback-Signale, Sleeptimer-Anzeige, Akku-Anzeige (Helligkeit/Schwelle einstellbar), dekorative Beleuchtung, Lichtorgel 1 & 2 (interner Audio-Pegel über MPD-FIFO), Flacker-Mitigation.
- **Aufnahme**: Mehrfachaufnahme, Pause/Segmente, Lautstärke-Anhebung bei Wiedergabe, Löschen ins Archiv.
- **WLAN**: Suchfunktion in der WebUI, Fix für SSIDs mit Leerzeichen.
- **Dokumentation**: Viewer in der WebUI (Unterordner, sichere Auslieferung).
- **SD-Schonung**: /tmp & journald im RAM, rsyslog aus, unnötige Tages-Timer deaktiviert, Live-Log-Viewer (liest aus dem RAM).
- **Admin**: Versionsstempel, Gerätename-Feld, Konfig-Sicherung & -Wiederherstellung, Software-Update per Knopf (GitHub), Hardware-Watchdog.

### Hardware
- RFID: PN532 (aktiv) und MFRC522 wählbar über `dual_reader.py`.
- Audio/LED/Akku über Custom HAT.
