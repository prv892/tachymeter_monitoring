import sys
import math as m
import serial.tools.list_ports
import pandas as pd
from pyGeoCOM.surveytools import Angle, Coordinate
from pyGeoCOM.GeoComLite import TotalStation, AtmosphericCorrectionData 
from pyGeoCOM.GeoComEnumeration import PositionMode, ATRMode, EDMMeasurementMode, TMCInclinationSensorMeasurementProgram, OnOffType
import time
from datetime import datetime




class execute():
    def __init__(self,  temp=20.0, druck=1000):
        self.startzeit = datetime.now()
        self.temp = temp
        self.druck = druck
        
        self.connect() #Port beachten! (siehe connect())
        #self.totalstation.wake_up() #Tachymeter wird angeschaltet (weglassen bei BT-Verbindung)
        
        
        self.moveit(100,100) #Parkposition
        self.totalstation.turn_off() #Tachymeter wird abgeschaltet (unb. weglassen bei BT-Verbindung!)
        #self.totalstation.serialPort.close() #evtl. unnötig, wird sicherheitshalber trotzdem gemacht

    def connect(self):

        """
        Wichtig: ttyUSB0 ist standardmäßig der erste angeschlossene USB-Port: 
        Entweder das Tachymeter IMMER als 1. anschließen, oder den Port entsprechend ändern
        Wird das Programm auf einem Windows-Betriebssystem ausgeführt, so ist der Pfad zum USB-Port zu ändern (/COMxx)
        """
        self.totalstation = TotalStation("COM5", baudrate=19200)

    def moveit(self, ph, pv):
        self.totalstation.set_telescope_position(Angle.from_gon(ph%400), Angle.from_gon(pv%400), 
                                                 PositionMode.AUT_NORMAL, ATRMode.AUT_TARGET)

    def changeEDMmode(self, index):
        mode = EDMMeasurementMode.EDM_SINGLE_STANDARD if index == 0 else EDMMeasurementMode.EDM_SINGLE_SRANGE
        self.totalstation.set_edm_mode(mode)


test = execute()