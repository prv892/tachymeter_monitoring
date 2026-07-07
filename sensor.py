import struct
import time
import serial
import board
import adafruit_bmp3xx


"""
Beide Klassen wurden vom jeweiligen Hersteller übernommen, welcher sie als Beispielklassen anbietet:
Thermometer: usbtemp.com
BMP388: Adafruit

Sollten andere Sensoren verbaut werden, so ist dies möglich, aber es muss der Abruf der Wetterdaten in main.py angepasst werden
"""

class ThermometerException(Exception):
    pass

class Thermometer:
    """USB Thermometer Middleware (DS18B20 via UART)
    
    Wichtig: ttyUSB1 ist standardmäßig der zweite angeschlossene USB-Port: 
    Entweder das Thermometer IMMER als 2. anschließen, oder den Port entsprechend ändern
    Wird das Programm auf einem Windows-Betriebssystem ausgeführt, so ist der Pfad zum USB-Port zu ändern (/COMxx)
    """
    def __init__(self, port='/dev/ttyUSB1', timeout=1):
        self.port = port
        self.timeout = timeout
        self.uart = None

    def Open(self):
        if not self.uart or not self.uart.isOpen():
            self.uart = serial.Serial(self.port, timeout=self.timeout)

    def Close(self):
        if self.uart and self.uart.isOpen():
            self.uart.close()
            self.uart = None

    def Temperature(self):
        self._owReset()
        self._owWrite(0xcc)
        self._owWrite(0x44)
        time.sleep(1)
        self._owReset()
        self._owWrite(0xcc)
        self._owWrite(0xbe)
        scratchpad = self._readBytes(9)
        if self._crc8(scratchpad[0:8]) != scratchpad[8]:
            raise ThermometerException('CRC error')
        temp = struct.unpack('<h', scratchpad[0:2])[0]
        return float(temp) / 16.0

    def _owReset(self):
        self.uart.reset_input_buffer()
        self.uart.reset_output_buffer()
        self.uart.baudrate = 9600
        self.uart.write(b'\xf0')
        r = self.uart.read(1)
        self.uart.baudrate = 115200
        if not r or r[0] == 0xf0: raise ThermometerException('No device')
        
    def _owWriteByte(self, byte):
        w = [(0xff if byte & (1 << i) else 0x00) for i in range(8)]
        self.uart.write(bytes(w))
        r = self.uart.read(8)
        val = 0
        for i, b in enumerate(r):
            if b == 0xff: val |= (1 << i)
        return val

    def _owWrite(self, byte):
        if self._owWriteByte(byte) != byte: raise ThermometerException('Write error')

    def _readBytes(self, n):
        return bytes([self._owWriteByte(0xff) for _ in range(n)])

    def _crc8(self, data):
        crc = 0
        for byte in data:
            for _ in range(8):
                mix = (crc ^ byte) & 0x01
                crc >>= 1
                if mix: crc ^= 0x8c
                byte >>= 1
        return crc

class PressureManager:
    """Klasse für den BMP388 I2C Drucksensor"""
    def __init__(self):
        try:
            self.i2c = board.I2C()
            self.sensor = adafruit_bmp3xx.BMP3XX_I2C(self.i2c)
            self.sensor.pressure_oversampling = 8
            self.sensor.temperature_oversampling = 2
        except Exception as e:
            print(f"Fehler Initialisierung BMP388: {e}")
            self.sensor = None

    def get_data(self):
        if not self.sensor: return None, None
        try:
            return self.sensor.pressure, self.sensor.temperature
        except Exception as e:
            print(f"Fehler beim Lesen des BMP388: {e}")
            return None, None