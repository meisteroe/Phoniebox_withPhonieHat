<?php
/*
 * inc.setHostname.php — Geraetename (Hostname) in der WebUI aendern.
 * Verarbeitet eigenen POST (newhostname), validiert streng und ruft
 * scripts/custom_set_hostname.sh (per sudo) auf. SSH per IP bleibt unberuehrt.
 */
$hostnameMsg = "";
if (isset($_POST['newhostname']) && trim($_POST['newhostname']) != "") {
    $cand = strtolower(trim($_POST['newhostname']));
    if (preg_match('/^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/', $cand)) {
        $cmd = "/usr/bin/sudo ".$conf['scripts_abs']."/custom_set_hostname.sh ".escapeshellarg($cand)." 2>&1";
        $out = trim(shell_exec($cmd));
        $cls = (strpos($out, 'FEHLER') === 0) ? 'danger' : 'success';
        $hostnameMsg = "<div class='alert alert-".$cls."' style='margin-top:10px;'>".htmlspecialchars($out)."</div>";
    } else {
        $hostnameMsg = "<div class='alert alert-danger' style='margin-top:10px;'>Ung&uuml;ltiger Name. Erlaubt: a&ndash;z, 0&ndash;9, Bindestrich (nicht am Anfang/Ende), max. 63 Zeichen.</div>";
    }
}
$curHost = trim(shell_exec("hostname"));
?>
<div class="col-md-8">
  <p class="text-muted" style="margin-top:0;">
    Erreichbar im Netzwerk als <code><?php echo htmlspecialchars($curHost); ?>.local</code>.
    N&uuml;tzlich, wenn mehrere Boxen im selben Netz sind. Nach der &Auml;nderung ggf. kurz neu verbinden.
  </p>
  <form name="hostname" method="post" action="<?php print $_SERVER['PHP_SELF']; ?>#hostname">
    <div class="input-group">
      <input type="text" name="newhostname" class="form-control"
             value="<?php echo htmlspecialchars($curHost); ?>"
             pattern="[A-Za-z0-9][A-Za-z0-9-]{0,62}" maxlength="63"
             title="a-z, 0-9, Bindestrich (nicht am Anfang/Ende)">
      <span class="input-group-btn">
        <input type="submit" class="btn btn-default" value="<?php print $lang['globalSet']; ?>">
      </span>
    </div>
  </form>
  <?php echo $hostnameMsg; ?>
</div>
