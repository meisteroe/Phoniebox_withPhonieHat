<?php
/**
 * LED API v2
 */
$CMD  = "/tmp/led_command.json";
$STAT = "/tmp/led_status.json";

header('Content-Type: application/json');
$a = isset($_GET['action']) ? $_GET['action'] : 'status';

switch ($a) {
    case 'status':
        if (file_exists($STAT)) {
            $d = json_decode(file_get_contents($STAT), true);
            if ($d && isset($d['timestamp'])) {
                $d['alive'] = (time() - $d['timestamp']) < 10;
                echo json_encode($d);
            } else {
                echo json_encode(['alive' => false]);
            }
        } else {
            echo json_encode(['alive' => false]);
        }
        break;

    case 'set_feedback_brightness':
        w(['command'=>'set_feedback_brightness','value'=>intval($_GET['v'])]);
        break;
    case 'set_lighting_brightness':
        w(['command'=>'set_lighting_brightness','value'=>intval($_GET['v'])]);
        break;
    case 'set_battery_brightness':
        w(['command'=>'set_battery_brightness','value'=>intval($_GET['v'])]);
        break;
    case 'set_battery_threshold':
        w(['command'=>'set_battery_threshold','value'=>intval($_GET['v'])]);
        break;
    case 'toggle_feedback':
        w(['command'=>'toggle_feedback','enabled'=>$_GET['v']==='1']);
        break;
    case 'toggle_lighting':
        w(['command'=>'toggle_lighting','enabled'=>$_GET['v']==='1']);
        break;
    case 'toggle_playback_status':
        w(['command'=>'toggle_playback_status','enabled'=>$_GET['v']==='1']);
        break;

    case 'save_slot':
        $i = intval($_GET['i']);
        $d = ['effect'=>$_GET['effect'],'color'=>$_GET['color'],
              'brightness'=>intval($_GET['brightness']),'speed'=>$_GET['speed']];
        w(['command'=>'save_slot','index'=>$i,'data'=>$d]);
        break;

    case 'test_slot':
        w(['command'=>'test_slot','index'=>intval($_GET['i'])]);
        break;

    case 'light_cycle':
        w(['command'=>'light_cycle']);
        break;
    case 'light_off':
        w(['command'=>'light_off']);
        break;

    case 'feedback':
        w(['command'=>'feedback','kind'=>$_GET['kind']]);
        break;

    default:
        echo json_encode(['error'=>"Unbekannt: $a"]);
}

function w($c) {
    global $CMD;
    echo json_encode(file_put_contents($CMD, json_encode($c)) !== false
        ? ['ok'=>true] : ['error'=>'Schreibfehler']);
}
?>
