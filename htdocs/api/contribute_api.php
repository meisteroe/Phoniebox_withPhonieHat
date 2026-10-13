<?php
/*
 * contribute_api.php - Mit-Entwickler-Beitrag (Collaborator-Modell).
 *   ?action=status            -> ist ein Zugangs-Token eingerichtet? (GET)
 *    action=savetoken (POST)  -> Token (+Name) speichern. Token kommt per STDIN an das
 *                                Helfer-Skript, damit er NIE in der Prozessliste auftaucht.
 *    action=submit    (POST)  -> lokale Aenderungen als Zweig/PR einreichen.
 * Der Token wird nie zurueckgegeben, nie geloggt, nie ins Repo geschrieben.
 */

header('Content-Type: text/plain; charset=utf-8');
header('Cache-Control: no-store');

$action = isset($_POST['action']) ? $_POST['action'] : (isset($_GET['action']) ? $_GET['action'] : '');
$script = '/home/pi/RPi-Jukebox-RFID/scripts/custom_contribute.sh';

if ($action === 'status') {
    echo shell_exec('sudo -u pi -H bash ' . escapeshellarg($script) . ' status 2>&1');
    exit;
}

if ($action === 'savetoken') {
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(405); echo "POST noetig."; exit; }
    $token = isset($_POST['token']) ? $_POST['token'] : '';
    $name  = isset($_POST['name'])  ? $_POST['name']  : '';
    if (trim($token) === '') { http_response_code(400); echo "Kein Token angegeben."; exit; }

    $cmd = 'sudo -u pi -H bash ' . escapeshellarg($script) . ' savetoken ' . escapeshellarg($name);
    $spec = array(0 => array('pipe','r'), 1 => array('pipe','w'), 2 => array('pipe','w'));
    $proc = proc_open($cmd, $spec, $pipes);
    if (is_resource($proc)) {
        fwrite($pipes[0], $token);              // Token ausschliesslich ueber STDIN
        fclose($pipes[0]);
        $out = stream_get_contents($pipes[1]); fclose($pipes[1]);
        $err = stream_get_contents($pipes[2]); fclose($pipes[2]);
        proc_close($proc);
        echo trim($out . $err);
    } else {
        http_response_code(500); echo "Konnte den Speichervorgang nicht starten.";
    }
    exit;
}

if ($action === 'submit') {
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(405); echo "POST noetig."; exit; }
    $desc = isset($_POST['desc']) ? $_POST['desc'] : '';
    echo shell_exec('sudo -u pi -H bash ' . escapeshellarg($script) . ' submit ' . escapeshellarg($desc) . ' 2>&1');
    exit;
}

http_response_code(400);
echo "Ungueltige Aktion.";
