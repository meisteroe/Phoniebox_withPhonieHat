<?php

include("inc.header.php");

/*******************************************
* START HTML
*******************************************/

html_bootstrap3_createHeader("en","System Info | Phoniebox",$conf['base_url']);

?>
<body>
  <div class="container">

<?php
include("inc.navigation.php");

// get System Information and parse into variables
$exec = "lsb_release -a";
if($debug == "true") { 
		print "Command: ".$exec; 
}  
exec($exec, $res);
$distributor = substr($res[0],strpos($res[0],":")+1,strlen($res[0])-strpos($res[0],":"));
$description = substr($res[1],strpos($res[1],":")+1,strlen($res[1])-strpos($res[1],":"));
$release = substr($res[2],strpos($res[2],":")+1,strlen($res[2])-strpos($res[2],":"));
$codename = substr($res[3],strpos($res[3],":")+1,strlen($res[3])-strpos($res[3],":"));
$rpi_temperature = explode("=", exec("sudo vcgencmd measure_temp"))[1];

// check RPis throttling state
function checkRpiThrottle() {
	$codes = array(
		0	=> "under-voltage detected",
		1	=> "arm frequency capped",
		2	=> "currently throttled",
		3	=> "soft temperature limit active",
		16	=> "under-voltage has occurred",
		17	=> "arm frequency capped has occurred",
		18	=> "throttling has occurred",
		19	=> "soft temperature limit has occurred"
	);

	$getThrottledResult = explode("0x", exec("sudo vcgencmd get_throttled"))[1];

	// code is zero => no issue
	if ($getThrottledResult == "0") return "OK";

	// analyse returned code
	$result = [];
	$codeHex = str_split($getThrottledResult);
	$codeBinary = "";
	foreach ($codeHex as $fourbits) {
		$codeBinary .= str_pad(base_convert($fourbits, 16, 2), 4, "0", STR_PAD_LEFT);
	}
	$codeBinary = array_reverse(str_split($codeBinary));
	foreach ($codeBinary as $bitNumber => $bitValue) {
		if ($bitValue) $result[] = $codes[$bitNumber];
	}
	return "WARNING: " . implode(", ", $result);
}
$rpi_throttle = checkRpiThrottle();

?>
<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title">
         <i class='mdi mdi-settings'></i> <?php print $lang['globalSystem']; ?> 
      </h4>
    </div><!-- /.panel-heading -->

    <div class="panel-body">
  
        <div class="row">	
          <label class="col-md-4 control-label" for=""><?php print $lang['infoOsDistrib']; ?></label> 
          <div class="col-md-6"><?php echo trim($distributor); ?></div>
        </div><!-- / row -->
        <div class="row">	
          <label class="col-md-4 control-label" for=""><?php print $lang['globalDescription']; ?></label> 
          <div class="col-md-6"><?php echo trim($description); ?></div>
		   </div><!-- / row -->

        <!-- Phoniebox-Softwareversion -->
        <div class="row">
          <label class="col-md-4 control-label" for="">Phoniebox-Software</label>
          <div class="col-md-6">
          <?php
            $pbVer  = @file_get_contents('../VERSION');
            $pbVer  = ($pbVer !== false && trim($pbVer) !== '') ? trim($pbVer) : 'unbekannt';
            $pbDate = @filemtime('../VERSION');
            echo '<strong>'.htmlspecialchars($pbVer).'</strong> &ndash; Custom HAT Edition';
            if ($pbDate) { echo '<br><small class="text-muted">Stand: '.date('d.m.Y', $pbDate).'</small>'; }
          ?>
          </div>
        </div><!-- / row -->

        <!-- Battery Status -->
        <?php
        $batteryFile = '/tmp/battery_status.json';
        if (file_exists($batteryFile)) {
            $battery = json_decode(file_get_contents($batteryFile), true);
            if ($battery && isset($battery['percent'])) {
                $percent = $battery['percent'];
                $voltage = $battery['voltage'];
                $status = $battery['status'];
                
                // Farbe je nach Status
                if ($percent > 80) {
                    $barColor = 'success';
                    $icon = '🔋';
                } elseif ($percent > 20) {
                    $barColor = 'info';
                    $icon = '🔋';
                } elseif ($percent > 10) {
                    $barColor = 'warning';
                    $icon = '⚡';
                } else {
                    $barColor = 'danger';
                    $icon = '⚠️';
                }
                
                echo '<div class="row" style="margin-bottom:15px;">';
                echo '<label class="col-md-4 control-label">Battery</label>';
                echo '<div class="col-md-6">';
                echo $icon . ' ' . $percent . '% (' . $voltage . 'V)';
                echo '<div class="progress" style="margin-top:5px; margin-bottom:0;">';
                echo '<div class="progress-bar progress-bar-' . $barColor . '" style="width:' . $percent . '%"></div>';
                echo '</div>';
                echo '</div>';
                echo '</div><!-- / row -->';
            }
        }
        ?> 
		<div class="row">		
          <label class="col-md-4 control-label" for=""><?php print $lang['globalRelease']; ?></label> 
          <div class="col-md-6"><?php echo trim($release); ?></div>
        </div><!-- / row -->
        <div class="row">	
          <label class="col-md-4 control-label" for=""><?php print $lang['infoOsCodename']; ?></label> 
          <div class="col-md-6"><?php echo trim($codename); ?></div>
        </div>
        <div class="row">
          <label class="col-md-4 control-label" for=""><?php print $lang['infoOsThrottle']; ?></label>
          <div class="col-md-6"><?php echo trim($rpi_throttle); ?></div>
        </div>     
        <div class="row">
          <label class="col-md-4 control-label" for=""><?php print $lang['infoOsTemperature']; ?></label>
          <div class="col-md-6"><?php echo trim($rpi_temperature); ?></div>
        </div>
	</div><!-- /.panel-body -->
  </div><!-- /.panel panel-default-->
</div><!-- /.panel-group -->

<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title">
         <i class='mdi mdi-settings'></i> Phoniebox Setup
      </h4>
    </div><!-- /.panel-heading -->

    <div class="panel-body">
  
        <div class="row">	
          <label class="col-md-4 control-label" for=""><?php print $lang['globalVersion']; ?></label> 
          <div class="col-md-6"><?php
            // create current version
            
            // get information for version number on current running system
            $exec = "cat ../settings/version-number";
            $VERSION_NO = exec($exec);
            $exec = "git --git-dir=../.git rev-parse --abbrev-ref HEAD";
            $USED_BRANCH = exec($exec);
            $exec = "git --git-dir=../.git  describe --always";
            $COMMIT_NO = exec($exec);
            $version = $VERSION_NO . " - " . $COMMIT_NO . " - " . $USED_BRANCH;
            // write version to file
            $exec = "echo ${version} > ../settings/version";
            exec($exec);
            // write new version number to global config file
            exec("sudo ".$conf['scripts_abs']."/inc.writeGlobalConfig.sh");
            exec("sudo chmod 777 ".$conf['settings_abs']."/global.conf");
            // and print the version on the info site
            echo $version; 

           ?></div>
        </div><!-- / row -->
        <div class="row">	
          <label class="col-md-4 control-label" for=""><?php print $lang['globalEdition']; ?></label> 
          <div class="col-md-6"><?php echo $lang[$edition]; ?></div>
        </div><!-- / row -->
		<div class="row">	
          <label class="col-md-4 control-label" for="">
		  <?php
		  if ($edition == "classic") {
			  print $lang['infoMPDStatus']."</label> 
		  <div id='mpdstatus'></div>";
		  } elseif ($edition == "plusSpotify") {
			  print $lang['infoMopidyStatus']."</label> 
		  <div id='mopidystatus'></div>";
		  }
		  ?>
		</div>
		<!-- / row -->
      
	</div><!-- /.panel-body -->
  </div><!-- /.panel panel-default-->
</div><!-- /.panel-group -->


<?php
if ($edition == "classic") {
	print "<script>
$(document).ready(function() {
    $('#mpdstatus').load('ajax.loadMPDStatus.php');
    var refreshId = setInterval(function() {
        $('#mpdstatus').load('ajax.loadMPDStatus.php?' + 1*new Date());
    }, 5000);
});

</script>";
} elseif ($edition == "plusSpotify") {
	print "<script>
$(document).ready(function() {
    $('#mopidystatus').load('ajax.loadMopidyStatus.php');
    var refreshId = setInterval(function() {
        $('#mopidystatus').load('ajax.loadMopidyStatus.php?' + 1*new Date());
    }, 5000);
});

</script>";
}
?>

<?php
// get the information of storage usage
$exec = "df -H -B K / ";
    if($debug == "true") { 
        print "Command: ".$exec; 
    } 
    $exploded = preg_split("/ +/", exec($exec));
    // all values are in MeBit
    $all = round(Trim(substr($exploded[1],0,Strpos($exploded[1],"K")))/1024, 2);
    $used = round(Trim(substr($exploded[2],0,Strpos($exploded[2],"K")))/1024, 2);
    $free = round(Trim(substr($exploded[3],0,Strpos($exploded[3],"K")))/1024, 2);
?>

<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title">
        <i class='mdi mdi-server'></i> <?php print $lang['globalStorage']; ?> <small>(<?php echo round($all/1024,2); ?> GB)</small>
      </h4>
    </div><!-- /.panel-heading -->

		<div class="panel-body">

		<?php	
			// get information about the shared folder to calculate media size
			$exec = "du -H -B K -s ".$conf['base_path']."/shared/";
			if($debug == "true") { 
					print "Command: ".$exec; 
			}  
			$res = exec($exec);
			$exploded = explode("/", $res);
			$Media = round(Trim(substr($exploded[0],0,Strpos($exploded[0],"K")))/1024, 2);
			// make some percentage calculation
			$percent = 100/$all;
			$reserved = $all - $used - $free;
			$system = $used - $Media;
		?>

			<h5><?php print $lang['infoStorageUsed']; ?> <small>(<?php echo round($free/1024,2); ?> GB free)</small></h5>
			<div class="row">
				<div class="col-xs-12">
					<div class="progress">
						<div class="progress-bar progress-bar-warning" role="progressbar" title="Reserved: <?php echo round($reserved*$percent, 2); ?>%" style="width:<?php echo round($reserved*$percent, 2); ?>%">Res.</div>
						<div class="progress-bar progress-bar-danger" role="progressbar" title="System: <?php echo round($system*$percent, 2); ?>%" style="width:<?php echo round($system*$percent, 2); ?>%">Sys.</div>
						<div class="progress-bar progress-bar progress-bar-info" role="progressbar" title="Media: <?php echo round($Media*$percent, 2); ?>%" style="width:<?php echo round($Media*$percent, 2); ?>%">Media</div>
						<div class="progress-bar progress-bar-success" role="progressbar" title="Free: <?php echo round($free*$percent, 2); ?>%" style="width:<?php echo round($free*$percent, 2); ?>%">Free</div>
					</div><!-- / .progress -->
				</div><!-- / .col-xs-12 -->
			</div><!-- / .row -->
			</div><!-- /.panel-body -->
  </div><!-- /.panel -->
</div><!-- /.panel-group -->

<?php
/* === Dokumentation: Ordner ../Doku rekursiv auflisten (Unterordner aufklappbar) === */
$dokuDir = __DIR__ . '/../Doku';

if (!function_exists('renderDokuNode')) {
  function renderDokuNode($absDir, $relDir) {
    $allowed  = array('pdf','html','htm','md','txt','png','jpg','jpeg','gif','svg','stl','3mf','obj','step','stp','zip');
    $download = array('stl','3mf','obj','step','stp','zip');
    $entries = glob($absDir . '/*');
    if ($entries === false) { return; }
    usort($entries, 'strcasecmp');
    $files = array(); $dirs = array();
    foreach ($entries as $e) {
      if (is_dir($e)) { $dirs[] = $e; }
      elseif (is_file($e)) { $files[] = $e; }
    }
    // Unterordner zuerst (aufklappbar), danach die Dateien
    foreach ($dirs as $d) {
      $dname  = basename($d);
      $relSub = ($relDir === '' ? '' : $relDir . '/') . $dname;
      $cid    = 'doku_' . substr(md5($relSub), 0, 10);
      $cnt    = count((array)glob($d . '/*'));
      print '        <a href="#' . $cid . '" data-toggle="collapse" class="list-group-item" style="font-weight:600"><i class="mdi mdi-folder-outline"></i> ' . htmlspecialchars($dname) . ' <span class="badge">' . $cnt . '</span></a>' . "\n";
      print '        <div class="collapse" id="' . $cid . '" style="padding-left:20px;border-left:2px solid #eee;margin:2px 0 2px 6px">' . "\n";
      renderDokuNode($d, $relSub);
      print '        </div>' . "\n";
    }
    foreach ($files as $f) {
      $name = basename($f);
      $ext  = strtolower(pathinfo($name, PATHINFO_EXTENSION));
      if (!in_array($ext, $allowed)) { continue; }
      $title = pathinfo($name, PATHINFO_FILENAME);
      $rel   = ($relDir === '' ? '' : $relDir . '/') . $name;
      $dl    = in_array($ext, $download) ? '&dl=1' : '';
      if ($ext === 'pdf') { $icon = 'mdi-file-pdf'; }
      elseif (in_array($ext, array('stl','3mf','obj','step','stp'))) { $icon = 'mdi-cube-outline'; }
      elseif (in_array($ext, array('png','jpg','jpeg','gif','svg'))) { $icon = 'mdi-file-image'; }
      elseif ($ext === 'zip') { $icon = 'mdi-folder-zip-outline'; }
      else { $icon = 'mdi-file-document-outline'; }
      print '        <a href="docViewer.php?doc=' . urlencode($rel) . $dl . '" target="_blank" class="list-group-item"><i class="mdi ' . $icon . '"></i> ' . htmlspecialchars($title) . ' <small class="text-muted">(' . strtoupper($ext) . ')</small></a>' . "\n";
    }
  }
}
?>
<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title">
        <i class='mdi mdi-book-open-page-variant'></i> <?php print isset($lang['globalDocumentation']) ? $lang['globalDocumentation'] : 'Dokumentation'; ?>
      </h4>
    </div><!-- /.panel-heading -->
    <div class="panel-body">
      <div class="list-group">
<?php
        if (is_dir($dokuDir)) {
            renderDokuNode($dokuDir, '');
        } else {
            print '        <p class="text-muted" style="padding:10px;">Ordner <code>Doku/</code> nicht gefunden.</p>' . "\n";
        }
?>
      </div>
    </div><!-- /.panel-body -->
  </div><!-- /.panel panel-default-->
</div><!-- /.panel-group -->

<!-- Spende / Unterstuetzung -->
<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title">
        <i class='mdi mdi-heart-outline'></i> Spende
      </h4>
    </div><!-- /.panel-heading -->
    <div class="panel-body">
      <p>Diese Phoniebox wurde mit viel Liebe von <strong>Adrian M&ouml;ller</strong> entwickelt und gebaut.
      Wenn sie dich und deine Familie mit Freude erf&uuml;llt und du das Projekt unterst&uuml;tzen m&ouml;chtest,
      freue ich mich sehr &uuml;ber eine kleine Spende &ndash; ganz so, wie es dir gef&auml;llt. Vielen Dank! &#128153;</p>
      <a href="https://paypal.me/MeisterAdrian" target="_blank" rel="noopener" class="btn btn-info">
        <i class="mdi mdi-gift-outline"></i> Per PayPal spenden
      </a>
    </div><!-- /.panel-body -->
  </div><!-- /.panel panel-default-->
</div><!-- /.panel-group -->

<?php
include("inc.addSystemInfo.php");
?>

<!-- Live-Log (journald, liegt im RAM -> keine SD-Last) -->

<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title">
        <i class='mdi mdi-console'></i> Live-Log (System &amp; Dienste)
      </h4>
    </div><!-- /.panel-heading -->
    <div class="panel-body">

      <div class="form-inline" style="margin-bottom:10px;">
        <select id="liveLogSource" class="form-control" style="margin:2px;">
          <option value="system">Gesamtes System</option>
          <option value="pn532">RFID-Reader (pn532)</option>
          <option value="gpio">Tasten / GPIO</option>
          <option value="mpd">Player (MPD)</option>
          <option value="led">LED-Steuerung</option>
          <option value="battery">Akku-Monitor</option>
          <option value="mpd-autoupdate">MPD Auto-Update</option>
          <option value="idle">Auto-Abschaltung</option>
          <option value="startup">Startskripte</option>
        </select>
        <select id="liveLogLines" class="form-control" style="margin:2px;">
          <option value="50">50 Zeilen</option>
          <option value="100" selected>100 Zeilen</option>
          <option value="200">200 Zeilen</option>
          <option value="500">500 Zeilen</option>
        </select>
        <label class="checkbox-inline" style="margin:2px 8px;">
          <input type="checkbox" id="liveLogLive" checked> Live (3s)
        </label>
        <a href="#" id="liveLogRefresh" class="btn btn-info btn-sm" style="margin:2px;">
          <i class="mdi mdi-refresh"></i> Aktualisieren
        </a>
      </div>

      <pre id="liveLogOut" style="height:380px; overflow:auto; background:#1e1e1e; color:#d4d4d4; font-family:monospace; font-size:12px; white-space:pre-wrap; word-break:break-word; padding:10px; border-radius:4px; margin-bottom:6px;">Lade...</pre>
      <small class="text-muted"><span id="liveLogStamp">&nbsp;</span> &middot; liest aus dem RAM (journald volatile) &ndash; belastet die SD-Karte nicht.</small>

    </div><!-- /.panel-body -->
  </div><!-- /.panel -->
</div><!-- /.panel-group -->

<script>
(function(){
  var pre    = document.getElementById('liveLogOut');
  var src    = document.getElementById('liveLogSource');
  var lines  = document.getElementById('liveLogLines');
  var live   = document.getElementById('liveLogLive');
  var stamp  = document.getElementById('liveLogStamp');
  var timer  = null;
  var first  = true;

  function load(){
    var url = 'api/log_api.php?source=' + encodeURIComponent(src.value)
            + '&lines=' + encodeURIComponent(lines.value);
    fetch(url, {cache:'no-store'})
      .then(function(r){ return r.text(); })
      .then(function(t){
        var atBottom = first || (pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 20);
        pre.textContent = t;
        if (atBottom) { pre.scrollTop = pre.scrollHeight; }
        first = false;
        var d = new Date();
        stamp.textContent = 'Aktualisiert ' + d.toLocaleTimeString();
      })
      .catch(function(){ stamp.textContent = 'Fehler beim Laden'; });
  }

  function apply(){
    if (timer) { clearInterval(timer); timer = null; }
    if (live.checked) { timer = setInterval(load, 3000); }
  }

  src.addEventListener('change', function(){ first = true; load(); });
  lines.addEventListener('change', function(){ first = true; load(); });
  live.addEventListener('change', apply);
  document.getElementById('liveLogRefresh').addEventListener('click', function(e){ e.preventDefault(); load(); });

  load();
  apply();
})();
</script>

<!-- debug.log -->

<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title">
        <i class='mdi mdi-text'></i> <?php print $lang['infoDebugLogTail']; ?>
        <br><br>
        <a href="systemInfo.php?DebugLogClear=true" class="btn btn-info"><?php print $lang['infoDebugLogClear']; ?></a>
      </h4>
    </div><!-- /.panel-heading -->

    <div class="panel-body">
    
        <?php
        $res = tailShell("../logs/debug.log", 40);
        print "<pre>\n".$res."\n</pre>";
        ?>
    
	</div><!-- /.panel-body -->
  </div><!-- /.panel -->
</div><!-- /.panel-group -->

</div><!-- /.container -->

</body>
</html>
