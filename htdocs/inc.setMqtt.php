<?php
/*
 * inc.setMqtt.php — Smart Home (MQTT / Home Assistant) in der WebUI einstellen.
 * Speichert settings/mqtt_client.json + settings/Function_Cards ueber
 * scripts/custom_mqtt.sh (per sudo) und schaltet den Dienst an/aus.
 * Das Passwort wird nie an den Browser zurueckgegeben.
 */
$mqttScript = "/usr/bin/sudo ".$conf['scripts_abs']."/custom_mqtt.sh";
$mqttMsg = "";

function mqttMsgBox($out) {
    $cls = (strpos($out, 'FEHLER') === 0) ? 'danger' : 'success';
    return "<div class='alert alert-".$cls."'>".nl2br(htmlspecialchars($out))."</div>";
}

/* --- Python-Pakete installieren --- */
if (isset($_POST['mqttInstallDeps'])) {
    $mqttMsg .= mqttMsgBox(trim(shell_exec($mqttScript." deps 2>&1")));
}

/* --- Einstellungen speichern --- */
if (isset($_POST['mqttSubmit'])) {
    $errors = array();
    $host = trim($_POST['mqttHostname'] ?? '');
    $port = intval($_POST['mqttPort'] ?? 1883);
    $user = trim($_POST['mqttUsername'] ?? '');
    $pass = (string)($_POST['mqttPassword'] ?? '');
    $topic = trim($_POST['mqttBaseTopic'] ?? '');
    $enabled = (($_POST['mqttEnabled'] ?? 'off') === 'on') ? 'on' : 'off';

    if ($host !== '' && !preg_match('/^[A-Za-z0-9.-]{1,253}$/', $host)) $errors[] = "Ung&uuml;ltiger Server-Name.";
    if ($port < 1 || $port > 65535) $errors[] = "Ung&uuml;ltiger Port.";
    if (strlen($user) > 128 || strlen($pass) > 256) $errors[] = "Benutzer oder Passwort zu lang.";
    if ($topic !== '' && !preg_match('/^[A-Za-z0-9_-]{1,64}$/', $topic)) $errors[] = "Topic: nur a&ndash;z, 0&ndash;9, _ und -.";
    if ($enabled === 'on' && $host === '') $errors[] = "Zum Einschalten bitte einen Server angeben.";

    $cur = json_decode(shell_exec($mqttScript." getconf 2>/dev/null"), true) ?: array();
    $allowedPlaying = array(5, 10, 30, 60);
    $allowedIdle = array(30, 60, 300, 900);
    $new = array(
        "mqttHostname" => $host,
        "mqttPort" => $port,
        "mqttUsername" => $user,
        "mqttPassword" => $pass,  // leer = bisheriges behalten (custom_mqtt.sh)
        "mqttBaseTopic" => ($topic === '') ? "auto" : $topic,
        "mqttClientId" => ($topic === '') ? "auto" : $topic,
        // Zertifikate gibt es in der WebUI nicht; vorhandene Werte bleiben erhalten
        "mqttCA" => $cur['mqttCA'] ?? "",
        "mqttCert" => $cur['mqttCert'] ?? "",
        "mqttKey" => $cur['mqttKey'] ?? "",
        "homeAssistantDiscovery" => isset($_POST['homeAssistantDiscovery']),
        "sendStatus" => isset($_POST['sendStatus']),
        "refreshIntervalPlaying" => in_array(intval($_POST['refreshIntervalPlaying'] ?? 10), $allowedPlaying) ? intval($_POST['refreshIntervalPlaying']) : 10,
        "refreshIntervalIdle" => in_array(intval($_POST['refreshIntervalIdle'] ?? 60), $allowedIdle) ? intval($_POST['refreshIntervalIdle']) : 60,
        "acceptCommands" => isset($_POST['acceptCommands']),
        "sendCards" => in_array($_POST['sendCards'] ?? 'all', array('all', 'function', 'none')) ? $_POST['sendCards'] : 'all',
        "sendButtons" => isset($_POST['sendButtons']),
    );

    if (count($errors) > 0) {
        $mqttMsg .= "<div class='alert alert-danger'>".implode("<br>", $errors)."</div>";
    } else {
        // Funktionskarten-Liste
        $tmpCards = tempnam(sys_get_temp_dir(), 'fcards');
        file_put_contents($tmpCards, str_replace("\r", "", (string)($_POST['functionCards'] ?? '')));
        $mqttMsg .= mqttMsgBox(trim(shell_exec($mqttScript." functioncards ".escapeshellarg($tmpCards)." 2>&1")));
        // Einstellungen + Dienst
        $tmp = tempnam(sys_get_temp_dir(), 'mqtt');
        file_put_contents($tmp, json_encode($new));
        chmod($tmp, 0600);
        $mqttMsg .= mqttMsgBox(trim(shell_exec($mqttScript." apply ".escapeshellarg($tmp)." ".$enabled." 2>&1")));
    }
}

/* --- aktuellen Stand lesen --- */
$mqttStatus = json_decode(shell_exec($mqttScript." status 2>/dev/null"), true) ?: array();
$mqttConf = json_decode(shell_exec($mqttScript." getconf 2>/dev/null"), true) ?: array();
$mqttOn = (($mqttStatus['enabled'] ?? '') === 'enabled');
$v = function($key, $default = '') use ($mqttConf) {
    return htmlspecialchars((string)($mqttConf[$key] ?? $default));
};
$chk = function($key, $default) use ($mqttConf) {
    return (($mqttConf[$key] ?? $default) ? ' checked' : '');
};
$sel = function($key, $val, $default) use ($mqttConf) {
    return ((string)($mqttConf[$key] ?? $default) === (string)$val) ? ' selected' : '';
};
$topicVal = (($mqttConf['mqttBaseTopic'] ?? 'auto') === 'auto') ? '' : $mqttConf['mqttBaseTopic'];
$curHostname = trim(shell_exec("hostname"));
$functionCards = @file_get_contents($conf['settings_abs'].'/Function_Cards');
$latestCard = trim(@file_get_contents($conf['settings_abs'].'/Latest_RFID'));
?>
<style>
  #mqtt .mqtt-state { font-size: 1.1em; margin-bottom: 1em; }
  #mqtt .mqtt-dot { display:inline-block; width:.8em; height:.8em; border-radius:50%; margin-right:.4em; vertical-align:middle; }
  #mqtt .mqtt-hint { color:#777; font-size:.9em; margin:.2em 0 0 1.6em; }
  #mqtt .checkbox label { font-weight:600; }
  #mqtt fieldset { margin-bottom: 1.2em; }
  #mqtt legend { font-size: 1.1em; margin-bottom: .6em; }
</style>

<div id="mqtt">
<?php echo $mqttMsg; ?>

  <div class="mqtt-state" id="mqttState">
    <span class="mqtt-dot" style="background:#999"></span> Status wird geladen &hellip;
  </div>

<?php if (empty($mqttStatus['deps'])) { ?>
  <div class="alert alert-warning">
    Die ben&ouml;tigten Python-Pakete (paho-mqtt, inotify) fehlen noch. Die Installation dauert etwa eine Minute und braucht Internet.
    <form method="post" action="<?php print $_SERVER['PHP_SELF']; ?>#mqttAnchor" style="margin-top:.5em;">
      <button class="btn btn-warning" name="mqttInstallDeps" value="1"><i class="mdi mdi-download"></i> Pakete installieren</button>
    </form>
  </div>
<?php } ?>

  <form method="post" action="<?php print $_SERVER['PHP_SELF']; ?>#mqttAnchor" autocomplete="off">

    <fieldset>
      <legend>Dienst</legend>
      <div class="radio"><label>
        <input type="radio" name="mqttEnabled" value="off"<?php echo $mqttOn ? '' : ' checked'; ?>>
        <strong>Aus</strong> &ndash; kein Hintergrunddienst, kein Akkuverbrauch
      </label></div>
      <div class="radio"><label>
        <input type="radio" name="mqttEnabled" value="on"<?php echo $mqttOn ? ' checked' : ''; ?>>
        <strong>An</strong> &ndash; Phoniebox mit Smart Home (z.&nbsp;B. Home Assistant) verbinden
      </label></div>
    </fieldset>

    <fieldset>
      <legend>Verbindung</legend>
      <div class="row">
        <div class="col-md-6 form-group">
          <label for="mqttHostname">Server (MQTT-Broker)</label>
          <input type="text" class="form-control" id="mqttHostname" name="mqttHostname" value="<?php echo $v('mqttHostname'); ?>" placeholder="homeassistant.local">
        </div>
        <div class="col-md-2 form-group">
          <label for="mqttPort">Port</label>
          <input type="number" class="form-control" id="mqttPort" name="mqttPort" value="<?php echo $v('mqttPort', 1883); ?>" min="1" max="65535">
        </div>
        <div class="col-md-4 form-group">
          <label for="mqttBaseTopic">Name im Smart Home</label>
          <input type="text" class="form-control" id="mqttBaseTopic" name="mqttBaseTopic" value="<?php echo htmlspecialchars($topicVal); ?>" placeholder="<?php echo htmlspecialchars($curHostname); ?> (Ger&auml;tename)">
        </div>
      </div>
      <div class="row">
        <div class="col-md-6 form-group">
          <label for="mqttUsername">Benutzer</label>
          <input type="text" class="form-control" id="mqttUsername" name="mqttUsername" value="<?php echo $v('mqttUsername'); ?>" placeholder="phoniebox">
        </div>
        <div class="col-md-6 form-group">
          <label for="mqttPassword">Passwort</label>
          <input type="password" class="form-control" id="mqttPassword" name="mqttPassword" value="" autocomplete="new-password"
                 placeholder="<?php echo !empty($mqttConf['hasPassword']) ? '&bull;&bull;&bull;&bull;&bull;&bull; (gespeichert &ndash; leer lassen = behalten)' : 'Passwort'; ?>">
        </div>
      </div>
      <p class="text-muted">Home Assistant: Add-on <em>Mosquitto broker</em> installieren und unter Einstellungen &rarr; Personen einen Benutzer (z.&nbsp;B. <code>phoniebox</code>) anlegen.</p>
    </fieldset>

    <fieldset>
      <legend>Was soll gesendet werden?</legend>

      <div class="checkbox"><label><input type="checkbox" name="homeAssistantDiscovery"<?php echo $chk('homeAssistantDiscovery', true); ?>>
        Home Assistant automatisch einrichten</label>
        <div class="mqtt-hint">Die Box erscheint in Home Assistant als Ger&auml;t mit allen Anzeigen und Kn&ouml;pfen.</div></div>

      <div class="form-group" style="margin-top:1em;">
        <label for="sendCards">Karten melden</label>
        <select class="form-control" id="sendCards" name="sendCards" style="max-width:28em;">
          <option value="all"<?php echo $sel('sendCards', 'all', 'all'); ?>>Alle Karten</option>
          <option value="function"<?php echo $sel('sendCards', 'function', 'all'); ?>>Nur Funktionskarten (Liste unten)</option>
          <option value="none"<?php echo $sel('sendCards', 'none', 'all'); ?>>Keine Karten</option>
        </select>
        <div class="mqtt-hint" style="margin-left:0;">In Home Assistant: Automation mit Ausl&ouml;ser <em>Tag gescannt</em>. Kostet keinen Akku, nur ein Ereignis pro Karte.</div>
      </div>

      <div class="checkbox"><label><input type="checkbox" name="sendButtons"<?php echo $chk('sendButtons', false); ?>>
        Tastendr&uuml;cke melden</label>
        <div class="mqtt-hint">Jede Taste wird in Home Assistant als Ausl&ouml;ser &bdquo;Taste gedr&uuml;ckt&ldquo; angeboten. Kostet keinen Akku.</div></div>

      <div class="checkbox"><label><input type="checkbox" name="acceptCommands"<?php echo $chk('acceptCommands', true); ?>>
        Steuerung aus dem Smart Home erlauben</label>
        <div class="mqtt-hint">Play/Pause, Lautst&auml;rke, Sleep-Timer, Herunterfahren &hellip;</div></div>

      <div class="checkbox"><label><input type="checkbox" id="sendStatus" name="sendStatus"<?php echo $chk('sendStatus', true); ?>>
        Status senden (Titel, Lautst&auml;rke, Timer, Temperatur)</label>
        <div class="mqtt-hint">Der einzige Punkt, der regelm&auml;&szlig;ig Rechenzeit braucht. Seltener = sparsamer.</div>
        <div class="row" style="margin:.6em 0 0 1.2em;">
          <div class="col-sm-6 form-group">
            <label for="refreshIntervalPlaying" style="font-weight:normal">alle &hellip; bei laufender Musik</label>
            <select class="form-control" id="refreshIntervalPlaying" name="refreshIntervalPlaying">
<?php foreach (array(5 => "5 Sekunden", 10 => "10 Sekunden (empfohlen)", 30 => "30 Sekunden", 60 => "1 Minute") as $k => $t) {
    echo "              <option value='".$k."'".$sel('refreshIntervalPlaying', $k, 10).">".$t."</option>\n"; } ?>
            </select>
          </div>
          <div class="col-sm-6 form-group">
            <label for="refreshIntervalIdle" style="font-weight:normal">alle &hellip; ohne Musik</label>
            <select class="form-control" id="refreshIntervalIdle" name="refreshIntervalIdle">
<?php foreach (array(30 => "30 Sekunden", 60 => "1 Minute (empfohlen)", 300 => "5 Minuten", 900 => "15 Minuten") as $k => $t) {
    echo "              <option value='".$k."'".$sel('refreshIntervalIdle', $k, 60).">".$t."</option>\n"; } ?>
            </select>
          </div>
        </div>
      </div>
    </fieldset>

    <fieldset>
      <legend>Funktionskarten</legend>
      <p class="text-muted">Funktionskarten starten keine Musik und stoppen sie nicht. Sie werden auf beiden Lesern erkannt &ndash; auch wenn auf dem anderen eine Musikkarte liegt &ndash; und nur ans Smart Home gemeldet (z.&nbsp;B. &bdquo;Licht-Farbe wechseln&ldquo;). Eine Karten-ID pro Zeile, Text nach <code>#</code> ist ein Kommentar.</p>
      <textarea class="form-control" id="functionCards" name="functionCards" rows="5" style="font-family:monospace" placeholder="E64634E6   # Kinderzimmer Licht"><?php echo htmlspecialchars((string)$functionCards); ?></textarea>
<?php if ($latestCard !== '') { ?>
      <p style="margin-top:.5em;">Zuletzt gelesene Karte: <code><?php echo htmlspecialchars($latestCard); ?></code>
        <button type="button" class="btn btn-default btn-xs" onclick="mqttAddCard('<?php echo htmlspecialchars($latestCard, ENT_QUOTES); ?>')"><i class="mdi mdi-plus"></i> als Funktionskarte &uuml;bernehmen</button></p>
<?php } ?>
    </fieldset>

    <button type="submit" class="btn btn-success" name="mqttSubmit" value="1"><i class="mdi mdi-content-save"></i> Speichern</button>
  </form>
</div>

<script>
function mqttAddCard(id) {
  var ta = document.getElementById('functionCards');
  if (ta.value.toUpperCase().indexOf(id.toUpperCase()) !== -1) { return; }
  ta.value = ta.value.replace(/\s*$/, '') + (ta.value.trim() ? '\n' : '') + id + '   # ';
  ta.focus();
}
(function () {
  var cb = document.getElementById('sendStatus');
  function toggle() {
    ['refreshIntervalPlaying', 'refreshIntervalIdle'].forEach(function (id) {
      document.getElementById(id).disabled = !cb.checked;
    });
  }
  cb.addEventListener('change', toggle); toggle();

  var box = document.getElementById('mqttState'), tries = 0;
  function show(s) {
    var c = s.connection || {}, color = '#999', text;
    if (s.enabled !== 'enabled' && s.active !== 'active') {
      text = '<strong>Aus</strong> &ndash; kein Hintergrunddienst aktiv.';
    } else if (c.state === 'connected') {
      color = '#3c763d'; text = '<strong>Verbunden</strong> mit ' + esc(c.host) + ' als <code>' + esc(c.topic) + '</code>';
    } else if (c.state === 'error') {
      color = '#a94442'; text = '<strong>Fehler:</strong> ' + esc(c.detail);
    } else if (s.active !== 'active') {
      color = '#a94442'; text = '<strong>Dienst l&auml;uft nicht</strong> (' + esc(s.active) + ')';
    } else {
      color = '#8a6d3b'; text = '<strong>Verbinde &hellip;</strong> ' + esc(c.detail || c.host || '');
    }
    box.innerHTML = '<span class="mqtt-dot" style="background:' + color + '"></span>' + text;
    return c.state === 'connected' || c.state === 'error' || s.active !== 'active';
  }
  function esc(t) { var d = document.createElement('div'); d.textContent = t || ''; return d.innerHTML; }
  function poll() {
    fetch('ajax.mqttStatus.php', {cache: 'no-store'}).then(function (r) { return r.json(); }).then(function (s) {
      var final = show(s);
      if (!final && ++tries < 15) { setTimeout(poll, 2000); }
    }).catch(function () {});
  }
  poll();
})();
</script>
