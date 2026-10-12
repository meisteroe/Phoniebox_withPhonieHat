<?php
/*
 * backup_import.php — stellt eine Konfigurations-Sicherung wieder her.
 *
 * Sicherheit:
 *   - akzeptiert nur echte .tar.gz (gzip-Magic geprueft)
 *   - listet den Archivinhalt und lehnt absolute Pfade, ".." und unerwartete
 *     oberste Verzeichnisse ab (nur settings/, components/, shared/)
 *   - legt VOR dem Ueberschreiben eine Auto-Sicherung der aktuellen Konfiguration
 *     unter shared/config-backups/ an (falls etwas schiefgeht)
 */

header('Content-Type: text/plain; charset=utf-8');

$base = realpath(__DIR__ . '/../..'); // Repo-Wurzel
$allowedTop = array('settings', 'components', 'shared');

if (!isset($_FILES['backupfile']) || $_FILES['backupfile']['error'] !== UPLOAD_ERR_OK) {
    http_response_code(400);
    echo "Keine Datei empfangen (oder Upload-Fehler).";
    exit;
}

$tmp = $_FILES['backupfile']['tmp_name'];

// gzip-Magic pruefen (1F 8B)
$fh = fopen($tmp, 'rb');
$magic = $fh ? fread($fh, 2) : '';
if ($fh) { fclose($fh); }
if ($magic !== "\x1f\x8b") {
    http_response_code(400);
    echo "Das ist keine gueltige .tar.gz-Sicherungsdatei.";
    exit;
}

// Inhalt listen und validieren
$list = shell_exec('tar tzf ' . escapeshellarg($tmp) . ' 2>&1');
$entries = array_filter(array_map('trim', explode("\n", (string)$list)));
if (empty($entries)) {
    http_response_code(400);
    echo "Archiv ist leer oder nicht lesbar.";
    exit;
}
foreach ($entries as $e) {
    if ($e === '') { continue; }
    if ($e[0] === '/' || strpos($e, '..') !== false) {
        http_response_code(400);
        echo "Unsichere Pfade in der Sicherung abgelehnt: " . $e;
        exit;
    }
    $top = explode('/', $e)[0];
    if (!in_array($top, $allowedTop, true)) {
        http_response_code(400);
        echo "Unerwarteter Pfad in der Sicherung abgelehnt: " . $e;
        exit;
    }
}

// Auto-Sicherung der AKTUELLEN Konfiguration ERZWINGEN (ohne sie wird nichts restauriert)
$backupDir = $base . '/shared/config-backups';
shell_exec('sudo mkdir -p ' . escapeshellarg($backupDir) . ' 2>/dev/null');
$snap = $backupDir . '/auto-vor-restore-' . date('Ymd-His') . '.tar.gz';
shell_exec('sudo tar czf ' . escapeshellarg($snap)
    . ' -C ' . escapeshellarg($base)
    . ' settings components/led_feedback/led_settings.json shared/shortcuts 2>/dev/null');
if (!file_exists($snap)) {
    http_response_code(500);
    echo "Abbruch: Sicherheitskopie konnte nicht angelegt werden. Es wurde nichts veraendert.";
    exit;
}

// Wiederherstellen als root, damit vorhandene Dateien zuverlaessig ueberschrieben werden.
// -p und --same-owner stellen die urspruenglichen Rechte und Besitzer exakt wieder her.
$out = shell_exec('sudo tar xzpf ' . escapeshellarg($tmp) . ' --same-owner -C ' . escapeshellarg($base) . ' 2>&1');

// LED-Dienst neu starten, damit led_settings.json sofort greift
shell_exec('sudo systemctl restart led-feedback.service 2>/dev/null');

echo "Wiederherstellung abgeschlossen.\n\n";
echo "Wiederhergestellt: " . count($entries) . " Eintraege (settings, LED-Einstellungen, Karten-Zuordnungen).\n";
echo "Sicherheitskopie der vorherigen Konfiguration: shared/config-backups/" . basename($snap) . "\n\n";
if (trim((string)$out) !== '') { echo "Hinweise von tar:\n" . $out . "\n\n"; }
echo "Empfehlung: Box einmal neu starten, damit alle Dienste die Einstellungen sicher uebernehmen.";
