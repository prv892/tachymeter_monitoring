import os
import sys


current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


import math as m
import serial.tools.list_ports
import pandas as pd
import time
from datetime import datetime
import serial.tools.list_ports


from pyGeoCOM.surveytools import Angle, Coordinate
from pyGeoCOM.GeoComLite import TotalStation, AtmosphericCorrectionData 
from pyGeoCOM.GeoComEnumeration import PositionMode, ATRMode, EDMMeasurementMode, TMCInclinationSensorMeasurementProgram, OnOffType




class execute():
    def __init__(self,  temp=20.0, druck=1000):
        self.startzeit = datetime.now()
        self.temp = temp
        self.druck = druck
        
        self.connect() #Port beachten! (siehe connect())
        #self.totalstation.wake_up() #Tachymeter wird angeschaltet (weglassen bei BT-Verbindung)
        #time.sleep(30)
        self.totalstation.get_instrument_name();
        
        self.moveit(100,100) #Parkposition
        #self.totalstation.turn_off() #Tachymeter wird abgeschaltet (unb. weglassen bei BT-Verbindung!)
        self.totalstation.serialPort.close() #evtl. unnötig, wird sicherheitshalber trotzdem gemacht

    def connect(self):

        """
        Wichtig: ttyUSB0 ist standardmäßig der erste angeschlossene USB-Port: 
        Entweder das Tachymeter IMMER als 1. anschließen, oder den Port entsprechend ändern
        Wird das Programm auf einem Windows-Betriebssystem ausgeführt, so ist der Pfad zum USB-Port zu ändern (/COMxx)
        """
        for p in serial.tools.list_ports.comports():
                # FTDI-Chip (0403:6001) -> Totalstation
                if p.vid == 0x0403 and p.pid == 0x6001:
                    port_ts = p.device
                    print(f"Totalstation gefunden an: {port_ts}")
                    
                # Prolific-Chip (067B:23A3) -> Thermometer
                elif p.vid == 0x067B and p.pid == 0x23A3:
                    port_temp = p.device
                    print(f"Thermometer gefunden an: {port_temp}")
        self.totalstation = TotalStation(port_ts, baudrate=115200)
        #self.totalstation = TotalStation("/dev/ttyUSB0", baudrate=115200)

    def moveit(self, ph, pv):
        self.totalstation.set_telescope_position(Angle.from_gon(ph%400), Angle.from_gon(pv%400), 
                                                 PositionMode.AUT_NORMAL, ATRMode.AUT_TARGET)

    def changeEDMmode(self, index):
        mode = EDMMeasurementMode.EDM_SINGLE_STANDARD if index == 0 else EDMMeasurementMode.EDM_SINGLE_SRANGE
        self.totalstation.set_edm_mode(mode)


test = execute()
