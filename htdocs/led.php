<?php
include("inc.header.php");
html_bootstrap3_createHeader("de","LED | Phoniebox",$conf['base_url']);
?>
<body>
<div class="container">
<?php include("inc.navigation.php"); ?>
<div class="panel-group">

<!-- EINSTELLUNGEN -->
<div class="panel panel-default">
<div class="panel-heading">
  <h3 class="panel-title"><i class="mdi mdi-lightbulb-outline"></i> LED Steuerung
  <span id="badge" class="label label-default pull-right">...</span></h3>
</div>
<div class="panel-body">
  <table class="table table-condensed" style="margin:0">
  <tr>
    <td width="35%"><strong>Feedback-LED</strong></td>
    <td width="10%"><input type="checkbox" id="fbOn" onchange="tog('toggle_feedback',this.checked)"></td>
    <td><input type="range" id="fbB" min="10" max="100" style="width:100%" onchange="slider('set_feedback_brightness',this.value)"></td>
    <td width="45px" class="text-right"><span id="fbV" class="label label-info">-</span></td>
  </tr>
  <tr>
    <td><strong>Beleuchtung</strong></td>
    <td><input type="checkbox" id="ltOn" onchange="tog('toggle_lighting',this.checked)"></td>
    <td><input type="range" id="ltB" min="5" max="100" style="width:100%" onchange="slider('set_lighting_brightness',this.value)"></td>
    <td class="text-right"><span id="ltV" class="label label-info">-</span></td>
  </tr>
  <tr>
    <td><strong>Playback-Status</strong><br><small class="text-muted">Sehr dunkles Leuchten bei Wiedergabe</small></td>
    <td><input type="checkbox" id="pbOn" onchange="tog('toggle_playback_status',this.checked)"></td>
    <td colspan="2"></td>
  </tr>
  <tr>
    <td><strong>Akku-Anzeige</strong><br><small class="text-muted">Helligkeit</small></td>
    <td></td>
    <td><input type="range" id="batB" min="0" max="100" style="width:100%" onchange="slider('set_battery_brightness',this.value)"></td>
    <td class="text-right"><span id="batV" class="label label-info">-</span></td>
  </tr>
  <tr>
    <td><strong>Akku-Anzeige ab</strong><br><small class="text-muted">leuchtet erst unter diesem Ladestand (100% = immer)</small></td>
    <td></td>
    <td><input type="range" id="batT" min="0" max="100" style="width:100%" onchange="slider('set_battery_threshold',this.value)"></td>
    <td class="text-right"><span id="batTV" class="label label-info">-</span></td>
  </tr>
  </table>
</div>
</div>

<!-- SLOTS -->
<div class="panel panel-default">
<div class="panel-heading">
  <h3 class="panel-title"><i class="mdi mdi-flash"></i> Lichttaster-Modi</h3>
</div>
<div class="panel-body">
  <p class="text-muted" style="margin-top:0"><small>Kurz drücken = nächster Modus &middot; Lang drücken = aus</small></p>
  <div id="slots">
<?php for($i=0; $i<6; $i++): ?>
    <div class="sr" id="slot-<?=$i?>">
      <span class="sn"><?=$i+1?></span>
      <select id="e<?=$i?>" onchange="sv(<?=$i?>)">
        <option value="off">Aus</option>
        <option value="nightlight">Nachtlicht</option>
        <option value="solid">Farbe</option>
        <option value="chase">Lauflicht</option>
        <option value="knightrider">Knight Rider</option>
        <option value="rainbow">Regenbogen</option>
        <option value="twinkle">Twinkles</option>
        <option value="firefly">Glühwürmchen</option>
        <option value="aurora">Polarlicht</option>
        <option value="candle">Kerzenlicht</option>
        <option value="vu_meter">Lichtorgel</option>
        <option value="vu_meter2">Lichtorgel 2</option>
      </select>
      <input type="color" id="c<?=$i?>" value="#FFFFFF" onchange="sv(<?=$i?>)">
      <input type="range" id="b<?=$i?>" min="5" max="100" value="50" onchange="sv(<?=$i?>)">
      <select id="s<?=$i?>" onchange="sv(<?=$i?>)">
        <option value="slow">Langsam</option>
        <option value="medium">Normal</option>
        <option value="fast">Schnell</option>
      </select>
      <button class="btn btn-xs btn-default" onclick="api('action=test_slot&i=<?=$i?>')" title="Testen">&#9654;</button>
    </div>
<?php endfor; ?>
  </div>
</div>
</div>

<!-- TEST -->
<div class="panel panel-default">
<div class="panel-heading"><h3 class="panel-title"><i class="mdi mdi-play-circle"></i> Test</h3></div>
<div class="panel-body">
  <div class="btn-group-sm">
    <button class="btn btn-default" onclick="api('action=feedback&kind=button_press')">Knopfdruck</button>
    <button class="btn btn-default" onclick="api('action=feedback&kind=card_ok')">Karte OK</button>
    <button class="btn btn-default" onclick="api('action=feedback&kind=card_unknown')">Karte ?</button>
    <button class="btn btn-default" onclick="api('action=feedback&kind=record_start')">Rec Start</button>
    <button class="btn btn-default" onclick="api('action=feedback&kind=record_stop')">Rec Stop</button>
    <button class="btn btn-default" onclick="api('action=feedback&kind=shutdown')">Shutdown</button>
  </div>
  <div style="margin-top:8px"><small class="text-muted" id="stateText">—</small></div>
</div>
</div>

</div>

<style>
.sr{background:#f9f9f9;border:1px solid #eee;border-radius:3px;padding:7px 8px;margin-bottom:6px;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.sr select,.sr input[type=color]{font-size:12px;height:28px;padding:2px 4px;border:1px solid #ccc;border-radius:3px;background-color:#fff;color:#333;-webkit-appearance:menulist}
.sr select option{background:#fff;color:#333}
.sr select{max-width:130px}
.sr input[type=color]{width:32px;cursor:pointer;padding:0}
.sr input[type=range]{width:70px}
.sn{width:20px;height:20px;line-height:20px;text-align:center;background:#3498db;color:#fff;border-radius:50%;font-size:11px;font-weight:bold;flex-shrink:0}
.sa{border-color:#3498db;background:#ebf5fb}
</style>

<script>
var E={"off":"Aus","nightlight":"Nachtlicht","solid":"Farbe","chase":"Lauflicht","knightrider":"Knight Rider","rainbow":"Regenbogen","twinkle":"Twinkles","firefly":"Glühwürmchen","aurora":"Polarlicht","candle":"Kerzenlicht","vu_meter":"Lichtorgel","vu_meter2":"Lichtorgel 2"};

function api(p){return fetch('api/led_api.php?'+p).then(function(r){return r.json()}).catch(function(){return null})}
function tog(a,v){api('action='+a+'&v='+(v?'1':'0'))}

var _t;
function slider(a,v){
  clearTimeout(_t);
  _t=setTimeout(function(){api('action='+a+'&v='+v)},250);
  if(a==='set_feedback_brightness')document.getElementById('fbV').textContent=v+'%';
  if(a==='set_lighting_brightness')document.getElementById('ltV').textContent=v+'%';
  if(a==='set_battery_brightness')document.getElementById('batV').textContent=v+'%';
  if(a==='set_battery_threshold')document.getElementById('batTV').textContent=(v>=100?'immer':v+'%');
}

function sv(i){
  var p='action=save_slot&i='+i;
  p+='&effect='+document.getElementById('e'+i).value;
  p+='&color='+encodeURIComponent(document.getElementById('c'+i).value);
  p+='&brightness='+document.getElementById('b'+i).value;
  p+='&speed='+document.getElementById('s'+i).value;
  api(p);
}

/* Setzt Wert nur wenn Element nicht gerade fokussiert ist */
function safeSet(id,val){
  var el=document.getElementById(id);
  if(el && document.activeElement!==el) el.value=val;
}
function safeCheck(id,val){
  var el=document.getElementById(id);
  if(el && document.activeElement!==el) el.checked=val;
}

function poll(){
  api('action=status').then(function(d){
    if(!d)return;

    /* Service-Badge */
    var b=document.getElementById('badge');
    b.textContent=d.alive?'Aktiv':'Aus';
    b.className='label pull-right '+(d.alive?'label-success':'label-danger');

    /* Einstellungen (nur wenn User nicht gerade bedient) */
    safeCheck('fbOn', d.feedback_enabled!==false);
    safeSet('fbB', d.feedback_brightness||70);
    document.getElementById('fbV').textContent=(d.feedback_brightness||70)+'%';

    safeCheck('ltOn', d.lighting_enabled!==false);
    safeSet('ltB', d.lighting_brightness||50);
    document.getElementById('ltV').textContent=(d.lighting_brightness||50)+'%';

    safeCheck('pbOn', d.playback_status_enabled===true);

    var bb=(d.battery_brightness!=null)?d.battery_brightness:30;
    safeSet('batB', bb); document.getElementById('batV').textContent=bb+'%';
    var bt=(d.battery_threshold!=null)?d.battery_threshold:100;
    safeSet('batT', bt); document.getElementById('batTV').textContent=(bt>=100?'immer':bt+'%');

    /* Slots: Werte updaten, kein DOM-Neuaufbau */
    var slots=d.slots||[];
    var cur=d.current_slot||-1;
    var on=d.lighting_on||false;
    for(var i=0;i<6;i++){
      var s=slots[i]||{effect:'off',color:'#FFFFFF',brightness:50,speed:'medium'};
      var row=document.getElementById('slot-'+i);
      if(!row)continue;

      /* Aktiv-Markierung */
      row.className=(on&&cur===i)?'sr sa':'sr';

      /* Werte setzen (nur wenn nicht fokussiert) */
      safeSet('e'+i, s.effect);
      safeSet('c'+i, s.color);
      safeSet('b'+i, s.brightness);
      safeSet('s'+i, s.speed);
    }

    /* Status-Text */
    var t=document.getElementById('stateText');
    if(!d.alive){t.textContent='Service nicht gestartet';return}
    var parts=[];
    if(d.lighting_on&&slots[d.current_slot])parts.push('Licht: '+(E[slots[d.current_slot].effect]||'?'));
    if(d.fb_mode&&d.fb_mode!=='none')parts.push('Feedback: '+d.fb_mode);
    if(d.sleep_active)parts.push('Sleep: '+Math.ceil(d.sleep_remaining)+'min');
    if(d.battery_voltage>0)parts.push('Akku: '+d.battery_voltage+'V');
    t.textContent=parts.length?parts.join(' · '):'Bereit';
  });
}

poll();
setInterval(poll,3000);
</script>

</div>
</body>
<script src="js/jukebox.js"></script>
</html>
