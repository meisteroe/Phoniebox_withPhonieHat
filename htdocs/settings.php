<?php

include("inc.header.php");

/*******************************************
* START HTML
*******************************************/

html_bootstrap3_createHeader("en","Settings | Phoniebox",$conf['base_url']);

?>
<body>
  <div class="container">

<?php
include("inc.navigation.php");

if($debug == "true") {
    print "<pre>";
    print "_POST:\n";
    print_r($_POST);
    print "</pre>";
}

?>

<div class="row">
  <div class="col-lg-12">
  <strong><?php print $lang['globalJumpTo']; ?>:</strong>
        <a href="#RFID" class="xbtn xbtn-default ">
        <i class='mdi mdi-cards-outline'></i> <?php print $lang['globalRFIDCards']; ?>
        </a> |
        <a href="#hostname" class="xbtn xbtn-default ">
        <i class='mdi mdi-rename-box'></i> Ger&auml;tename
        </a> |
        <a href="#backup" class="xbtn xbtn-default ">
        <i class='mdi mdi-content-save'></i> Sicherung
        </a> |
        <a href="#update" class="xbtn xbtn-default ">
        <i class='mdi mdi-cloud-download'></i> Update
        </a> |
        <a href="#contribute" class="xbtn xbtn-default ">
        <i class='mdi mdi-source-pull'></i> Beitragen
        </a> |
        <a href="#language" class="xbtn xbtn-default ">
        <i class='mdi mdi-emoticon'></i> <?php print $lang['globalLanguageSettings']; ?>
        </a> |
        <a href="#volume" class="xbtn xbtn-default ">
        <i class='mdi mdi-volume-high'></i> <?php print $lang['globalVolumeSettings']; ?>
        </a> |
        <a href="#autoShutdown" class="xbtn xbtn-default ">
        <i class='mdi mdi-clock-end'></i> <?php print $lang['globalIdleShutdown']." / ".$lang['globalSleepTimer']; ?>
        </a> |
        <a href="#wifi" class="xbtn xbtn-default ">
        <i class='mdi mdi-wifi'></i> <?php print $lang['globalWifiSettings']; ?>
        </a> |
        <!--a href="#wlanIpEmail" class="xbtn xbtn-default ">
        <i class='mdi mdi-wifi'></i> <?php print $lang['settingsWlanSendNav']; ?>
        </a>  |-->
        <a href="#wlanIpRead" class="xbtn xbtn-default ">
        <i class='mdi mdi-wifi'></i> <?php print $lang['settingsWlanReadNav']; ?>
        </a>  |
        <a href="#webInterface" class="xbtn xbtn-default ">
        <i class='mdi mdi-cards-outline'></i> <?php print $lang['settingsWebInterface']; ?>
        </a>  |
        <a href="#externalInterfaces" class="xbtn xbtn-default ">
        <i class='mdi mdi-usb'></i> <?php print $lang['globalExternalInterfaces']; ?>
        </a>  |
        <a href="#secondSwipe" class="xbtn xbtn-default ">
        <i class='mdi mdi-cards-outline'></i> <?php print $lang['settingsSecondSwipe']; ?>
        </a> |
        <a href="#DebugLogSettings" class="xbtn xbtn-default ">
        <i class='mdi mdi-text'></i> <?php print $lang['infoDebugLogSettings']; ?>
        </a>

  </div>
</div>
        <br/>
<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title"><a name="RFID"></a>
         <i class='mdi mdi-cards-outline'></i> <?php print $lang['indexManageFilesChips']; ?>
      </h4>
    </div><!-- /.panel-heading -->

      <div class="panel-body">
        <div class="row">
          <div class="col-lg-12">
                <a href="cardRegisterNew.php" class="btn btn-primary btn">
                <i class='mdi mdi-cards-outline'></i> <?php print $lang['globalRegisterCard']; ?>
                </a>
          </div><!-- / .col-lg-12 -->
        </div><!-- /.row -->
      </div><!-- /.panel-body -->

    </div><!-- /.panel -->
</div><!-- /.panel-group -->

<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title"><a name="hostname"></a>
         <i class='mdi mdi-rename-box'></i> Ger&auml;tename
      </h4>
    </div><!-- /.panel-heading -->
    <div class="panel-body">
      <div class="row">
<?php include("inc.setHostname.php"); ?>
      </div><!-- /.row -->
    </div><!-- /.panel-body -->
  </div><!-- /.panel -->
</div><!-- /.panel-group -->

<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title"><a name="backup"></a>
         <i class='mdi mdi-content-save'></i> Sicherung &amp; Wiederherstellung
      </h4>
    </div><!-- /.panel-heading -->
    <div class="panel-body">
      <p class="text-muted">
        Sichert <strong>Einstellungen</strong>, <strong>LED-Konfiguration</strong> und
        <strong>Karten-Zuordnungen</strong> in eine Datei (ohne Medien und ohne WLAN-Zugangsdaten).
        Ideal, um eine Box zu duplizieren oder vor &Auml;nderungen zu sichern.
      </p>
      <div class="row">
        <div class="col-md-6" style="margin-bottom:10px;">
          <h4>Sicherung herunterladen</h4>
          <a href="api/backup_export.php" class="btn btn-primary">
            <i class="mdi mdi-download"></i> Konfiguration sichern
          </a>
        </div>
        <div class="col-md-6">
          <h4>Sicherung wiederherstellen</h4>
          <form method="post" action="api/backup_import.php" enctype="multipart/form-data" target="_blank"
                onsubmit="return confirm('Aktuelle Einstellungen, LED-Konfiguration und Karten-Zuordnungen werden ueberschrieben (vorher wird automatisch eine Sicherheitskopie angelegt). Fortfahren?');">
            <div class="input-group">
              <input type="file" name="backupfile" accept=".gz,.tar.gz,application/gzip" class="form-control" required>
              <span class="input-group-btn">
                <input type="submit" class="btn btn-warning" value="Wiederherstellen">
              </span>
            </div>
          </form>
        </div>
      </div>
    </div><!-- /.panel-body -->
  </div><!-- /.panel -->
</div><!-- /.panel-group -->

<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title"><a name="update"></a>
        <i class="mdi mdi-cloud-download"></i> Software-Update
      </h4>
    </div><!-- /.panel-heading -->
    <div class="panel-body">
      <p class="text-muted">
        Holt Verbesserungen aus deinem GitHub-Repo. Deine Einstellungen, LED-Konfiguration und
        Karten bleiben unber&uuml;hrt (vorher wird automatisch gesichert). Es wird nur &bdquo;vorgespult&ldquo;,
        nie etwas erzwungen.
      </p>
      <a href="#" id="updCheck" class="btn btn-info"><i class="mdi mdi-magnify"></i> Nach Updates suchen</a>
      <a href="#" id="updApply" class="btn btn-warning" style="display:none;"><i class="mdi mdi-cloud-download"></i> Jetzt aktualisieren</a>
      <pre id="updOut" style="display:none; margin-top:10px; white-space:pre-wrap; word-break:break-word;"></pre>
    </div><!-- /.panel-body -->
  </div><!-- /.panel -->
</div><!-- /.panel-group -->

<script>
(function(){
  var out=document.getElementById('updOut'),
      chk=document.getElementById('updCheck'),
      app=document.getElementById('updApply');
  function show(t){ out.style.display='block'; out.textContent=t; }
  chk.addEventListener('click', function(e){
    e.preventDefault(); show('Suche nach Updates...');
    fetch('api/update_api.php?action=check',{cache:'no-store'})
      .then(function(r){return r.text();})
      .then(function(t){
        show(t.replace(/^STATUS:\w+\n?/,''));
        app.style.display = /^STATUS:available/.test(t) ? 'inline-block' : 'none';
      })
      .catch(function(){ show('Fehler bei der Suche.'); });
  });
  app.addEventListener('click', function(e){
    e.preventDefault();
    if(!confirm('Update jetzt installieren? Einige Dienste werden dabei kurz neu gestartet.')) return;
    show('Aktualisiere...');
    fetch('api/update_api.php',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'action=apply',cache:'no-store'})
      .then(function(r){return r.text();})
      .then(function(t){ show(t); app.style.display='none'; })
      .catch(function(){ show('Fehler beim Update.'); });
  });
})();
</script>

<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title"><a name="contribute"></a>
        <i class="mdi mdi-source-pull"></i> Als Mit-Entwickler beitragen
      </h4>
    </div><!-- /.panel-heading -->
    <div class="panel-body">
      <p class="text-muted">
        Hier kannst du eigene Verbesserungen als <strong>Vorschlag (Pull Request)</strong> einreichen.
        Nichts wird direkt &uuml;bernommen &ndash; Adrian pr&uuml;ft jeden Vorschlag und entscheidet.
      </p>

      <div class="well well-sm" style="background:#f7f7f9;">
        <strong>Einmalige Einrichtung:</strong>
        <ol style="margin:8px 0 0 18px; padding:0;">
          <li>Kostenloses <strong>GitHub-Konto</strong> erstellen auf <a href="https://github.com/signup" target="_blank">github.com/signup</a>.</li>
          <li>Adrian deinen <strong>GitHub-Benutzernamen</strong> nennen &ndash; er l&auml;dt dich einmalig als Mitarbeiter ein.</li>
          <li><strong>Zugangs-Token</strong> erstellen unter
              <a href="https://github.com/settings/personal-access-tokens" target="_blank">github.com/settings/personal-access-tokens</a>
              &rarr; &bdquo;Generate new token&ldquo;. Dort einstellen: <em>Repository access</em> = nur
              <code>meisteroe/Phoniebox_withPhonieHat</code>, und unter <em>Permissions &rarr; Repository &rarr; Contents</em> =
              <strong>Read and write</strong>. Token erzeugen und <strong>kopieren</strong> (wird nur einmal angezeigt!).</li>
          <li>Unten <strong>Namen</strong> und den <strong>Token</strong> einf&uuml;gen und <strong>Speichern</strong>.</li>
        </ol>
      </div>

      <div class="row">
        <div class="col-md-8">
          <div class="form-group">
            <label>Dein Name (erscheint an den Commits)</label>
            <input type="text" id="contribName" class="form-control" placeholder="z. B. Max Mustermann">
          </div>
          <div class="form-group">
            <label>GitHub-Zugangs-Token</label>
            <input type="password" id="contribToken" class="form-control" autocomplete="off" placeholder="github_pat_...">
          </div>
          <a href="#" id="contribSave" class="btn btn-default"><i class="mdi mdi-content-save"></i> Speichern</a>
          <span id="contribStatus" class="text-muted" style="margin-left:10px;">&nbsp;</span>
        </div>
      </div>

      <hr>

      <p><strong>Vorschlag einreichen</strong> &ndash; verpackt deine aktuellen &Auml;nderungen in einen Pull Request:</p>
      <div class="row">
        <div class="col-md-8">
          <div class="input-group">
            <input type="text" id="contribDesc" class="form-control" placeholder="Kurz: was hast du geaendert?">
            <span class="input-group-btn">
              <a href="#" id="contribSubmit" class="btn btn-warning"><i class="mdi mdi-source-pull"></i> Vorschlag einreichen</a>
            </span>
          </div>
        </div>
      </div>
      <pre id="contribOut" style="display:none; margin-top:10px; white-space:pre-wrap; word-break:break-word;"></pre>
      <div id="contribLink" style="margin-top:8px;"></div>

    </div><!-- /.panel-body -->
  </div><!-- /.panel -->
</div><!-- /.panel-group -->

<script>
(function(){
  var nameEl=document.getElementById('contribName'),
      tokEl=document.getElementById('contribToken'),
      statusEl=document.getElementById('contribStatus'),
      outEl=document.getElementById('contribOut'),
      linkEl=document.getElementById('contribLink');
  function show(t){ outEl.style.display='block'; outEl.textContent=t; }
  function refreshStatus(){
    fetch('api/contribute_api.php?action=status',{cache:'no-store'})
      .then(function(r){return r.text();})
      .then(function(t){
        if(/STATUS:ready/.test(t)){
          var m=t.match(/name:(.*)/); var nm=(m&&m[1].trim())?(' ('+m[1].trim()+')'):'';
          statusEl.innerHTML='<span class="text-success">✓ eingerichtet'+nm+'</span>';
        } else {
          statusEl.innerHTML='<span class="text-warning">noch nicht eingerichtet</span>';
        }
      }).catch(function(){});
  }
  document.getElementById('contribSave').addEventListener('click', function(e){
    e.preventDefault();
    if(tokEl.value.trim()===''){ show('Bitte zuerst den Token einfügen.'); return; }
    show('Speichere...');
    var body='action=savetoken&name='+encodeURIComponent(nameEl.value)+'&token='+encodeURIComponent(tokEl.value);
    fetch('api/contribute_api.php',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:body,cache:'no-store'})
      .then(function(r){return r.text();})
      .then(function(t){ show(t); tokEl.value=''; refreshStatus(); })
      .catch(function(){ show('Fehler beim Speichern.'); });
  });
  document.getElementById('contribSubmit').addEventListener('click', function(e){
    e.preventDefault();
    if(!confirm('Deine aktuellen Änderungen als Vorschlag einreichen?')) return;
    show('Reiche ein...'); linkEl.innerHTML='';
    var body='action=submit&desc='+encodeURIComponent(document.getElementById('contribDesc').value);
    fetch('api/contribute_api.php',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:body,cache:'no-store'})
      .then(function(r){return r.text();})
      .then(function(t){
        show(t);
        var m=t.match(/https:\/\/github\.com\/\S+compare\S+/);
        if(m){ linkEl.innerHTML='<a href="'+m[0]+'" target="_blank" class="btn btn-success"><i class="mdi mdi-source-pull"></i> Pull Request oeffnen und abschicken</a>'; }
      })
      .catch(function(){ show('Fehler beim Einreichen.'); });
  });
  refreshStatus();
})();
</script>

<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title"><a name="language"></a>
         <i class='mdi mdi-emoticon'></i> <?php print $lang['globalLanguageSettings']; ?>
      </h4>
    </div><!-- /.panel-heading -->

    <div class="panel-body">
      <div class="row">
<?php
include("inc.setLanguage.php");
?>
      </div><!-- / .row -->
    </div><!-- /.panel-body -->

<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title"><a name="language"></a>
         <i class='mdi mdi-emoticon'></i> <?php print $lang['settingsPlayoutBehaviourCard']; ?>
      </h4>
    </div><!-- /.panel-heading -->
    
    <div class="panel-body">
      <div class="row">
<?php
include("inc.setPlayerBehaviourRFID.php");
?>
      </div><!-- / .row -->
    </div><!-- /.panel-body -->

  </div><!-- /.panel -->
</div><!-- /.panel-group -->

<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title"><a name="volume"></a>
         <i class='mdi mdi-volume-high'></i> <?php print $lang['globalVolumeSettings']; ?>
      </h4>
    </div><!-- /.panel-heading -->

    <div class="panel-body">
      <div class="row">
<?php
include("inc.setVolume.php");
include("inc.setMaxVolume.php");
include("inc.setVolumeStep.php");
include("inc.setStartupVolume.php");
include("inc.setBootVolume.php");
?>
      </div><!-- / .row -->
    </div><!-- /.panel-body -->

  </div><!-- /.panel -->
</div><!-- /.panel-group -->


<?php
$filename = $conf['settings_abs'].'/bluetooth-sink-switch';
if (file_exists($filename)) {
   if (strcmp(strtolower(trim(file_get_contents($filename))), "enabled") === 0) {
      include('inc.bluetooth.php');
   }
}
?>


<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title"><a name="autoShutdown"></a>
        <i class='mdi mdi-clock-end'></i> <?php print $lang['globalAutoShutdown']." ".$lang['globalSettings']; ?>
      </h4>
    </div><!-- /.panel-heading -->
    <div class="panel-body">

        <div class="row">

<?php
include("inc.setStoptimer.php");
include("inc.setSleeptimer.php");
include("inc.setShutdownVolumeReduction.php");
include("inc.setIdleShutdown.php");
?>
        </div><!-- / .row -->

    </div><!-- /.panel-body -->

  </div><!-- /.panel -->
</div><!-- /.panel-group -->

<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title"><a name="wifi"></a>
        <i class='mdi mdi-wifi'></i> <?php print $lang['globalWifiSettings']; ?>
      </h4>
    </div><!-- /.panel-heading -->

      <div class="panel-body">
<?php
include("inc.setWifi.php");
?>
      </div><!-- /.panel-body -->

  </div><!-- /.panel -->
</div><!-- /.panel-group -->

<?php
/*
* This is work in progress. 
* If you were to have a local mailserver installed, 
* Phoniebox could send you the IP address over email.
* Useful if you move your Phoniebox into a new Wifi which
* assigns a dynmamic IP.
*/
include("inc.setWlanIpRead.php");
?>

<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title"><a name="webInterface"></a>
        <i class='mdi mdi-cards-outline'></i> <?php print $lang['settingsWebInterface']; ?>
      </h4>
    </div><!-- /.panel-heading -->

      <div class="panel-body">

<?php
include("inc.setWebUI.php");
?>

      </div><!-- /.panel-body -->
  </div><!-- /.panel -->
</div><!-- /.panel-group -->

<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title"><a name="externalInterfaces"></a>
        <i class='mdi mdi-usb'></i> <?php print $lang['globalExternalInterfaces']; ?>
      </h4>
    </div><!-- /.panel-heading -->

      <div class="panel-body">
<?php
include("inc.setInputDevices.php");
?>
      </div><!-- /.panel-body -->
  </div><!-- /.panel -->
</div><!-- /.panel-group -->

<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title"><a name="secondSwipe"></a>
        <i class='mdi mdi-cards-outline'></i> <?php print $lang['settingsSecondSwipe']; ?>
      </h4>
    </div><!-- /.panel-heading -->

      <div class="panel-body">
<?php
include("inc.setSecondSwipe.php");
include("inc.setSecondSwipePause.php");
include("inc.setSecondSwipePauseControls.php");
?>
      </div><!-- /.panel-body -->

  </div><!-- /.panel -->
</div><!-- /.panel-group -->

<?php include("inc.setDebugLogConf.php"); ?>

</div><!-- /.container -->

</body>
<script src="js/jukebox.js">
</script>
</html>
