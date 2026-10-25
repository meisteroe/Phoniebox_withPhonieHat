#!/usr/bin/env python3

import datetime
import json
import os
import re
import socket
import subprocess
import time
from threading import Thread

import inotify.adapters
import paho.mqtt.client as mqtt
import paho.mqtt.enums as mqtt_enum

# ----------------------------------------------------------
#  Prerequisites
# ----------------------------------------------------------
# pip3 install paho-mqtt inotify


# ----------------------------------------------------------
#  SETTINGS
# ----------------------------------------------------------
config = {
    "DEBUG": False,
    "mqttBaseTopic": "phoniebox",  # MQTT base topic
    "mqttClientId": "phoniebox",  # MQTT client ID
    "mqttHostname": "openHAB",  # MQTT server hostname
    "mqttPort": 8883,  # MQTT server port (typically 1883 for unencrypted, 8883 for encrypted)
    "mqttUsername": "",  # username for user/pass based authentication
    "mqttPassword": "",  # password for user/pass based authentication
    "mqttCA": "/home/pi/MQTT/mqtt-ca.crt",  # path to server certificate for certificate-based authentication
    "mqttCert": "/home/pi/MQTT/mqtt-client-phoniebox.crt",  # path to client certificate for certificate-based authentication
    "mqttKey": "/home/pi/MQTT/mqtt-client-phoniebox.key",  # path to client keyfile for certificate-based authentication
    "mqttConnectionTimeout": 60,  # in seconds; timeout for MQTT connection
    "refreshIntervalPlaying": 5,  # in seconds; how often should the status be sent to MQTT (while playing)
    "refreshIntervalIdle": 30,  # in seconds; how often should the status be sent to MQTT (when NOT playing)
    "homeAssistantDiscovery": False,  # publish Home Assistant MQTT discovery configs
    "homeAssistantDiscoveryPrefix": "homeassistant",
}


# ----------------------------------------------------------
#  DO NOT CHANGE BELOW
# ----------------------------------------------------------

# absolute path of the Phoniebox "scripts" folder. The daemon may run from
# scripts/ (classic install) or directly from components/.../MQTT-protocol/.
path = os.path.dirname(os.path.realpath(__file__))
if not os.path.exists(os.path.join(path, "playout_controls.sh")):
    path = os.path.realpath(os.path.join(path, "..", "..", "..", "scripts"))

# Optional local settings (not in git) override the defaults above, e.g.
# settings/mqtt_client.json: {"mqttHostname": "homeassistant.local", ...}
# The value "auto" for mqttBaseTopic / mqttClientId means: use the hostname,
# so cloned boxes don't collide on the same broker.
settingsFile = os.path.join(path, "..", "settings", "mqtt_client.json")
if os.path.exists(settingsFile):
    with open(settingsFile) as f:
        config.update(json.load(f))
hostname = socket.gethostname()
for key in ("mqttBaseTopic", "mqttClientId"):
    if config.get(key) == "auto":
        config[key] = hostname

# internal refresh interval
refreshInterval = config.get("refreshIntervalPlaying")

# list of available commands and attributes
arAvailableCommands = [
    "volumeup",
    "volumedown",
    "mute",
    "playerplay",
    "playerpause",
    "playernext",
    "playerprev",
    "playerstop",
    "playerrewind",
    "playershuffle",
    "playerreplay",
    "scan",
    "shutdown",
    "shutdownsilent",
    "reboot",
    "disablewifi",
]
arAvailableCommandsWithParam = [
    "setvolume",
    "setvolstep",
    "setmaxvolume",
    "setidletime",
    "playerseek",
    "shutdownafter",
    "shutdownvolumereduction",
    "playerstopafter",
    "playerrepeat",
    "rfid",
    "gpio",
    "swipecard",
    "playfolder",
    "playfolderrecursive",
]
arAvailableAttributes = [
    "volume",
    "mute",
    "repeat",
    "repeat_mode",
    "random",
    "state",
    "file",
    "artist",
    "albumartist",
    "title",
    "album",
    "track",
    "elapsed",
    "duration",
    "trackdate",
    "last_card",
    "maxvolume",
    "volstep",
    "idletime",
    "rfid",
    "gpio",
    "remaining_stopafter",
    "remaining_shutdownafter",
    "remaining_shutdownvolumereduction",
    "remaining_idle",
    "throttling",
    "temperature",
]


def watchForNewCard():
    i = inotify.adapters.Inotify()
    i.add_watch(path + "/../settings/Latest_RFID")

    # wait for inotify events
    for event in i.event_gen(yield_nones=False):
        if event is not None:
            # fetch event attributes
            (e_header, e_type_names, e_path, e_filename) = event

            # file was closed and written => a new card was swiped
            if "IN_CLOSE_WRITE" in e_type_names:
                # fetch card ID
                cardid = readfile(path + "/../settings/Latest_RFID")

                # publish event "card_swiped"
                client.publish(
                    config.get("mqttBaseTopic") + "/event/card_swiped", payload=cardid
                )
                print(" --> Publishing event card_swiped = " + cardid)

                # process all attributes
                processGet("all")


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connection established.")

        # retrieve server version and edition
        version = readfile(path + "/../settings/version")
        edition = readfile(path + "/../settings/edition")

        # check disk space
        disk_total, disk_avail = disk_stats()

        # publish general server info
        client.publish(
            config.get("mqttBaseTopic") + "/state", payload="online", qos=1, retain=True
        )
        client.publish(
            config.get("mqttBaseTopic") + "/version",
            payload=version,
            qos=1,
            retain=True,
        )
        client.publish(
            config.get("mqttBaseTopic") + "/edition",
            payload=edition,
            qos=1,
            retain=True,
        )
        client.publish(
            config.get("mqttBaseTopic") + "/disk_total",
            payload=disk_total,
            qos=1,
            retain=True,
        )
        client.publish(
            config.get("mqttBaseTopic") + "/disk_avail",
            payload=disk_avail,
            qos=1,
            retain=True,
        )

        # (re)subscribe here so subscriptions survive reconnects
        client.subscribe(config.get("mqttBaseTopic") + "/cmd/#")
        client.subscribe(config.get("mqttBaseTopic") + "/get/#")

        if config.get("homeAssistantDiscovery"):
            publishHomeAssistantDiscovery()
            # Home Assistant announces restarts here -> resend everything
            client.subscribe(config.get("homeAssistantDiscoveryPrefix") + "/status")

        # send all attributes in the next cycle (not only changed ones)
        global lastFullPublish
        lastFullPublish = 0

    else:
        print("Connection could NOT be established. Return-Code:", rc)


def on_disconnect(client, userdata, rc):
    # paho reconnects automatically as long as the network loop keeps running
    print("Disconnected. Return-Code:", str(rc))


def publishHomeAssistantDiscovery():
    """Announce Phoniebox entities to Home Assistant (MQTT discovery)."""
    base = config.get("mqttBaseTopic")
    prefix = config.get("homeAssistantDiscoveryPrefix")
    node = re.sub(r"[^a-zA-Z0-9_-]", "_", base)
    device = {
        "identifiers": [node],
        "name": hostname,
        "manufacturer": "Phoniebox",
        "model": readfile(path + "/../settings/edition"),
        "sw_version": readfile(path + "/../settings/version"),
        "configuration_url": "http://" + hostname + ".local/",
    }
    common = {
        "availability_topic": base + "/state",
        "payload_available": "online",
        "payload_not_available": "offline",
        "device": device,
    }

    def attr(name):
        return base + "/attribute/" + name

    def cmd(name):
        return base + "/cmd/" + name

    entities = []

    # sensors: (key, name, icon, unit, device_class, value_template)
    sensors = [
        ("state", "Status", "mdi:play-pause", None, None, None),
        ("title", "Titel", "mdi:music", None, None, None),
        ("artist", "Interpret", "mdi:account-music", None, None, None),
        ("album", "Album", "mdi:album", None, None, None),
        ("elapsed", "Laufzeit", "mdi:timer-outline", None, None, None),
        ("duration", "Dauer", "mdi:timer", None, None, None),
        ("last_card", "Letzte Karte", "mdi:card-account-details", None, None, None),
        ("temperature", "CPU-Temperatur", None, "°C", "temperature",
         "{{ value | replace(\"'C\", \"\") | float(0) }}"),
        ("throttling", "Stromversorgung", "mdi:flash", None, None, None),
        ("remaining_stopafter", "Stopp in", "mdi:timer-stop", "min", None, None),
        ("remaining_shutdownafter", "Ausschalten in", "mdi:power-sleep", "min", None, None),
        ("remaining_idle", "Leerlauf-Abschaltung in", "mdi:sleep", "min", None, None),
    ]
    for key, name, icon, unit, dclass, tpl in sensors:
        e = {"name": name, "state_topic": attr(key)}
        if icon:
            e["icon"] = icon
        if unit:
            e["unit_of_measurement"] = unit
        if dclass:
            e["device_class"] = dclass
            e["state_class"] = "measurement"
        if tpl:
            e["value_template"] = tpl
        if key in ("temperature", "throttling"):
            e["entity_category"] = "diagnostic"
        entities.append(("sensor", key, e))

    entities.append(("sensor", "disk_avail", {
        "name": "Freier Speicher", "state_topic": base + "/disk_avail",
        "unit_of_measurement": "GB", "icon": "mdi:sd", "entity_category": "diagnostic",
    }))

    # numbers: (key, name, icon, state attribute, command, min, max, unit)
    numbers = [
        ("volume", "Lautstärke", "mdi:volume-high", "volume", "setvolume", 0, 100, "%"),
        ("maxvolume", "Maximale Lautstärke", "mdi:volume-plus", "maxvolume", "setmaxvolume", 0, 100, "%"),
        ("stopafter", "Stopp nach", "mdi:timer-stop", "remaining_stopafter", "playerstopafter", 0, 180, "min"),
        ("shutdownafter", "Ausschalten nach", "mdi:power-sleep", "remaining_shutdownafter", "shutdownafter", 0, 180, "min"),
    ]
    for key, name, icon, state, command, nmin, nmax, unit in numbers:
        entities.append(("number", key, {
            "name": name, "icon": icon, "state_topic": attr(state),
            "command_topic": cmd(command), "command_template": "{{ value | int }}",
            "min": nmin, "max": nmax, "step": 1, "unit_of_measurement": unit,
            "mode": "slider" if unit == "%" else "box",
        }))

    # buttons: (command, name, icon)
    buttons = [
        ("playerplay", "Play", "mdi:play"),
        ("playerpause", "Pause (umschalten)", "mdi:play-pause"),
        ("playerstop", "Stopp", "mdi:stop"),
        ("playernext", "Nächster Titel", "mdi:skip-next"),
        ("playerprev", "Vorheriger Titel", "mdi:skip-previous"),
        ("volumeup", "Lauter", "mdi:volume-plus"),
        ("volumedown", "Leiser", "mdi:volume-minus"),
        ("mute", "Stumm (umschalten)", "mdi:volume-mute"),
        ("shutdown", "Herunterfahren", "mdi:power"),
        ("reboot", "Neustart", "mdi:restart"),
    ]
    for command, name, icon in buttons:
        e = {"name": name, "icon": icon, "command_topic": cmd(command), "payload_press": ""}
        if command in ("shutdown", "reboot"):
            e["entity_category"] = "config"
        entities.append(("button", command, e))

    # text field: play a folder by name
    entities.append(("text", "playfolder", {
        "name": "Ordner abspielen", "icon": "mdi:folder-play",
        "command_topic": cmd("playfolder"), "max": 255,
    }))

    for component, key, e in entities:
        e.update(common)
        e["unique_id"] = node + "_" + key
        e["object_id"] = node + "_" + key
        client.publish(
            prefix + "/" + component + "/" + node + "/" + key + "/config",
            payload=json.dumps(e), qos=1, retain=True,
        )

    # every swiped card becomes a Home Assistant "tag" (Settings -> Tags)
    client.publish(
        prefix + "/tag/" + node + "/card/config",
        payload=json.dumps({
            "topic": base + "/event/card_swiped",
            "value_template": "{{ value }}",
            "device": device,
        }),
        qos=1, retain=True,
    )
    print("Published Home Assistant discovery for " + str(len(entities)) + " entities")


def on_log(client, userdata, level, buf):
    print("   [LOG]", buf)


def on_message(client, userdata, message):
    global lastFullPublish
    if message.topic == config.get("homeAssistantDiscoveryPrefix") + "/status":
        if message.payload.decode("utf-8") == "online":
            print("Home Assistant (re)started -> resending discovery and all attributes")
            publishHomeAssistantDiscovery()
            lastFullPublish = 0
        return

    print("")
    print("MQTT message incoming to subscriptions...")
    print(" - topic =", message.topic)
    print(" - value =", message.payload.decode("utf-8"))

    regex_extract = re.search(
        config.get("mqttBaseTopic") + "\/(.*)\/(.*)", message.topic
    )
    message_topic = regex_extract.group(1).lower()
    message_subtopic = regex_extract.group(2).lower()
    message_payload = message.payload.decode("utf-8")

    if message_topic == "cmd":
        processCmd(message_subtopic, message_payload)

    elif message_topic == "get":
        processGet(message_subtopic, force=True)


def processCmd(command, parameter):
    # list all commands
    if command == "help":
        availableCommands = ", ".join(arAvailableCommands)
        availableCommandsWithParam = ", ".join(arAvailableCommandsWithParam)
        client.publish(
            config.get("mqttBaseTopic") + "/available_commands",
            payload=availableCommands,
        )
        client.publish(
            config.get("mqttBaseTopic") + "/available_commands_with_params",
            payload=availableCommandsWithParam,
        )
        print(" --> Publishing response available_commands =", availableCommands)
        print(
            " --> Publishing response available_commands_with_params =",
            availableCommandsWithParam,
        )

    # toggle RFID reader daemon
    elif command == "rfid":
        parameter = parameter.lower()
        if parameter == "start" or parameter == "stop":
            subprocess.call(
                ["sudo /bin/systemctl " + parameter + " phoniebox-rfid-reader.service"],
                shell=True,
            )
        else:
            print(" --> Expecting parameter start or stop")

    # toggle GPIO button daemon
    elif command == "gpio":
        parameter = parameter.lower()
        if parameter == "start" or parameter == "stop":
            subprocess.call(
                [
                    "sudo /bin/systemctl "
                    + parameter
                    + " phoniebox-gpio-control.service"
                ],
                shell=True,
            )
        else:
            print(" --> Expecting parameter start or stop")

    # virtually swipe a RFID card
    elif command == "swipecard":
        print(" --> Virtually swiping card with ID", parameter)
        subprocess.call([path + "/rfid_trigger_play.sh", "-i=" + parameter])

    # play folder
    elif command == "playfolder":
        print(" --> Playing folder", parameter)
        subprocess.call([path + "/rfid_trigger_play.sh", "-d=" + parameter])

    # play folder (recursive)
    elif command == "playfolderrecursive":
        print(" --> Playing folder " + parameter + " (recursive)")
        subprocess.call(
            [path + "/rfid_trigger_play.sh", "-d=" + parameter, "-v=recursive"]
        )

    # all the other known commands w/o param
    elif command in arAvailableCommands:
        print(" --> Sending command " + command + " to playout_controls.sh")
        subprocess.call([path + "/playout_controls.sh", "-c=" + command])

    # all the other known commands /w param
    elif command in arAvailableCommandsWithParam:
        print(
            " --> Sending command "
            + command
            + " and value "
            + parameter
            + " to playout_controls.sh"
        )
        subprocess.call(
            [path + "/playout_controls.sh", "-c=" + command, "-v=" + parameter]
        )

    # we don't know this command
    else:
        print(" --> Unknown command", command)
        return

    # this was a known command => refresh all attributes as they might have changed
    refreshSlowValuesSoon()
    client.publish(config.get("mqttBaseTopic") + "/get/all", payload="")


# last published value per attribute (publish only on change, see processGet)
lastPublished = {}
lastFullPublish = 0
FULL_PUBLISH_INTERVAL = 60  # seconds; send everything at least this often


def processGet(attribute, force=False):
    global lastFullPublish

    # list all possible attributes
    if attribute == "help":
        availableAttributes = ", ".join(arAvailableAttributes)
        client.publish(
            config.get("mqttBaseTopic") + "/available_attributes",
            payload=availableAttributes,
        )
        return

    mpd_status = fetchData()

    # respond with all attributes (only changed ones, unless forced/periodic)
    if attribute == "all":
        if time.time() - lastFullPublish > FULL_PUBLISH_INTERVAL:
            force = True
        if force:
            lastFullPublish = time.time()
        for name, value in mpd_status.items():
            if force or lastPublished.get(name) != value:
                client.publish(config.get("mqttBaseTopic") + "/attribute/" + name, payload=value)
                lastPublished[name] = value
                if config.get("DEBUG"):
                    print(" --> Publishing " + name + " = " + value)

    # all the other known attributes
    elif attribute in mpd_status:
        client.publish(
            config.get("mqttBaseTopic") + "/attribute/" + attribute,
            payload=mpd_status[attribute],
        )
        lastPublished[attribute] = mpd_status[attribute]

    # we don't know this attribute
    else:
        print(" --> Could not retrieve attribute", attribute)


def disk_stats():
    statvfs = os.statvfs("/home/pi")
    size_total = statvfs.f_frsize * statvfs.f_blocks  # total
    # size_avail = statvfs.f_frsize * statvfs.f_bfree    # actual free
    size_avail = statvfs.f_frsize * statvfs.f_bavail  # free for non-root

    return round(size_total / 1073741824, 1), round(size_avail / 1073741824, 1)


def readfile(filepath):
    result = ""
    with open(filepath, "r") as f:
        result = f.read()
    return result.rstrip()


def isServiceRunning(svc):
    cmd = ["/bin/systemctl", "is-active", "--quiet", svc]
    return "true" if subprocess.run(cmd).returncode == 0 else "false"


def linux_jobs_remaining():
    """Minutes left per 'at' queue (s=stop, t=shutdown, q=volume reduction,
    i=idle) from ONE atq call instead of one call per queue."""
    result = {"s": 0, "t": 0, "q": 0, "i": 0}
    out = subprocess.run(["sudo", "atq"], stdout=subprocess.PIPE).stdout.decode("utf-8")
    now = datetime.datetime.now()
    for line in out.splitlines():
        # e.g. "12	Sun Oct 25 18:30:00 2026 s pi"
        m = re.match(r"\d+\s+\w+\s+(\w+)\s+(\d+)\s+(\d+:\d+:\d+)\s+(\d+)\s+(\w)\s", line + " ")
        if not m or m.group(5) not in result:
            continue
        try:
            due = datetime.datetime.strptime(" ".join(m.group(1, 2, 3, 4)), "%b %d %H:%M:%S %Y")
        except ValueError:
            continue
        minutes = max(0, int(round((due - now).total_seconds() / 60, 0)))
        result[m.group(5)] = max(result[m.group(5)], minutes)
    return result


THROTTLE_CODES = {
    0: "under-voltage detected",
    1: "arm frequency capped",
    2: "currently throttled",
    3: "soft temperature limit active",
    16: "under-voltage has occurred",
    17: "arm frequency capped has occurred",
    18: "throttling has occurred",
    19: "soft temperature limit has occurred",
}


def getOsThrottling():
    # read from sysfs (no vcgencmd process); fall back to vcgencmd
    try:
        code = int(readfile("/sys/devices/platform/soc/soc:firmware/get_throttled"), 16)
    except Exception:
        try:
            out = subprocess.run(["vcgencmd", "get_throttled"], stdout=subprocess.PIPE).stdout.decode()
            code = int(out.strip().split("0x")[1], 16)
        except Exception:
            return "-"
    if code == 0:
        return "OK"
    return "WARNING: " + ", ".join(t for bit, t in THROTTLE_CODES.items() if code & (1 << bit))


def getOsTemperature():
    try:
        return "{:.1f}'C".format(int(readfile("/sys/class/thermal/thermal_zone0/temp")) / 1000)
    except Exception:
        return "-"


def readGlobalConf():
    """Settings that playout_controls.sh would echo (getmaxvolume etc.),
    read directly from global.conf instead of starting a bash script."""
    values = {}
    try:
        with open(path + "/../settings/global.conf") as f:
            for line in f:
                m = re.match(r'\s*([A-Z0-9_]+)="?([^"\n]*)"?', line)
                if m:
                    values[m.group(1)] = m.group(2)
    except Exception:
        pass
    return values


def mpdQuery(commands, timeout=2):
    """Talk to MPD directly (no 'nc' process)."""
    data = b""
    try:
        with socket.create_connection(("localhost", 6600), timeout=timeout) as s:
            s.sendall(("\n".join(commands) + "\nclose\n").encode("utf-8"))
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
    except Exception as e:
        print("MPD query failed:", e)
    return data.decode("utf-8", errors="replace")


# slow values (timers, services, OS info) are refreshed less often
SLOW_REFRESH_INTERVAL = 30  # seconds
slowCache = {}
slowCacheTime = 0


def refreshSlowValuesSoon():
    """Call after a command so timers/services show up right away."""
    global slowCacheTime
    slowCacheTime = 0


def normalizeTrueFalse(s):
    if s == "0":
        return "false"
    else:
        return "true"


def regex(needle, hay, exception="-"):
    regex_extract = re.search(needle, hay)
    if regex_extract:
        return regex_extract.group(1)
    else:
        return exception


def getDuration(status):
    """ Find the duration of the track in the output from mpd status"""

    # try to get the duration value
    duration = regex("\nduration: (.*)\n", status)

    if duration == "-":
        # if the duration attribute is missing try to get the time
        # this attribute value is split into two parts by ":"
        # first is the elapsed time and the second part is the duration
        duration = regex("\ntime: .*:(.*)\n", status, "0")

    return int(float(duration))


REPEAT_MODE_OFF = "off"
REPEAT_MODE_SINGLE = "single"
REPEAT_MODE_PLAYLIST = "playlist"


def get_repeat_mode(repeat, status):
    """ Returns the repeat mode that is selected in mpd """

    if repeat == "false":
        return REPEAT_MODE_OFF

    single = regex("\nsingle: (.*)\n", status)
    if single == "0":
        return REPEAT_MODE_PLAYLIST

    return REPEAT_MODE_SINGLE


def fetchData():
    # use global refreshInterval as this function is run as a thread through the paho-mqtt loop
    global refreshInterval

    result = {}

    global slowCache, slowCacheTime

    # fetch status from MPD
    status = mpdQuery(["status", "currentsong"])

    # interpret status
    result["state"] = regex("\nstate: (.*)\n", status).lower()
    result["volume"] = regex("\nvolume: (.*)\n", status)
    result["repeat"] = normalizeTrueFalse(regex("\nrepeat: (.*)\n", status))
    result["repeat_mode"] = get_repeat_mode(result["repeat"], status)
    result["random"] = normalizeTrueFalse(regex("\nrandom: (.*)\n", status))

    # interpret mute state based on volume
    if result["volume"] == "0":
        result["mute"] = "true"
    else:
        result["mute"] = "false"

    # interpret metadata when in play/pause mode
    if result["state"] != "stop":

        result["file"] = regex("\nfile: (.*)\n", status)
        result["artist"] = regex("\nArtist: (.*)\n", status)
        result["albumartist"] = regex("\nAlbumArtist: (.*)\n", status)
        result["title"] = regex("\nTitle: (.*)\n", status)
        result["album"] = regex("\nAlbum: (.*)\n", status)
        result["track"] = regex("\nTrack: (.*)\n", status, "0")
        result["trackdate"] = regex("\nDate: (.*)\n", status)

        if result["title"] == "-":
            result["title"] = result["file"]

        elapsed = int(float(regex("\nelapsed: (.*)\n", status, "0")))
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        result["elapsed"] = "{:02}:{:02}:{:02}".format(
            int(hours), int(minutes), int(seconds)
        )

        duration = getDuration(status)
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        result["duration"] = "{:02}:{:02}:{:02}".format(
            int(hours), int(minutes), int(seconds)
        )

    # settings from global.conf (same values playout_controls.sh would echo)
    conf = readGlobalConf()
    result["maxvolume"] = conf.get("AUDIOVOLMAXLIMIT", "-")
    result["volstep"] = conf.get("AUDIOVOLCHANGESTEP", "-")
    result["idletime"] = conf.get("IDLETIMESHUTDOWN", "-")

    # fetch last card
    result["last_card"] = readfile(path + "/../settings/Latest_RFID")

    # slow values: service states, 'at' timers, OS information
    if time.time() - slowCacheTime > SLOW_REFRESH_INTERVAL:
        jobs = linux_jobs_remaining()
        slowCache = {
            "rfid": isServiceRunning("phoniebox-rfid-reader.service"),
            "gpio": isServiceRunning("phoniebox-gpio-control.service"),
            "remaining_stopafter": str(jobs["s"]),
            "remaining_shutdownafter": str(jobs["t"]),
            "remaining_shutdownvolumereduction": str(jobs["q"]),
            "remaining_idle": str(jobs["i"]),
            "throttling": getOsThrottling(),
        }
        slowCacheTime = time.time()
    result.update(slowCache)
    result["temperature"] = getOsTemperature()

    # modify refresh rate depending on play state
    if result["state"] == "play":
        refreshInterval = config.get("refreshIntervalPlaying")
    else:
        refreshInterval = config.get("refreshIntervalIdle")

    return result


# create client instance
client = mqtt.Client(callback_api_version=mqtt_enum.CallbackAPIVersion.VERSION1, client_id=config.get("mqttClientId"))

# configure authentication
if config.get("mqttUsername") and config.get("mqttPassword"):
    client.username_pw_set(
        username=config.get("mqttUsername"), password=config.get("mqttPassword")
    )

if config.get("mqttCert") and config.get("mqttKey"):
    if config.get("mqttCA"):
        client.tls_set(
            ca_certs=config.get("mqttCA"),
            certfile=config.get("mqttCert"),
            keyfile=config.get("mqttKey"),
        )
    else:
        client.tls_set(certfile=config.get("mqttCert"), keyfile=config.get("mqttKey"))
elif config.get("mqttCA"):
    client.tls_set(ca_certs=config.get("mqttCA"))

# attach event handlers
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
if config.get("DEBUG") is True:
    client.on_log = on_log

# define last will
client.will_set(
    config.get("mqttBaseTopic") + "/state", payload="offline", qos=1, retain=True
)

# connect to MQTT server
print(
    "Connecting to "
    + config.get("mqttHostname")
    + " on port "
    + str(config.get("mqttPort"))
)
# connect_async + loop_start: paho keeps retrying if the broker is not
# reachable yet (e.g. at boot) or goes away later (e.g. Home Assistant update)
client.reconnect_delay_set(min_delay=1, max_delay=60)
client.connect_async(
    config.get("mqttHostname"),
    config.get("mqttPort"),
    config.get("mqttConnectionTimeout"),
)
print("Subscribing to " + config.get("mqttBaseTopic") + "/cmd/# and /get/# once connected")

# register thread for watchForNewCard
tWatchForNewCard = Thread(target=watchForNewCard)
tWatchForNewCard.setDaemon(True)
tWatchForNewCard.start()

# start endless loop
client.loop_start()
while True:
    processGet("all")
    time.sleep(refreshInterval)
