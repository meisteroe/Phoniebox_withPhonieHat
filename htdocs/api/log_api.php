<?php
/*
 * log_api.php — Live-Log-Viewer fuer die WebUI.
 *
 * Liest systemd-Journal-Eintraege ueber journalctl. Da journald auf
 * Storage=volatile steht, liegt das Journal komplett im RAM (/run) —
 * dieses Endpunkt erzeugt daher KEINE Schreibzugriffe auf die SD-Karte.
 *
 * www-data ist Mitglied der Gruppe systemd-journal und liest das Journal
 * daher OHNE sudo (kein Root noetig, keine sudo-Eigeneintraege im Log).
 *
 * Sicherheit: Der Parameter ?source waehlt nur einen Schluessel aus einer
 * festen Whitelist aus; die eigentliche systemd-Unit kommt aus dieser Map,
 * nie direkt aus der Nutzereingabe. ?lines wird auf int gecastet und begrenzt.
 */

header('Content-Type: text/plain; charset=utf-8');
header('Cache-Control: no-store');

// Whitelist: Schluessel (aus der WebUI) -> feste systemd-Unit ('' = ganzes System)
$sources = array(
    'system'         => '',                          // komplettes System (aktueller Boot)
    'pn532'          => 'pn532',                      // RFID-Reader-Daemon
    'gpio'           => 'phoniebox-gpio-control',     // Tasten/GPIO
    'mpd'            => 'mpd',                         // Player
    'led'            => 'led-feedback',               // LED-Steuerung
    'battery'        => 'battery-monitor',            // Akku-Ueberwachung
    'mpd-autoupdate' => 'mpd-autoupdate',             // MPD-DB-Watcher
    'idle'           => 'phoniebox-idle-watchdog',    // Auto-Abschaltung
    'startup'        => 'phoniebox-startup-scripts',  // Startskripte
);

$source = isset($_GET['source']) ? $_GET['source'] : 'system';
if (!array_key_exists($source, $sources)) {
    $source = 'system';
}

$lines = isset($_GET['lines']) ? intval($_GET['lines']) : 100;
if ($lines < 10)   { $lines = 10; }
if ($lines > 1000) { $lines = 1000; }

$unit = $sources[$source];

// Kommando bauen. -b = nur aktueller Boot (Journal ist im RAM, also ohnehin
// nur der aktuelle Boot, aber explizit sauberer). -o short-iso = Zeitstempel.
$cmd = 'journalctl -b --no-pager -o short-iso -n ' . intval($lines);
if ($unit !== '') {
    $cmd .= ' -u ' . escapeshellarg($unit);
}
$cmd .= ' 2>&1';

$out = shell_exec($cmd);
if ($out === null || $out === '') {
    $out = '(keine Eintraege)';
}

echo $out;
