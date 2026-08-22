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
    def __init__(self, pktliste, anz_saetze, temp=20.0, druck=1000, ts_port='/dev/ttyUSB1'):
        self.startzeit = datetime.now()
        self.anz_saetze = anz_saetze
        self.tar = pktliste
        self.temp = temp
        self.druck = druck
        self.ts_port = ts_port
        
        try:
            # 1. Neue ausfallsichere Verbindungsroutine aufrufen
            self._connect_with_retries()
            
            # 2. Regulärer Ablauf startet ab hier
            self.set_prism_type(BAPPrismenType.BAP_PRISM_ROUND)
            atmo_data = AtmosphericCorrectionData(0.2818, self.druck, self.temp, self.temp)
            print(f"Sende Atmo-Daten: {self.temp}°C bei {self.druck}hPa")
            self.totalstation.set_atm_correction(atmo_data)
            
            print("Setze Streckenmessmodus...")
            self.changeEDMmode(0) 
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
                    self.moveit(hz + 200, 400 - vz)
                    
                    m_obj = self.totalstation.measure(pnr, self.totalstation.get_atm_correction(), time.time())
                    korr_dist = float(m_obj.slope_distances) + p_const

                    x = Satzmessung.Messung(
                        m_obj.target_number, 
                        float(m_obj.direction.value_rad),
                        float(m_obj.zenith.value_rad), 
                        korr_dist
                    )
                    L2.addMessung(x)

                S = Satzmessung.Satz(L1, L2)
                S.mittelLage() 
                self.alle_saetze.append(S) 
                
            self.sm = Satzmessung.Satzmessung(self.alle_saetze) 
            
            print("Satzmessung beendet, Warteposition...")
            self.moveit(0,200) 
            print("Gute Nacht Tachymeter!")
            
        finally:
            print("Cleanup: Garantiertes Schließen der Verbindungen...")
            if hasattr(self, 'totalstation'):
                try:
                    self.totalstation.turn_off() 
                except Exception as e:
                    print(f"Warnung beim Abschalten: {e}")
                
                try:
                    self.totalstation.serialPort.close() 
                    print("Serieller Port erfolgreich freigegeben.")
                except Exception as e:
                    print(f"Warnung beim Port-Schließen: {e}")

    def _connect_with_retries(self):
        """Versucht bis zu 3-mal, eine stabile Verbindung aufzubauen."""
        max_retries = 3
        
        for versuch in range(max_retries):
            try:
                print(f"Verbindungsversuch {versuch + 1}/3 auf {self.ts_port}...")
                self.connect()
                
                print("Sende wake_up() Signal...")
                self.totalstation.wake_up()
                
                print("Warte 5 Sekunden auf Instrument...")
                time.sleep(5)
                
                # Testbefehl absenden, um Timeout abzufangen
                print("Prüfe Kommunikationsebene...")
                instr_name = self.totalstation.get_instrument_name()
                print(f"Erfolgreich verbunden mit: {instr_name}")
                
                # Wenn wir bis hierher kommen, war alles erfolgreich -> Schleife abbrechen
                return
                
            except Exception as e:
                print(f"Verbindungsfehler bei Versuch {versuch + 1}: {e}")
                
                # Port sicherheitshalber schließen, um ihn für den nächsten Versuch freizugeben
                if hasattr(self, 'totalstation'):
                    try:
                        self.totalstation.serialPort.close()
                    except:
                        pass
                
                if versuch < max_retries - 1:
                    print("Warte 10 Sekunden vor dem nächsten Versuch...")
                    time.sleep(10)
                    
        # Wenn die Schleife ohne 'return' durchläuft, schlug alles fehl
        raise ConnectionError("Abbruch: Tachymeter reagiert auch nach 3 Versuchen nicht auf Befehle.")

    def connect(self):
        self.totalstation = TotalStation(self.ts_port, baudrate=115200) 

    def moveit(self, ph, pv):
        self.totalstation.set_telescope_position(Angle.from_gon(ph%400), Angle.from_gon(pv%400), 
                                                 PositionMode.AUT_NORMAL, ATRMode.AUT_TARGET)

    def changeEDMmode(self, index):
        mode = EDMMeasurementMode.EDM_SINGLE_STANDARD if index == 0 else EDMMeasurementMode.EDM_SINGLE_SRANGE
        self.totalstation.set_edm_mode(mode)

    def set_prism_type(self, prism_type: BAPPrismenType):
        command = f"%R1Q,17008:{prism_type.value}"
        response = self.totalstation.request(command)
        return response[0]