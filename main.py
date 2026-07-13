import sys
from unittest.mock import MagicMock

# 1. Create the fake modules
sys.modules['board'] = MagicMock()
sys.modules['busio'] = MagicMock()

# 2. Create a specialized mock for the BMP sensor
fake_bmp_module = MagicMock()

# 3. Define what the simulated sensor should return when read
fake_bmp_module.BMP3XX_I2C.return_value.pressure = 1013.25
fake_bmp_module.BMP3XX_I2C.return_value.temperature = 22.5

# 4. Inject our smart mock into Python's system memory
sys.modules['adafruit_bmp3xx'] = fake_bmp_module

# Your original code starts here...
from sensor import Thermometer, PressureManager, ThermometerException

# Your original code starts here...
from sensor import Thermometer, PressureManager, ThermometerException



import os, math, json, csv, numpy as np
from datetime import datetime
from aufnahme_neu import execute
from ausgleichung import GaussMarkovAusgleichung
from Satzmessung import Satzmessung
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

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

def schreibe_ergebnis_pdf(path, gma, neupunkte):
    doc = SimpleDocTemplate(path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [Paragraph("Transformationsergebnisse", styles["Title"]), Spacer(1, 12)]
    status_text = "Status: Konvergenz erreicht." if gma.konvergiert else "ACHTUNG: Konvergenz GESCHEITERT!"
    color = colors.green if gma.konvergiert else colors.red
    story.append(Paragraph(f"<font color={color}>{status_text}</font>", styles["Normal"]))
    
    story.append(Paragraph("Parameter", styles["Heading2"]))
    p_data = [["Parameter", "Wert", "Std-Dev"]]
    labels = ['dX', 'dY', 'dZ', 'omega', 'phi', 'kappa']
    for i, label in enumerate(labels):
        val = gma.x[i] if i < 3 else gma.x[i] * 200/math.pi
        std = gma.std_dev[i] if i < 3 else gma.std_dev[i] * 200/math.pi
        unit = "[m]" if i < 3 else "[gon]"
        p_data.append([label, f"{val:.4f} {unit}", f"±{std:.6f}"])
    
    t1 = Table(p_data, hAlign='LEFT')
    t1.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.black), ('BACKGROUND',(0,0),(-1,0), colors.lightgrey)]))
    story.append(t1)

    if gma.konvergiert and neupunkte:
        story.append(Spacer(1, 20))
        story.append(Paragraph("Transformierte Neupunkte", styles["Heading2"]))
        n_data = [["PNR", "X", "Y", "Z"]] + [[p["PNR"], f"{p['x']:.4f}", f"{p['y']:.4f}", f"{p['z']:.4f}"] for p in neupunkte]
        t2 = Table(n_data, hAlign='LEFT')
        t2.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.black), ('BACKGROUND',(0,0),(-1,0), colors.lightblue)]))
        story.append(t2)
    
    doc.build(story)

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    params_raw = lade_parameter()
    zeit = datetime.now().strftime("%y%m%d_%H%M")
    for o in [ORDNER_RAW, ORDNER_RES]: 
        if not os.path.exists(o): os.makedirs(o)

    # --- Parameter-Struktur normalisieren ---
    # Alles auf Großbuchstaben für den sicheren Zugriff
    params = {k.upper(): v for k, v in params_raw.items()}
    
    # Extrahiere das Unter-Objekt "PARAMS" aus der JSON
    config = params.get("PARAMS", {})
    config = {k.upper(): v for k, v in config.items()}

    # --- Sensorwerte / Startwerte abrufen ---
    aktuelle_temp = float(config.get("START_TEMP", 20.0))
    aktueller_druck = float(config.get("START_DRUCK", 1013.25))
    anz_saetze = int(config.get("SAETZE", 1))

    p_manager = PressureManager()
    p_val, t_int = p_manager.get_data()
    if p_val is not None:
        aktueller_druck = p_val
        print(f"Sensor BMP388: {aktueller_druck:.1f} hPa")

    t_manager = Thermometer('/dev/ttyUSB1')
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
    # Wichtig: params["PKTLISTE"] kommt von der Hauptebene, anz_saetze aus config
    aufnahme = execute(params["PKTLISTE"], anz_saetze, temp=aktuelle_temp, druck=aktueller_druck)
    
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
                    # Fall A: Ziel ist ein Dictionary
                    if isinstance(ziel, dict):
                        z_pnr = str(ziel.get("pnr") or ziel.get("PNR") or "")
                        if z_pnr == mw_pnr and mw.get("HZ_red") is not None:
                            h_k = "hz" if "hz" in ziel else "HZ"
                            v_k = "vz" if "vz" in ziel else "VZ"
                            ziel[h_k] = round(mw["HZ_red"]*200/math.pi, 4)
                            ziel[v_k] = round(mw["VZ_red"]*200/math.pi, 4)
                    
                    # Fall B: Ziel ist eine Liste [PNR, HZ, VZ, ...]
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

        # PDF Bericht schreiben
        schreibe_ergebnis_pdf(os.path.join(ORDNER_RES, f"{zeit}.pdf"), gma, neupunkte)
        
    except Exception as e:
        # Falls es doch kracht, zeigt uns das 'import traceback' genau wo
        import traceback
        print(f"Fehler bei Ausgleichung/Export: {e}")
        traceback.print_exc()

if __name__ == "__main__": 
    main()
