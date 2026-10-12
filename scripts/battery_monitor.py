#!/usr/bin/env python3
"""
Battery Monitor für Phoniebox
Liest ADS1115 A0, berechnet %, schreibt JSON für WebUI
"""

#!/usr/bin/env python3
"""
Battery Monitor Daemon für Phoniebox v2.8.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Funktionen:
- Kontinuierliche Spannungsüberwachung (alle 2s)
- Auto-Shutdown bei < 3.15V (5s Hysterese)
- PWRLock Trigger (bistabile Kippstufe, GPIO15)
- LED-Feedback über LED Controller
- WebUI JSON Export
"""
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import RPi.GPIO as GPIO
import json
import time
import subprocess
import sys

# ═══════════════════════════════════════════════════════════
# KONFIGURATION
# ═══════════════════════════════════════════════════════════

def signal_handler(sig, frame):
    """
    Sauberes Beenden bei SIGTERM/SIGINT
    WICHTIG: Kein GPIO.cleanup()! (würde Input machen → Flanke!)
    """
    sig_name = signal.Signals(sig).name
    print()
    print("=" * 40)
    print(f"⏹️  Signal {sig_name} empfangen")
    print("   Beende Battery Monitor (GPIO15 bleibt LOW)")
    print("=" * 40)
    
    # GPIO15 explizit auf LOW halten
    try:
        GPIO.output(PWRLOCK_GPIO, GPIO.LOW)
        print(f"✓ GPIO{PWRLOCK_GPIO} bleibt als OUTPUT LOW")
    except Exception as e:
        print(f"⚠️  GPIO Fehler: {e}")
    
    # WICHTIG: KEIN GPIO.cleanup()!
    # Pin bleibt als OUTPUT LOW → keine Flanke!
    
    sys.exit(0)

# Akku-Limits
VMAX = 4.2              # Voll geladen (LiPo 1S)
VMIN = 3.1              # Leer (absolutes Minimum)
VCRITICAL = 3.1        # Kritische Spannung → Shutdown!
SHUTDOWN_DELAY = 10      # Sekunden unter VCRITICAL vor Shutdown

# Hardware
PWRLOCK_GPIO = 17       #(GPIO17) - PWRLock Kippstufe
PWRLOCK_DURATION = 0.3  # Sekunden HIGH für bistabile Kippstufe
VOLTAGE_FACTOR = 5.7    # Spannungsteiler-Faktor (R1+R2)/R2

# Timing
CHECK_INTERVAL = 2      # Prüf-Intervall in Sekunden

# ═══════════════════════════════════════════════════════════
# GPIO SETUP
# ═══════════════════════════════════════════════════════════

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(PWRLOCK_GPIO, GPIO.OUT, initial=GPIO.LOW)  

print("=== Battery Monitor Daemon v2.0 ===")
print(f"PWRLock: GPIO{PWRLOCK_GPIO}")
print(f"Shutdown Schwelle: < {VCRITICAL}V für {SHUTDOWN_DELAY}s")
print(f"Check Interval: {CHECK_INTERVAL}s")
print("=" * 40)

# ═══════════════════════════════════════════════════════════
# HELPER FUNKTIONEN
# ═══════════════════════════════════════════════════════════

def led_battery(voltage):
    """
    Sendet Spannung an LED Controller
    LED 0 zeigt automatisch Farbe basierend auf Spannung:
    - ≥4.1V: Grün
    - 3.5-4.1V: Grün→Gelb
    - 3.3-3.5V: Gelb→Rot
    - ≤3.2V: Rot pulsierend
    """
    try:
        with open("/tmp/led_command.json", "w") as f:
            json.dump({"command": "battery", "voltage": voltage}, f)
    except:
        pass

def trigger_pwrlock_shutdown(voltage):
    """
    Aktiviert PWRLock Kippstufe und fährt System herunter
    
    PWRLock-Funktion:
    - Bistabile Kippstufe verhindert Neustart nach Shutdown
    - Nur manueller Power-Button kann System wieder einschalten
    - Schützt LiPo vor Tiefentladung
    """
    print()
    print("=" * 40)
    print(f"⚠️  KRITISCHE SPANNUNG: {voltage:.2f}V")
    print(f"⚠️  Schwelle {VCRITICAL}V für {SHUTDOWN_DELAY}s unterschritten!")
    print("=" * 40)
    print("🔒 Aktiviere PWRLock Kippstufe...")
    
    # NEU: Vor dem eigentlichen Shutdown die Wiedergabe sauber beenden und den
    # LowBat-Warnton abspielen. Reihenfolge exakt wie beim regulaeren Shutdown
    # (playout_controls.sh -c=shutdown), der bewaehrt ist:
    #   1. Resume-Position sichern, solange MPD noch spielt (savepos)
    #   2. Playlist leeren -> gibt das Audiogeraet frei, stoppt die Musik
    #   3. LowBat.mp3 ueber mpg123 abspielen (klar hoerbar, nichts uebertoent es)
    # Zusaetzlich sichert der systemd-Dienst resume-savepos-on-shutdown die Position
    # als Fallback beim Herunterfahren (dann greift savepos hier bereits, der Dienst
    # findet MPD geleert vor und ueberschreibt die gute Position nicht).
    try:
        subprocess.run(["/home/pi/RPi-Jukebox-RFID/scripts/resume_play.sh", "-c=savepos"], timeout=15)
        subprocess.run(["/usr/bin/mpc", "clear"], timeout=10)
    except Exception as e:
        print(f"⚠️  Resume-Position sichern / Playlist leeren fehlgeschlagen: {e}")
    try:
        subprocess.run(["/usr/bin/mpg123", "/home/pi/RPi-Jukebox-RFID/shared/LowBat.mp3"], timeout=20)
    except Exception as e:
        print(f"⚠️  LowBat-Ton konnte nicht abgespielt werden: {e}")

    # PWRLock HIGH für 0.3s (triggert bistabile Kippstufe)
    GPIO.output(PWRLOCK_GPIO, GPIO.HIGH)
    time.sleep(PWRLOCK_DURATION)
    GPIO.output(PWRLOCK_GPIO, GPIO.LOW)
    
    print("✓ PWRLock aktiviert - Neustart verhindert")
    print("🔴 System wird heruntergefahren...")
    print("=" * 40)
    
    # LED auf niedrigste Spannung (Rot pulsierend)
    led_battery(0)
    
    # Shutdown (1 Minute Warnung für laufende Prozesse)
    subprocess.run(["sudo", "shutdown", "-h", "+1", "Battery critical - Auto shutdown"])
    
    # Sofortiges Exit (Service wird nicht neu gestartet)
    GPIO.cleanup()
    sys.exit(0)

# ═══════════════════════════════════════════════════════════
# HAUPTLOGIK
# ═══════════════════════════════════════════════════════════

def main():
    # ADS1115 Setup
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c)
        chan = AnalogIn(ads, 0)  # Kanal A0
        print("✓ ADS1115 initialisiert (I2C @ 0x48)")
    except Exception as e:
        print(f"❌ ADS1115 Fehler: {e}")
        print("Prüfe I2C Verbindung: i2cdetect -y 1")
        sys.exit(1)
    
    # State
    low_voltage_start = None  # Timestamp wann unter VCRITICAL
    last_debug_log = 0        # Timestamp letztes Debug-Log
    
    print("✓ Daemon gestartet - überwache Akku...")

    # Einschwingen: erste ADS1115-Messung(en) verwerfen. Direkt nach dem Start
    # liefert der ADS oft 0 / eine Transiente → sonst zeigt die LED kurz ROT und
    # springt dann auf GRÜN. Erst ab plausibler Spannung (>2.5V, unter dem echten
    # Akku-Bereich) weiter; bei wirklich leerem Akku bricht der Timeout (~3s) ab.
    for _ in range(15):
        try:
            if chan.voltage * VOLTAGE_FACTOR > 2.5:
                break
        except Exception:
            pass
        time.sleep(0.2)

    print()

    # Hauptschleife
    while True:
        try:
            # ─────────────────────────────────────────────
            # SPANNUNG MESSEN
            # ─────────────────────────────────────────────
            
            raw_voltage = chan.voltage
            voltage = raw_voltage * VOLTAGE_FACTOR
            
            # Prozent berechnen (linear zwischen VMIN und VMAX)
            percent = ((voltage - VMIN) / (VMAX - VMIN)) * 100
            percent = max(0, min(100, int(percent)))
            
            # Status-Text für WebUI
            if percent > 80:
                status = "full"
            elif percent > 20:
                status = "good"
            elif percent > 10:
                status = "low"
            else:
                status = "critical"
            
            # ─────────────────────────────────────────────
            # JSON EXPORT (für WebUI & Scripts)
            # ─────────────────────────────────────────────
            
            data = {
                "voltage": round(voltage, 2),
                "percent": percent,
                "status": status,
                "raw": chan.value,
                "timestamp": int(time.time())
            }
            
            # WebUI JSON
            with open("/tmp/battery_status.json", "w") as f:
                json.dump(data, f)
            
            # Legacy Format (für alte Scripts)
            with open("/tmp/jukebox.battery", "w") as f:
                f.write(f"{voltage:.2f}")
            
            # ─────────────────────────────────────────────
            # LED-FEEDBACK AKTUALISIEREN
            # ─────────────────────────────────────────────
            
            led_battery(voltage)
            
            # ─────────────────────────────────────────────
            # LOW VOLTAGE DETECTION & SHUTDOWN
            # ─────────────────────────────────────────────
            
            if voltage < VCRITICAL:
                # ⚠️ Spannung unter kritischer Schwelle!
                
                if low_voltage_start is None:
                    # Erste Unterschreitung → Timer starten
                    low_voltage_start = time.time()
                    print(f"⚠️  Niedrige Spannung erkannt: {voltage:.2f}V (Schwelle: {VCRITICAL}V)")
                    print(f"    Shutdown in {SHUTDOWN_DELAY}s wenn Spannung nicht steigt...")
                
                else:
                    # Prüfe wie lange schon unter Schwelle
                    elapsed = time.time() - low_voltage_start
                    
                    if elapsed >= SHUTDOWN_DELAY:
                        # ❌ Zu lange unter Schwelle → SHUTDOWN!
                        trigger_pwrlock_shutdown(voltage)
                        # (kommt nie hier zurück - sys.exit() in Funktion)
                    
                    else:
                        # ⏱️ Countdown
                        remaining = SHUTDOWN_DELAY - elapsed
                        print(f"⚠️  Shutdown in {remaining:.1f}s ({voltage:.2f}V)")
            
            else:
                # ✓ Spannung OK (über Schwelle)
                
                if low_voltage_start is not None:
                    # Spannung hat sich erholt!
                    print(f"✓ Spannung erholt: {voltage:.2f}V (über {VCRITICAL}V)")
                    low_voltage_start = None
            
            # ─────────────────────────────────────────────
            # DEBUG-LOG (alle 20 Sekunden)
            # ─────────────────────────────────────────────
            
            now = time.time()
            if now - last_debug_log >= 20:
                print(f"🔋 {percent}% ({voltage:.2f}V) - {status}")
                last_debug_log = now
            
            # Warte bis nächster Check
            time.sleep(CHECK_INTERVAL)
        
        except KeyboardInterrupt:
            signal_handler(signal.SIGINT, None) 
        
        except Exception as e:
            # Fehlerbehandlung - Service läuft weiter!
            print(f"❌ Fehler im Monitor-Loop: {e}")
            print("   Retry in 5 Sekunden...")
            time.sleep(5)

# ═══════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Fataler Fehler: {e}")
        GPIO.cleanup()
        sys.exit(1)