<?php
/*
* docViewer.php — sicherer Datei-Server fuer den Dokumentations-Ordner (../Doku).
* Zeigt PDF/HTML/Bilder/Text inline im Browser an. Wird vom Dokumentations-Panel
* in systemInfo.php verlinkt (docViewer.php?doc=<Dateiname>).
*
* Sicherheit: basename() entfernt Pfad-Anteile, realpath()+Praefix-Check stellt sicher,
* dass ausschliesslich Dateien direkt aus dem Doku-Ordner ausgeliefert werden
* (kein Directory-Traversal, keine Symlink-Ausbrueche).
*/

$dokuDir = realpath(__DIR__ . '/../Doku');

// relativer Pfad innerhalb Doku (Unterordner erlaubt), aber kein ".." (Directory-Traversal)
$requested = isset($_GET['doc']) ? (string)$_GET['doc'] : '';
$requested = ltrim(str_replace('\\', '/', $requested), '/');
$path = ($dokuDir !== false && $requested !== '' && strpos($requested, '..') === false)
        ? realpath($dokuDir . '/' . $requested) : false;

// Validierung: Datei muss existieren UND innerhalb des Doku-Ordners liegen
if ($dokuDir === false || $path === false || strpos($path, $dokuDir . DIRECTORY_SEPARATOR) !== 0 || !is_file($path)) {
    http_response_code(404);
    header('Content-Type: text/plain; charset=utf-8');
    echo "Dokument nicht gefunden.";
    exit;
}

// Nur erlaubte Dateitypen ausliefern
$ext = strtolower(pathinfo($path, PATHINFO_EXTENSION));
$types = array(
    'pdf'  => 'application/pdf',
    'html' => 'text/html; charset=utf-8',
    'htm'  => 'text/html; charset=utf-8',
    'md'   => 'text/plain; charset=utf-8',
    'txt'  => 'text/plain; charset=utf-8',
    'png'  => 'image/png',
    'jpg'  => 'image/jpeg',
    'jpeg' => 'image/jpeg',
    'gif'  => 'image/gif',
    'svg'  => 'image/svg+xml',
    'stl'  => 'application/octet-stream',
    '3mf'  => 'application/octet-stream',
    'obj'  => 'application/octet-stream',
    'step' => 'application/octet-stream',
    'stp'  => 'application/octet-stream',
    'zip'  => 'application/zip',
);
if (!isset($types[$ext])) {
    http_response_code(415);
    header('Content-Type: text/plain; charset=utf-8');
    echo "Dateityp wird nicht unterstuetzt.";
    exit;
}

// 3D-/Archiv-Dateien herunterladen, den Rest inline anzeigen; ?dl=1 erzwingt Download.
$forceDownload = array('stl', '3mf', 'obj', 'step', 'stp', 'zip');
$disp = ((isset($_GET['dl']) && $_GET['dl']) || in_array($ext, $forceDownload)) ? 'attachment' : 'inline';
header('Content-Type: ' . $types[$ext]);
header('Content-Length: ' . filesize($path));
header('Content-Disposition: ' . $disp . '; filename="' . basename($path) . '"');
header('X-Content-Type-Options: nosniff');
readfile($path);
