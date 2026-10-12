<?php
/*
 * backup_export.php — streamt eine tar.gz-Sicherung der Phoniebox-Konfiguration.
 *
 * Inhalt der Sicherung:
 *   - settings/                              (alle Einstellungen: Lautstaerke, GPIO, Idle, ...)
 *   - components/led_feedback/led_settings.json   (LED-/Beleuchtungs-Konfiguration)
 *   - shared/shortcuts/                      (Karten-Zuordnungen: welche Karte -> welcher Ordner)
 *
 * NICHT enthalten: Medien (zu gross, liegen auf der SD) und WLAN-Zugangsdaten
 * (system-/sicherheitsrelevant, pro Box separat). Die Sicherung wird direkt zum
 * Browser gestreamt (kein Temp auf der SD-Karte).
 */

$base = realpath(__DIR__ . '/../..'); // Repo-Wurzel
$items = array(
    'settings',
    'components/led_feedback/led_settings.json',
    'shared/shortcuts',
);

$exist = array();
foreach ($items as $it) {
    if (file_exists($base . '/' . $it)) { $exist[] = $it; }
}
if (empty($exist)) {
    http_response_code(500);
    header('Content-Type: text/plain; charset=utf-8');
    echo "Keine Konfigurationsdaten gefunden.";
    exit;
}

$host  = preg_replace('/[^a-z0-9-]/i', '', trim(shell_exec('hostname')));
$fname = 'phoniebox-config-' . ($host !== '' ? $host : 'box') . '-' . date('Ymd-His') . '.tar.gz';

header('Content-Type: application/gzip');
header('Content-Disposition: attachment; filename="' . $fname . '"');
header('Cache-Control: no-store');

$cmd = 'tar czf - -C ' . escapeshellarg($base) . ' ' . implode(' ', array_map('escapeshellarg', $exist));
passthru($cmd);
