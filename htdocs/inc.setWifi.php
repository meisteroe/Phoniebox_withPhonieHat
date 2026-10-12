<?php

$active_essid = trim(exec("iwconfig wlan0 | grep ESSID | cut -d ':' -f 2"),'"');
/*
* Reconfigure all entries from UI
*/
unset($exec);
if(isset($_POST["submitWifi"]) && $_POST["submitWifi"] == "submit") {
    // make multiline bash
    $exec  = "bash -e <<'END'\n";
    $exec .= "source ".$conf['scripts_abs']."/helperscripts/inc.networkHelper.sh\n";
    // SICHERHEIT: aktuelle WLAN-Konfig sichern, bevor sie neu geschrieben wird.
    $exec .= "backup_wpa_conf\n";
    $exec .= "clear_wireless_networks\n";

    $tempPOST = $_POST;
    $_POST=array(); //clear
    foreach ( $tempPOST as $post_key => $post_value ) {
        unset($temp_ssid);
        unset($temp_pass);
        unset($temp_prio);
        if ( substr(trim($post_key), 0, 9) == "WIFIssid_" ) {
            $temp_ssid = trim($post_value);
            $post_key = "WIFIpass_".substr(trim($post_key), 9);
            $post_value = $tempPOST[$post_key];
            $temp_pass = trim($post_value);
            $post_key = "WIFIprio_".substr(trim($post_key), 9);
            $post_value = $tempPOST[$post_key];
            $temp_prio = trim($post_value);

            if (isset($temp_ssid) && $temp_ssid != "" && isset($temp_pass) && strlen($temp_pass) >= 8) {
                if(!isset($temp_prio) || !is_numeric($temp_prio)) {
                    $temp_prio = 0;
                }
                // base64-kodiert uebergeben -> SSID/Passwort mit Leerzeichen und anderen
                // Sonderzeichen kommen sicher durch alle Shell-Ebenen (kein Wortsplitting).
                $exec .= "add_wireless_network_b64 wlan0 ".base64_encode($temp_ssid)." ".base64_encode($temp_pass)." ".intval($temp_prio)."\n";
            }
        }
    }

    // SICHERHEIT: Falls das aktuell verbundene Netz nach dem Neuschreiben fehlen wuerde
    // (dann ginge der Fernzugriff verloren!), die vorherige Konfig automatisch zuruecksichern.
    if(isset($active_essid) && $active_essid != "") {
        $exec .= "restore_wpa_conf_if_ssid_missing_b64 ".base64_encode($active_essid)."\n";
    }
    $exec .= "END\n";
    exec("sudo bash -c '". $exec . "'");
}

/*
* NEU: WLAN-Scan. Button "Netzwerke suchen" listet verfuegbare Netze auf.
* Ergebnis: $scannedNetworks[SSID] = staerkstes Signal (dBm). SSIDs mit Leerzeichen
* funktionieren, weil hier in PHP geparst wird (kein Shell-Wortsplitting).
*/
$scannedNetworks = array();
if(isset($_POST["scanWifi"])) {
    $scan_raw = shell_exec("sudo iw dev wlan0 scan 2>/dev/null");
    $cur_signal = -100;
    foreach(explode("\n", (string)$scan_raw) as $sline) {
        if(preg_match('/^\s*signal:\s*(-?[0-9.]+)/', $sline, $m)) {
            $cur_signal = floatval($m[1]);
        } elseif(preg_match('/^\s*SSID:\s?(.*)$/', $sline, $m)) {
            $ssid = rtrim($m[1], "\r");
            // leere/versteckte Netze ueberspringen
            if($ssid === "") { continue; }
            // je SSID nur das staerkste Signal behalten
            if(!isset($scannedNetworks[$ssid]) || $cur_signal > $scannedNetworks[$ssid]) {
                $scannedNetworks[$ssid] = $cur_signal;
            }
        }
    }
    arsort($scannedNetworks); // staerkstes Signal zuerst
}

/*
* get all configured wifis
*/
$network_confs_shell = shell_exec("sudo bash -c 'source ".$conf['scripts_abs']."/helperscripts/inc.networkHelper.sh && get_wireless_networks'");
// Neues Format: eine Zeile pro Netz "base64(ssid):base64(psk):prio" (base64 haelt Leerzeichen intakt).
$network_confs = explode("\n", trim($network_confs_shell));

$networks = array();
foreach($network_confs as $line){
    unset($temp_ssid);
    unset($temp_pass);
    unset($temp_prio);
	unset($temp_active);

    if(trim($line) == "") { continue; }
    $network_conf = explode(':',$line);
    $temp_ssid = base64_decode(trim($network_conf[0]));
    $temp_pass = isset($network_conf[1]) ? base64_decode(trim($network_conf[1])) : "";
    $temp_prio = isset($network_conf[2]) ? trim($network_conf[2]) : "0";
	$temp_active = isset($active_essid) && $temp_ssid == $active_essid;

    if(isset($temp_ssid) && $temp_ssid != "" && isset($temp_pass) && $temp_pass != "") {
		if(!isset($temp_prio) || !is_numeric($temp_prio)) {
			$temp_prio = 0;
		}
        $temp_entry = array($temp_ssid => [ $temp_pass, $temp_prio, $temp_active ]);
        # use different methods to have the same behavior: the data of the first appearance are kept, following will be ignored
        if($temp_active) {
            $networks = array_merge($temp_entry, $networks);
        } else {
            $networks = $networks + $temp_entry;
        }
    }
}
unset($temp_ssid);
unset($temp_pass);
unset($temp_prio);

?>

<form name='wifi' method='post' action='<?php print $_SERVER['PHP_SELF']; ?>'>
    <fieldset>
        <!-- Form Name -->
        <legend><?php print $lang['globalWifiNetwork']; ?></legend>
<?php
    if(isset($exec)) {
        print '
        <div class="alert alert-info">
        '.$lang['settingsWifiRestart'].'
        </div>';
    }
    if(isset($active_essid) && $active_essid != "") {
        print '
        <div class="alert alert-info">
        '.$lang['globalSSID'].': '.$active_essid.'
        </div>';
    }

    // NEU: versteckter Standard-Submit, damit Enter "Speichern" ausloest (nicht den Scan-Button,
    // der im DOM davor steht).
    print '<button type="submit" name="submitWifi" value="submit" style="display:none" tabindex="-1" aria-hidden="true"></button>';

    // NEU: Button "Netzwerke suchen" + Liste der gefundenen Netze (zum Anklicken).
    // WICHTIG: bewusst OHNE Bootstrap-Grid-Spalten (col-md-*). Die haben float:left und
    // wuerden - ohne umgebende .row/Clearfix - von der folgenden Netzwerkliste ueberdeckt
    // (Button war deshalb im HTML vorhanden, aber unsichtbar). Einfache Bloecke sind robust.
    $lblScan     = isset($lang['settingsWifiScanBtn'])   ? $lang['settingsWifiScanBtn']   : 'Netzwerke suchen';
    $lblFound    = isset($lang['settingsWifiScanFound']) ? $lang['settingsWifiScanFound'] : 'Gefundene Netzwerke (zum Auswählen anklicken):';
    $lblScanHelp = isset($lang['settingsWifiScanHelp'])  ? $lang['settingsWifiScanHelp']  : 'Netzwerk anklicken, dann unten das Passwort eingeben und speichern.';
    $lblScanNone = isset($lang['settingsWifiScanNone'])  ? $lang['settingsWifiScanNone']  : 'Keine Netzwerke gefunden.';
    print '
        <div style="margin-bottom:12px;">
            <button type="submit" name="scanWifi" value="scan" class="btn btn-info"><i class="fa fa-refresh"></i> '.$lblScan.'</button>
        </div>';
    if(isset($_POST["scanWifi"])) {
        if(!empty($scannedNetworks)) {
            print '<div style="margin-bottom:16px;"><p><strong>'.$lblFound.'</strong></p><div class="list-group">';
            foreach($scannedNetworks as $sSsid => $sSignal) {
                // dBm grob in Prozent: -50 dBm ~ 100%, -100 dBm ~ 0%
                $pct = max(0, min(100, intval(2 * ($sSignal + 100))));
                $safe = htmlspecialchars($sSsid, ENT_QUOTES);
                print '
                <button type="button" class="list-group-item" onclick="phonieboxSelectWifi(this.getAttribute(\'data-ssid\'));" data-ssid="'.$safe.'">
                    <span class="badge">'.$pct.' %</span>
                    <i class="fa fa-wifi"></i> '.htmlspecialchars($sSsid).'
                </button>';
            }
            print '</div><p class="help-block">'.$lblScanHelp.'</p></div>';
        } else {
            print '<div style="margin-bottom:12px;"><div class="alert alert-warning">'.$lblScanNone.'</div></div>';
        }
    }
?>
        <ul class="list-group">
<?php
    $network_index = 0;
    foreach ( $networks as $WIFIssid => $WIFIconf ) {
        $WIFIpass = $WIFIconf[0];
        $WIFIprio = $WIFIconf[1];
		$WIFIactive = $WIFIconf[2];
        $WIFIindex = $network_index++;
?>
            <li class="list-group-item">
                <div class="row">

                    <!-- Text input-->
                    <div class="form-group">
                        <label class="col-md-4 control-label" for="WIFIssid_<?php print $WIFIindex; ?>"><?php
                            if($WIFIactive) {
                                print $lang['globalSSID']."*";
                            } else {
                                print $lang['globalSSID'];
                            }
                        ?></label>
                        <div class="col-md-6">
                            <input value="<?php
								print $WIFIssid;
                            ?>" id="WIFIssid_<?php print $WIFIindex; ?>" name="WIFIssid_<?php print $WIFIindex; ?>" placeholder="<?php print $lang['settingsWifiSsidPlaceholder']; ?>" class="form-control input-md" type="text" <?php print $WIFIactive ? "readonly" : ""; ?>>
                            <span class="help-block"></span>
                        </div>
                    </div>

                    <!-- Text input-->
                    <div class="form-group">
                        <label class="col-md-4 control-label" for="WIFIpass_<?php print $WIFIindex; ?>"><?php print $lang['globalPassword']; ?></label>
                        <div class="col-md-6">
                            <input value="<?php
								print $WIFIpass;
                            ?>" id="WIFIpass_<?php print $WIFIindex; ?>" name="WIFIpass_<?php print $WIFIindex; ?>" placeholder="" class="form-control input-md" type="password" minlength="8" maxlength="63" <?php print $WIFIactive ? "readonly" : ""; ?>>
                            <span class="help-block"></span>
                        </div>
                    </div>

                    <!-- Text input-->
                    <div class="form-group">
                      <label class="col-md-4 control-label" for="WIFIprio_<?php print $WIFIindex; ?>"><?php print $lang['globalPriority']; ?></label>
                      <div class="col-md-6">
                          <input value="<?php
							  print $WIFIprio;
                          ?>" id="WIFIprio_<?php print $WIFIindex; ?>" name="WIFIprio_<?php print $WIFIindex; ?>" placeholder="" class="form-control input-md" type="number" min="0" max="100" <?php print $WIFIactive ? "readonly" : ""; ?>>
                          <span class="help-block"></span>
                      </div>
                    </div>
                </div>
            </li>
<?php
    }
?>
            <li class="list-group-item">
                <div class="row">
                    <!-- Text input-->
                    <div class="form-group">
                      <label class="col-md-4 control-label" for="WIFIssid_<?php print $network_index; ?>"><?php print $lang['globalSSID']; ?></label>
                      <div class="col-md-6">
                          <input value="" id="WIFIssid_<?php print $network_index; ?>" name="WIFIssid_<?php print $network_index; ?>" placeholder="<?php print $lang['settingsWifiSsidPlaceholder']; ?>" class="form-control input-md" type="text">
                          <span class="help-block"><?php print $lang['settingsWifiSsidHelp']; ?></span>
                      </div>
                    </div>

                    <!-- Text input-->
                    <div class="form-group">
                      <label class="col-md-4 control-label" for="WIFIpass_<?php print $network_index; ?>"><?php print $lang['globalPassword']; ?></label>
                      <div class="col-md-6">
                          <input value="" id="WIFIpass_<?php print $network_index; ?>" name="WIFIpass_<?php print $network_index; ?>" placeholder="" class="form-control input-md" type="password" minlength="8" maxlength="63">
                          <span class="help-block"><?php print $lang['settingsWifiPassHelp']; ?></span>
                      </div>
                    </div>

                    <!-- Text input-->
                    <div class="form-group">
                      <label class="col-md-4 control-label" for="WIFIprio_<?php print $network_index; ?>"><?php print $lang['globalPriority']; ?></label>
                      <div class="col-md-6">
                          <input value="0" id="WIFIprio_<?php print $network_index; ?>" name="WIFIprio_<?php print $network_index; ?>" placeholder="" class="form-control input-md" type="number" min="0" max="100">
                          <span class="help-block"><?php print $lang['settingsWifiPrioHelp']; ?></span>
                      </div>
                    </div>
                </div>
            </li>
        </ul>
    </fieldset>

    <!-- Button (Double) -->
    <div class="form-group">
        <label class="col-md-4 control-label" for="submit"></label>
        <div class="col-md-8">
            <button id="submitWifi" name="submitWifi" class="btn btn-success" value="submit"><?php print $lang['globalSubmit']; ?></button>
            <br clear='all'><br>
        </div>
    </div>

</form>

<script>
// NEU: Klick auf ein gescanntes Netzwerk fuellt das SSID-Feld des "neues Netzwerk"-Blocks
// (letzter, leerer Eintrag) und springt zum Passwort-Feld.
function phonieboxSelectWifi(ssid) {
    var idx = <?php print $network_index; ?>;
    var s = document.getElementById('WIFIssid_' + idx);
    var p = document.getElementById('WIFIpass_' + idx);
    if (s) { s.value = ssid; s.scrollIntoView({behavior:'smooth', block:'center'}); }
    if (p) { p.focus(); }
}
</script>
