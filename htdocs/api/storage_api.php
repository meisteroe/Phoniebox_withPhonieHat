<?php
/*
 * storage_api.php — erweitert das Dateisystem auf die volle SD-Kartengroesse.
 *   action=expand (nur POST): parted resizepart + resize2fs (online, kein Reboot).
 * Nur-Wachsen-Operation; laeuft via sudo (www-data NOPASSWD). Ist die Karte schon
 * voll genutzt, passiert nichts (no-op).
 */

header('Content-Type: text/plain; charset=utf-8');
header('Cache-Control: no-store');

$action = isset($_POST['action']) ? $_POST['action'] : (isset($_GET['action']) ? $_GET['action'] : '');

if ($action !== 'expand') {
    http_response_code(400);
    echo "Ungueltige Aktion.";
    exit;
}
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo "Erweitern bitte ueber den Knopf (POST).";
    exit;
}

$before = trim(shell_exec("df -h / | awk 'NR==2{print \$2}'"));

// Partition 2 bis zum Kartenende wachsen lassen, dann Dateisystem online vergroessern
shell_exec("sudo parted -s /dev/mmcblk0 resizepart 2 100% 2>&1");
$rs = shell_exec("sudo resize2fs /dev/mmcblk0p2 2>&1");

$after = trim(shell_exec("df -h / | awk 'NR==2{print \$2}'"));

echo "Dateisystem vorher:  $before\n";
echo "Dateisystem nachher: $after\n\n";
if (trim($after) === trim($before)) {
    echo "(Keine Aenderung — die Karte war wohl schon voll genutzt.)";
} else {
    echo "Erfolgreich auf die volle Kartengroesse erweitert.";
}
