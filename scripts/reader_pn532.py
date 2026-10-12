#!/usr/bin/env python3
"""
PN532-Treibermodul für den Dual-Reader.

Verwendet die Adafruit-CircuitPython-Bibliothek (adafruit_pn532), die die
komplette ISO14443A-Logik (REQA, Anticollision, UID-Zusammenbau) intern erledigt.
Funktioniert sowohl am I²C-Bus (vorderer Slot) als auch am SPI-Bus (oberer Slot).

Einheitliche Schnittstelle (wie alle reader_*.py):
    r = PN532Reader(bus="i2c")        # oder bus="spi"
    uid = r.read()                    # -> "A1A53BB4" (Hex, Großbuchstaben) oder None
    r.cleanup()

Die UID wird als rohe Byte-Folge in Hex zurückgegeben – identisch zu allen
anderen Readern (reader_mfrc522, reader_pn5180). Dadurch ergibt dieselbe Karte
auf JEDEM Reader dieselbe ID, und Verknüpfungen bleiben beim Reader-Wechsel gültig.

Kann ISO14443A (MIFARE, NTAG) – aber KEIN ISO15693 (Tonie-Figuren). Dafür PN5180.
"""
import board
import busio
from digitalio import DigitalInOut


class PN532Reader:
    def __init__(self, bus="i2c", address=0x24, cs_pin=None, name=None):
        """
        bus     : "i2c" (vorderer Slot) oder "spi" (oberer Slot)
        address : I²C-Adresse (nur bei bus="i2c"), Standard 0x24
        cs_pin  : Chip-Select für SPI (Standard board.D24 = GPIO24)
        name    : Anzeigename (Standard "PN532-I2C" / "PN532-SPI")
        """
        self.bus = bus
        if bus == "i2c":
            from adafruit_pn532.i2c import PN532_I2C
            i2c = busio.I2C(board.SCL, board.SDA)
            self._pn532 = PN532_I2C(i2c, debug=False, address=address)
            self.name = name or "PN532-I2C"
        elif bus == "spi":
            from adafruit_pn532.spi import PN532_SPI
            spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
            cs = DigitalInOut(cs_pin if cs_pin is not None else board.D24)
            self._pn532 = PN532_SPI(spi, cs, debug=False)
            self.name = name or "PN532-SPI"
        else:
            raise ValueError(f"PN532Reader: unbekannter bus '{bus}' (erwartet 'i2c'/'spi')")

        # Secure Access Module konfigurieren (Normal-Modus) – sonst liest der PN532 nicht.
        self._pn532.SAM_configuration()

    def read(self):
        """Liest eine ISO14443A-UID. Gibt Hex-String (4- oder 7-Byte) oder None zurück."""
        try:
            uid = self._pn532.read_passive_target(timeout=0.1)
            if uid:
                return ''.join(f'{b:02X}' for b in uid)
        except Exception:
            pass
        return None

    def cleanup(self):
        """Nichts aufzuräumen – die Adafruit-Lib hält keine globalen Ressourcen."""
        pass
