import logging
import sys
from subprocess import Popen as function_call
import os
import pathlib
import RPi.GPIO as GPIO
import json

# === LED FEEDBACK v2 ===
def led_feedback(kind):
    """Sendet LED-Feedback"""
    try:
        with open("/tmp/led_command.json", "w") as f:
            json.dump({"command": "feedback", "kind": kind}, f)
    except:
        pass

def led_playback(state):
    """Sendet Playback-Status"""
    try:
        with open("/tmp/led_command.json", "w") as f:
            json.dump({"command": "playback", "state": state}, f)
    except:
        pass

def led_sleep(minutes):
    """Sendet Sleep-Timer"""
    try:
        with open("/tmp/led_command.json", "w") as f:
            json.dump({"command": "sleep", "minutes": minutes}, f)
    except:
        pass
        
# GPIO27 Setup (Kopfhörerverstärker) das wurde in anleitung nicht erwähnt
GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.OUT, initial=GPIO.LOW)

class phoniebox_function_calls:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        playout_control_relative_path = "../../scripts/playout_controls.sh"
        function_calls_absolute_path = str(pathlib.Path(__file__).parent.absolute())
        self.playout_control = os.path.abspath(os.path.join(function_calls_absolute_path, playout_control_relative_path))
        rfid_trigger_relative_path = "../../scripts/rfid_trigger_play.sh"
        self.rfid_trigger = os.path.abspath(os.path.join(function_calls_absolute_path, rfid_trigger_relative_path))

    # ========== STANDARD FUNKTIONEN ==========
    
    def functionCallShutdown(self, *args):
        led_feedback("button_press")
        #led_feedback("shutdown")
        function_call("{command} -c=shutdown".format(command=self.playout_control), shell=True)

    def functionCallVolU(self, steps=None, *args):
        led_feedback("button_press")
        if steps is None:
            function_call("{command} -c=volumeup".format(command=self.playout_control), shell=True)
        else:
            function_call("{command} -c=volumeup -v={value}".format(value=steps, command=self.playout_control), shell=True)

    def functionCallVolD(self, steps=None, *args):
        led_feedback("button_press")
        if steps is None:
            function_call("{command} -c=volumedown".format(command=self.playout_control), shell=True)
        else:
            function_call("{command} -c=volumedown -v={value}".format(value=steps, command=self.playout_control), shell=True)

    def functionCallVol0(self, *args):
        if os.path.exists("/tmp/phoniebox_recording_state"):
            return  # Ignoriere Button bei Aufnahme
        led_feedback("volume_min")
        function_call("{command} -c=mute".format(command=self.playout_control), shell=True)

    def functionCallPlayerNext(self, *args):
        led_feedback("button_press")
        function_call("{command} -c=playernext".format(command=self.playout_control), shell=True)

    def functionCallPlayerPrev(self, *args):
        led_feedback("button_press")
        function_call("{command} -c=playerprev".format(command=self.playout_control), shell=True)

    def functionCallPlayerPauseForce(self, *args):
        function_call("{command} -c=playerpauseforce".format(command=self.playout_control), shell=True)

    def functionCallPlayerPause(self, *args):
        # Waehrend einer Aufnahme: Play/Pause pausiert/setzt die AUFNAHME fort
        # (Segment-basiert via custom_record_pause.sh), statt den MPD-Player zu steuern.
        if os.path.exists("/tmp/phoniebox_recording_state"):
            import subprocess
            subprocess.run(['/home/pi/RPi-Jukebox-RFID/scripts/custom_record_pause.sh'])
            return
        led_feedback("button_press")
        function_call("{command} -c=playerpause".format(command=self.playout_control), shell=True)

    def functionCallRecordStart(self, *args):
        function_call("{command} -c=recordstart".format(command=self.playout_control), shell=True)

    def functionCallRecordStop(self, *args):
        function_call("{command} -c=recordstop".format(command=self.playout_control), shell=True)

    def functionCallRecordPlayLatest(self, *args):
        function_call("{command} -c=recordplaylatest".format(command=self.playout_control), shell=True)

    def functionCallToggleWifi(self, *args):
        function_call("{command} -c=togglewifi".format(command=self.playout_control), shell=True)

    def functionCallPlayerStop(self, *args):
        function_call("{command} -c=playerstop".format(command=self.playout_control), shell=True)

    def functionCallPlayerSeekFwd(self, seconds=None, *args):
        led_feedback("button_press")
        if seconds is None:
            seconds = 10
        function_call("{command} -c=playerseek -v=+{value}".format(command=self.playout_control, value=seconds), shell=True)

    def functionCallPlayerSeekBack(self, seconds=None, *args):
        led_feedback("button_press")
        if seconds is None:
            seconds = 10
        function_call("{command} -c=playerseek -v=-{value}".format(command=self.playout_control, value=seconds), shell=True)

    def functionCallPlayerSeekFarFwd(self, seconds=None, *args):
        if seconds is None:
            seconds = 60
        function_call("{command} -c=playerseek -v=+{value}".format(command=self.playout_control, value=seconds), shell=True)

    def functionCallPlayerSeekFarBack(self, seconds=None, *args):
        if seconds is None:
            seconds = 60
        function_call("{command} -c=playerseek -v=-{value}".format(command=self.playout_control, value=seconds), shell=True)

    def functionCallPlayerRandomTrack(self, *args):
        function_call("{command} -c=randomtrack".format(command=self.playout_control), shell=True)

    def functionCallPlayerRandomCard(self, *args):
        function_call("{command} -c=randomcard".format(command=self.playout_control), shell=True)

    def functionCallPlayerRandomFolder(self, *args):
        function_call("{command} -c=randomfolder".format(command=self.playout_control), shell=True)

    def functionCallBluetoothToggle(self, mode=None, *args):
        if mode is None:
            mode = 'toggle'
        function_call("{command} -c=bluetoothtoggle -v={value}".format(command=self.playout_control, value=mode), shell=True)

    def functionCallTriggerPlayCardId(self, cardid, *args):
        function_call("{command} --cardid={value}".format(command=self.rfid_trigger, value=cardid), shell=True)

    def functionCallTriggerPlayFolder(self, folder, *args):
        function_call("{command} --dir={value}".format(command=self.rfid_trigger, value=folder), shell=True)

    def getFunctionCall(self, functionName):
        self.logger.error('Get FunctionCall: {} {}'.format(functionName, functionName in locals()))
        getattr(sys.modules[__name__], str)
        return locals().get(functionName, None)

# ========== CUSTOM FUNKTIONEN ==========

    def functionCallHeadphoneDetect(self, *args):
        """
        Kopfhörer-Erkennung
        GPIO12 LOW = eingesteckt → GPIO27 HIGH (Verstärker AN)
        GPIO12 HIGH = raus → GPIO27 LOW (Verstärker AUS)
        """
        import RPi.GPIO as GPIO
        
        # GPIO27 Setup (falls noch nicht geschehen)
        GPIO.setmode(GPIO.BCM)
        try:
            GPIO.setup(27, GPIO.OUT)
        except:
            pass
        
        # Status prüfen
        if GPIO.input(12) == GPIO.LOW:
            GPIO.output(27, GPIO.HIGH)
            led_feedback("headphone_in")
            self.logger.info("Kopfhörer eingesteckt - Verstärker aktiviert")
        else:
            GPIO.output(27, GPIO.LOW)
            led_feedback("headphone_out")
            self.logger.info("Kopfhörer entfernt - Verstärker deaktiviert")

    def functionCallSleepTimer(self, *args):
        if os.path.exists("/tmp/phoniebox_recording_state"):
            return  # Ignoriere Button bei Aufnahme
        led_feedback("button_press")
        """Sleep Timer durchschalten (15/30/45/60/aus)"""
        import subprocess
        subprocess.run(['/home/pi/RPi-Jukebox-RFID/scripts/custom_sleep_toggle.sh'])

    def functionCallNightLight(self, *args):
        if os.path.exists("/tmp/phoniebox_recording_state"):
            return  # Ignoriere Button bei Aufnahme
        """Nachtlicht Toggle"""
        led_feedback("button_press")
        import subprocess
        subprocess.run(['/home/pi/RPi-Jukebox-RFID/scripts/custom_nightlight_toggle.sh'])

    def functionCallRecord(self, *args):
        """Audio Aufnahme starten/stoppen"""
        import subprocess
        subprocess.run(['/home/pi/RPi-Jukebox-RFID/scripts/custom_record_toggle.sh'])
    
    def functionCallUnlinkRecording(self, *args):
        if os.path.exists("/tmp/phoniebox_recording_state"):
            return  # Ignoriere Button bei Aufnahme
        """Recording-Verknüpfung entfernen (Record 5s)"""
        import subprocess
        subprocess.run(['/home/pi/RPi-Jukebox-RFID/scripts/custom_unlink_recording.sh'])