<?php
/**
 * Battery Status API
 * Returns battery level and status
 */

header('Content-Type: application/json');

$batteryFile = '/tmp/battery_status.json';

if (file_exists($batteryFile)) {
    $data = file_get_contents($batteryFile);
    $battery = json_decode($data, true);
    
    // Prüfe ob Daten älter als 60s
    if (isset($battery['timestamp'])) {
        $age = time() - $battery['timestamp'];
        if ($age > 60) {
            $battery['status'] = 'stale';
        }
    }
    
    echo json_encode($battery);
} else {
    // Kein Akku-Daten verfügbar
    echo json_encode([
        'voltage' => 0,
        'percent' => 0,
        'status' => 'unavailable'
    ]);
}
?>
