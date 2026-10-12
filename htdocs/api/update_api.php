<?php
/*
 * update_api.php - loest das Software-Update aus (GitHub-Pull).
 *   ?action=check  -> prueft, ob Updates vorliegen (GET)
 *    action=apply  -> wendet sie an (nur POST, mit Bestaetigung im Frontend)
 *
 * Laeuft das eigentliche git/Service-Kommando als Benutzer 'pi' (Repo-Besitzer)
 * ueber scripts/custom_update.sh. Nur die beiden festen Aktionen sind erlaubt.
 */

header('Content-Type: text/plain; charset=utf-8');
header('Cache-Control: no-store');

$action = isset($_GET['action']) ? $_GET['action'] : (isset($_POST['action']) ? $_POST['action'] : '');

if ($action !== 'check' && $action !== 'apply') {
    http_response_code(400);
    echo "Ungueltige Aktion.";
    exit;
}

// 'apply' nur per POST, damit es nicht versehentlich per Link ausgeloest wird
if ($action === 'apply' && $_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo "Aktualisieren bitte ueber den Knopf.";
    exit;
}

$script = '/home/pi/RPi-Jukebox-RFID/scripts/custom_update.sh';
$cmd = 'sudo -u pi -H bash ' . escapeshellarg($script) . ' ' . escapeshellarg($action) . ' 2>&1';
echo shell_exec($cmd);
