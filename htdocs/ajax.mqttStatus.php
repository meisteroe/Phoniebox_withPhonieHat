<?php
// Status des Smart-Home-Dienstes (MQTT) fuer die Einstellungsseite.
header('Content-Type: application/json');
header('Cache-Control: no-store');
$script = realpath(__DIR__.'/../scripts/custom_mqtt.sh');
$out = shell_exec("/usr/bin/sudo ".escapeshellarg($script)." status 2>/dev/null");
echo ($out && json_decode($out) !== null) ? $out : '{}';
