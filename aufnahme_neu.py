import sys
import math as m
import serial.tools.list_ports
import pandas as pd
from pyGeoCOM.surveytools import Angle, Coordinate
from pyGeoCOM.GeoComLite import TotalStation, AtmosphericCorrectionData 
from pyGeoCOM.GeoComEnumeration import PositionMode, ATRMode, EDMMeasurementMode, TMCInclinationSensorMeasurementProgram, OnOffType, BAPPrismenType 
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
        try:
            dictlist.sort(key=lambda x: x["HZ"], reverse=not auf)
        except KeyError:
            
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
        time.sleep(40)
        
        ###--- 

        """
        Die 1. Geschwindigkeitskorretion wird im Gerät nach Herstellerformel angebracht! 
        """
        self.set_prism_type(BAPPrismenType.BAP_PRISM_ROUND)
        atmo_data = AtmosphericCorrectionData(0.2818, self.druck, self.temp, self.temp)
        print(f"Sende Atmo-Daten: {self.temp}°C bei {self.druck}hPa")
        self.totalstation.set_atm_correction(atmo_data)
        
        ###---

        print("Setze Streckenmessmodus...")
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
                print("Messung 1. Lage: Punkt "+str(pnr))
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
            
                print("Messung 2. Lage: Punkt "+str(pnr))
                # Berechnung für die zweite Lage (Umschlag)
                self.moveit(hz + 200, 400 - vz)
                
                m_obj = self.totalstation.measure(pnr, self.totalstation.get_atm_correction(), time.time())
                korr_dist = float(m_obj.slope_distances) + p_const

                x = Satzmessung.Messung(
                    m_obj.target_number, 
                    float(m_obj.direction.value_rad),
                    float(m_obj.zenith.value_rad), 
                    korr_dist
                    #achtung *0.5 evtl wieder weg!
                )
                L2.addMessung(x)

            S = Satzmessung.Satz(L1, L2)
            S.mittelLage() # Hier wird die 1-gon Toleranz intern angewendet, Schwellenwert ist bewusst hoch & sollte nicht geändert werden!
            self.alle_saetze.append(S) 
            
        self.sm = Satzmessung.Satzmessung(self.alle_saetze) 
        
        print("Satzmessung beendet, Warteposition...")
        self.moveit(0,200) #Parkposition
        print("Gute Nacht Tachymeter!")
        self.totalstation.turn_off() #Tachymeter wird abgeschaltet (unb. weglassen bei BT-Verbindung!)
        self.totalstation.serialPort.close() #evtl. unnötig, wird sicherheitshalber trotzdem gemacht

    def connect(self):

        """
        Wichtig: ttyUSB0 ist standardmäßig der erste angeschlossene USB-Port: 
        Entweder das Tachymeter IMMER als 1. anschließen, oder den Port entsprechend ändern
        Wird das Programm auf einem Windows-Betriebssystem ausgeführt, so ist der Pfad zum USB-Port zu ändern (/COMxx)
        """
        self.totalstation = TotalStation("/dev/ttyUSB1", baudrate=115200) #für linux
        #self.totalstation = TotalStation("COM11", baudrate=9600)     #für windows

    def moveit(self, ph, pv):
        self.totalstation.set_telescope_position(Angle.from_gon(ph%400), Angle.from_gon(pv%400), 
                                                 PositionMode.AUT_NORMAL, ATRMode.AUT_TARGET)

    def changeEDMmode(self, index):
        mode = EDMMeasurementMode.EDM_SINGLE_STANDARD if index == 0 else EDMMeasurementMode.EDM_SINGLE_SRANGE
        self.totalstation.set_edm_mode(mode)

    def set_prism_type(self, prism_type: BAPPrismenType):
        """
        Sendet den Befehl zum Wechsel des Prismentyps direkt über die 
        offene Schnittstelle der pyGeoCOM-Bibliothek.
        RPC 17008 = BAP_SetPrismType
        """
        command = f"%R1Q,17008:{prism_type.value}"
        response = self.totalstation.request(command)
        return response[0] # Gibt den LeicaReturnCode zurück    
