import sys
import subprocess
import os, math, json, csv, numpy as np
from datetime import datetime
from aufnahme_neu import execute
from ausgleichung import GaussMarkovAusgleichung
from Satzmessung import Satzmessung
import berichte
import serial.tools.list_ports

"""
Dieses Modul ist das "Main"-Modul des ganzen Programms.
Alle relevanten Parameter können im Arbeitsverzeichnis unter /parameter/params.txt angepasst werden.
"""

# Import der Sensor-Klassen
from sensor import Thermometer, PressureManager, ThermometerException

PARAM_ORDNER = "parameter"
PARAM_DATEI = os.path.join(PARAM_ORDNER, "params.txt")
ORDNER_RAW = "rohdaten"
ORDNER_RES = "ergebnisse"



def finde_usb_ports():
    # Fallback-Ports, falls mal etwas nicht erkannt wird
    port_ts = '/dev/ttyUSB0' 
    port_temp = '/dev/ttyUSB1' 
    
    for p in serial.tools.list_ports.comports():
        # FTDI-Chip (0403:6001) -> Totalstation
        if p.vid == 0x0403 and p.pid == 0x6001:
            port_ts = p.device
            print(f"Totalstation gefunden an: {port_ts}")
            
        # Prolific-Chip (067B:23A3) -> Thermometer
        elif p.vid == 0x067B and p.pid == 0x23A3:
            port_temp = p.device
            print(f"Thermometer gefunden an: {port_temp}")
            
    return port_ts, port_temp

def lade_parameter():
    if not os.path.exists(PARAM_DATEI):
        if not os.path.exists(PARAM_ORDNER): os.makedirs(PARAM_ORDNER)
        data = {
            "_info": "Trick 1: Kommentar-Key",
            "PKTLISTE": [["FP_1", 0.0, 77.55, 0.0175], ["M_6", 187.15, 101.76, 0.0175]],
            "SOLL_KOORDINATEN": [{"PNR": "FP_1", "x": 10013.519, "y": 50000.0, "z": 105.143}],
            "S_HZ_GON": 0.001, "S_VZ_GON": 0.001, "S_DIST_M": 0.002,
            "ANZ_SAETZE": 3, "START_TEMP": 20.0, "START_DRUCK": 1013.25
        }
        speichere_parameter(data)
        return data
    with open(PARAM_DATEI, "r", encoding="utf-8") as f: return json.load(f)

def speichere_parameter(params):
    params["_last_update"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    with open(PARAM_DATEI, "w", encoding="utf-8") as f: json.dump(params, f, indent=4)

def schreibe_rohdaten_csv(path, aufnahme):
    """Speichert die Rohdaten als leerzeichengetrennte Datei."""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            # Header schreiben
            f.write("Satz Lage PNR HZ[gon] VZ[gon] Dist[m]\n")
            for s_idx, satz in enumerate(aufnahme.alle_saetze):
                for l_v, l_o in [("I", satz.lage1), ("II", satz.lage2)]:
                    for m in l_o.getMessungen():
                        hz_gon = f"{m.hz*200/math.pi:.4f}"
                        vz_gon = f"{m.vz*200/math.pi:.4f}"
                        dist = f"{m.dist:.4f}"
                        f.write(f"{s_idx+1} {l_v} {m.pnr} {hz_gon} {vz_gon} {dist}\n")
        print(f"Rohdaten-Export erfolgreich: {path}")
    except Exception as e:
        print(f"Fehler beim Rohdaten-Export: {e}")

def schreibe_neupunkte_csv(path, neupunkte):
    """Speichert die transformierten Neupunkte in eine CSV-Datei (Trennzeichen: Semikolon)."""
    if not neupunkte:
        return
    header = ["PNR", "X", "Y", "Z"]
    try:
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=header, delimiter=';')
            writer.writeheader()
            for p in neupunkte:
                writer.writerow({
                    "PNR": p["PNR"],
                    "X": f"{p['x']:.4f}",
                    "Y": f"{p['y']:.4f}",
                    "Z": f"{p['z']:.4f}"
                })
        print(f"CSV-Export erfolgreich: {path}")
    except Exception as e:
        print(f"Fehler beim CSV-Export: {e}")





def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    params_raw = lade_parameter()
    zeit = datetime.now().strftime("%y%m%d_%H%M")
    for o in [ORDNER_RAW, ORDNER_RES]: 
        if not os.path.exists(o): os.makedirs(o)

    # --- Parameter-Struktur normalisieren ---
    params = {k.upper(): v for k, v in params_raw.items()}
    
    config = params.get("PARAMS", {})
    config = {k.upper(): v for k, v in config.items()}

    # --- Sensorwerte / Startwerte abrufen ---
    port_ts, port_temp = finde_usb_ports()

    aktuelle_temp = float(config.get("START_TEMP", 20.0))
    aktueller_druck = float(config.get("START_DRUCK", 1013.25))
    anz_saetze = int(config.get("SAETZE", 1))



    p_manager = PressureManager()
    p_val, t_int = p_manager.get_data()
    if p_val is not None:
        aktueller_druck = p_val
        print(f"Sensor BMP388: {aktueller_druck:.1f} hPa")

    t_manager = Thermometer(port_temp)
    try:
        t_manager.Open()
        aktuelle_temp = t_manager.Temperature()
        print(f"Sensor USB-Temp: {aktuelle_temp:.2f} °C")
    except Exception as e:
        print(f"USB-Temp Fehler: {e}. Nutze Fallback.")
        if t_int is not None:
            aktuelle_temp = t_int
    finally:
        t_manager.Close()

    # Aufnahme starten
    aufnahme = execute(params["PKTLISTE"], anz_saetze, temp=aktuelle_temp, druck=aktueller_druck, ts_port=port_ts)
    
    # Berechnungen vorbereiten
    satzmessung = aufnahme.sm
    s_hz = float(config.get("S_HZ_GON", 0.001)) * math.pi / 200
    s_vz = float(config.get("S_VZ_GON", 0.001)) * math.pi / 200
    s_dist = float(config.get("S_DIST_M", 0.002))
    s_dist_ppm = float(config.get("S_DIST_PPM", 1.0))
    s_winkel_off = float(config.get("S_WINKEL_OFFSET_M", 0.0005))

    satzmessung.mittelSaetze(s_hz, s_vz, s_dist, s_dist_ppm, s_winkel_off)
    satzmessung.rechneLokal(s_hz, s_vz, s_dist, s_dist_ppm, s_winkel_off)

    # Rohdaten Export
    schreibe_rohdaten_csv(os.path.join(ORDNER_RAW, f"{zeit}_rohdaten.txt"), aufnahme)

    try:
        # Initialisierung der Ausgleichung
        gma = GaussMarkovAusgleichung(satzmessung.koor_lokal, params.get("SOLL_KOORDINATEN", []))
        gma.berechne_und_eliminiere_ausreisser()
        
        neupunkte = []
        if gma.konvergiert:
            # PKTLISTE Update (In-Memory)
            for mw in satzmessung.saetze_mittel:
                mw_pnr = str(mw.get("PNR") or "")
                if not mw_pnr: continue

                for ziel in params_raw.get("PKTLISTE", []):
                    if isinstance(ziel, dict):
                        z_pnr = str(ziel.get("pnr") or ziel.get("PNR") or "")
                        if z_pnr == mw_pnr and mw.get("HZ_red") is not None:
                            h_k = "hz" if "hz" in ziel else "HZ"
                            v_k = "vz" if "vz" in ziel else "VZ"
                            ziel[h_k] = round(mw["HZ_red"]*200/math.pi, 4)
                            ziel[v_k] = round(mw["VZ_red"]*200/math.pi, 4)
                    elif isinstance(ziel, list) and len(ziel) >= 3:
                        if str(ziel[0]) == mw_pnr and mw.get("HZ_red") is not None:
                            ziel[1] = round(mw["HZ_red"]*200/math.pi, 4)
                            ziel[2] = round(mw["VZ_red"]*200/math.pi, 4)
            
            # Parameter speichern
            speichere_parameter(params_raw)
            
            # Neupunkte berechnen
            neupunkte = gma.transformiere_neupunkte(satzmessung.koor_lokal)
            
            # CSV Export
            csv_path = os.path.join(ORDNER_RES, f"{zeit}_neupunkte.csv")
            schreibe_neupunkte_csv(csv_path, neupunkte)

            # --- AMBERG GEODATE EXPORT & UPLOAD ---
            ap_pnrs = {str(p.get("PNR") or p.get("pnr")) for p in params.get("SOLL_KOORDINATEN", [])}
            amberg_path = os.path.join(ORDNER_RES, f"{zeit}_amberg.csv")
            
            # NEU: Aufruf über das neue Modul
            berichte.schreibe_amberg_csv(amberg_path, neupunkte, ap_pnrs)

            # Upload-Skript aufrufen ...
            try:
                subprocess.Popen([sys.executable, "upload.py", amberg_path])
                print(f"Upload-Skript (upload.py) für {amberg_path} aufgerufen.")
            except Exception as e:
                print(f"Fehler beim Aufruf von upload.py: {e}")

        # NEU: Text Bericht schreiben (ersetzt PDF)
        # Übergebe params_raw, damit die Residuen anhand der SOLL_KOORDINATEN berechnet werden können
        txt_path = os.path.join(ORDNER_RES, f"{zeit}_ausgleichung.txt")
        berichte.schreibe_ausgleichung_txt(txt_path, gma, neupunkte, params_raw)
        
    except Exception as e:
        import traceback
        print(f"Fehler bei Ausgleichung/Export: {e}")
        traceback.print_exc()
if __name__ == "__main__": 
    main()