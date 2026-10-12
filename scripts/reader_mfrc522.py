#!/usr/bin/env python3
"""
MFRC522-Treibermodul für den Dual-Reader (oberer SPI-Slot).

Verwendet die 'mfrc522'-Bibliothek (pimylifeup), dieselbe wie die frühere
funktionierende Version (dual_readervor energiesparen.py).

WICHTIG – UID-Normalisierung:
  Die früher genutzte Klasse SimpleMFRC522 liefert eine DEZIMALZAHL
  (uid_to_num), die per format(id,'X')[:8] in Hex gewandelt wurde – ein
  ANDERES Format als der PN532 (roher Byte-Hex). Dadurch ergab dieselbe
  Karte je nach Reader unterschiedliche IDs.

  Dieses Modul nutzt stattdessen die Low-Level-Klasse MFRC522 direkt und gibt
  die ROHEN UID-Bytes als Hex zurück – exakt wie reader_pn532 / reader_pn5180.
  → Gleiche Karte = gleiche ID auf jedem Reader, Verknüpfungen bleiben gültig.

Einheitliche Schnittstelle:
    r = MFRC522Reader()
    uid = r.read()        # -> "A1A53BB4" oder None
    r.cleanup()

HINWEIS: Vollständig unterstützt werden 4-Byte-UIDs (MIFARE Classic – der
typische Anwendungsfall hier). 7-Byte-UIDs (NTAG, Cascade) werden vom MFRC522
in diesem Modul NICHT zusammengesetzt (der vordere PN532 kann das); bei Bedarf
später um SelectTag + Anticoll-Level-2 erweitern.
"""
import time

# Import erst hier, damit ein fehlendes mfrc522-Paket nur diesen Reader betrifft
from mfrc522 import MFRC522


class MFRC522Reader:
    name = "MFRC522-SPI"

    def __init__(self):
        self._rc = MFRC522()           # Standard-Pins (wie früher SimpleMFRC522())
        self._last_read = 0.0

    def read(self):
        """Liest eine MIFARE-UID. Gibt rohen Byte-Hex (4-Byte) oder None zurück."""
        # Kurze Sperre gegen Doppel-Reads (der MFRC522 ist schneller als nötig)
        now = time.time()
        if now - self._last_read < 0.05:
            return None
        try:
            # Karte wecken
            (status, _tag_type) = self._rc.MFRC522_Request(self._rc.PICC_REQIDL)
            if status != self._rc.MI_OK:
                return None
            # Anticollision → rohe UID-Bytes [u0, u1, u2, u3, BCC]
            (status, uid) = self._rc.MFRC522_Anticoll()
            if status != self._rc.MI_OK or not uid or len(uid) < 4:
                return None
            self._last_read = time.time()
            # Cascade-Tag (0x88) = 7-Byte-UID → hier nicht vollständig unterstützt
            if uid[0] == 0x88:
                return None
            return ''.join(f'{b:02X}' for b in uid[:4])
        except Exception:
            return None

    def cleanup(self):
        """RPi.GPIO freigeben (die mfrc522-Lib belegt GPIO-Pins im BOARD-Modus)."""
        try:
            import RPi.GPIO as GPIO
            GPIO.cleanup()
        except Exception:
            pass
