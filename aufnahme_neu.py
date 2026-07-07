import sys
import math as m
import serial.tools.list_ports
import pandas as pd
from surveytools import Angle, Coordinate
from GeoComLite import TotalStation, AtmosphericCorrectionData 
from GeoComEnumeration import PositionMode, ATRMode, EDMMeasurementMode, TMCInclinationSensorMeasurementProgram, OnOffType
import time
from datetime import datetime
import Satzmessung

class sortierer():
    """
    Sortiert die Zielliste nach HZ, 
    auf = True  aufsteigend
    auf = False absteigend
    """
    @staticmethod
    def output(dictlist, auf):
        # Wir nutzen die eingebaute sort-Funktion von Python, das ist schneller und sauberer
        # Wir sortieren nach dem Key "HZ" (Großbuchstaben beachten wegen der Vorverarbeitung in main)
        try:
            dictlist.sort(key=lambda x: x["HZ"], reverse=not auf)
        except KeyError:
            # Fallback, falls die Keys doch kleingeschrieben sind
            dictlist.sort(key=lambda x: x["hz"], reverse=not auf)
        return dictlist

class execute():
    def __init__(self, pktliste, anz_saetze, temp=20.0, druck=1000):
        self.startzeit = datetime.now()
        self.anz_saetze = anz_saetze
        self.tar = pktliste
        self.temp = temp
        self.druck = druck
        
        self.connect() #Port beachten! (siehe connect())
        self.totalstation.wake_up() #Tachymeter wird angeschaltet (weglassen bei BT-Verbindung)
        
        ###--- 

        """
        Die 1. Geschwindigkeitskorretion wird im Gerät nach Herstellerformel angebracht! 
        """

        atmo_data = AtmosphericCorrectionData(0.2818, self.druck, self.temp, self.temp)
        print(f"Sende Atmo-Daten: {self.temp}°C bei {self.druck}hPa")
        self.totalstation.set_atm_correction(atmo_data)
        
        ###---

        self.changeEDMmode(0) ### Streckenmessmodus mit Reflektor, Reflektorlos = 1
        self.alle_saetze = [] 

        for s_idx in range(self.anz_saetze):
            print(f"Satz {s_idx+1} startet...")

            # --- Lage I ---
            L1 = Satzmessung.Lage(1)    
            self.tar = sortierer.output(self.tar, True)
            
            for i in range(len(self.tar)):
                punkt = self.tar[i]
                pnr = punkt.get("PNR", punkt.get("pnr"))
                hz = float(punkt.get("HZ", punkt.get("hz")))
                vz = float(punkt.get("VZ", punkt.get("vz")))
                p_const = float(punkt.get("PRISM", punkt.get("prism", 0.0)))
                self.moveit(hz, vz)
                
                m_obj = self.totalstation.measure(pnr, self.totalstation.get_atm_correction(), time.time())
                korr_dist = float(m_obj.slope_distances) + p_const
                
                x = Satzmessung.Messung(m_obj.target_number, float(m_obj.direction.value_rad),
                                       float(m_obj.zenith.value_rad), korr_dist)
                L1.addMessung(x)
                
                
            # --- Lage II ---
            L2 = Satzmessung.Lage(2)
            self.tar = sortierer.output(self.tar, False)
            
            for i in range(len(self.tar)):
                punkt = self.tar[i]
                pnr = punkt.get("PNR", punkt.get("pnr"))
                hz = float(punkt.get("HZ", punkt.get("hz")))
                vz = float(punkt.get("VZ", punkt.get("vz")))
                p_const = float(punkt.get("PRISM", punkt.get("prism", 0.0)))
            
                
                # Berechnung für die zweite Lage (Umschlag)
                self.moveit(hz + 200, 400 - vz)
                
                m_obj = self.totalstation.measure(pnr, self.totalstation.get_atm_correction(), time.time())
                korr_dist = float(m_obj.slope_distances) + p_const

                x = Satzmessung.Messung(
                    m_obj.target_number, 
                    float(m_obj.direction.value_rad),
                    float(m_obj.zenith.value_rad), 
                    korr_dist*0.5
                    #achtung *0.5 evtl wieder weg!
                )
                L2.addMessung(x)

            S = Satzmessung.Satz(L1, L2)
            S.mittelLage() # Hier wird die 1-gon Toleranz intern angewendet, Schwellenwert ist bewusst hoch & sollte nicht geändert werden!
            self.alle_saetze.append(S) 
            
        self.sm = Satzmessung.Satzmessung(self.alle_saetze) 
        
        self.moveit(0,200) #Parkposition
        self.totalstation.turn_off() #Tachymeter wird abgeschaltet (unb. weglassen bei BT-Verbindung!)
        self.totalstation.serialPort.close() #evtl. unnötig, wird sicherheitshalber trotzdem gemacht

    def connect(self):

        """
        Wichtig: ttyUSB0 ist standardmäßig der erste angeschlossene USB-Port: 
        Entweder das Tachymeter IMMER als 1. anschließen, oder den Port entsprechend ändern
        Wird das Programm auf einem Windows-Betriebssystem ausgeführt, so ist der Pfad zum USB-Port zu ändern (/COMxx)
        """
        #self.totalstation = TotalStation("/dev/ttyUSB0", baudrate=9600)
        self.totalstation = TotalStation("COM1", baudrate=9600)

    def moveit(self, ph, pv):
        self.totalstation.set_telescope_position(Angle.from_gon(ph%400), Angle.from_gon(pv%400), 
                                                 PositionMode.AUT_NORMAL, ATRMode.AUT_TARGET)

    def changeEDMmode(self, index):
        mode = EDMMeasurementMode.EDM_SINGLE_STANDARD if index == 0 else EDMMeasurementMode.EDM_SINGLE_SRANGE
        self.totalstation.set_edm_mode(mode)
