import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import math
import json
import csv

from Satzmessung import Messung, Lage, Satz, Satzmessung
from ausgleichung import GaussMarkovAusgleichung

# Globalen Basispfad definieren
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def schreibe_neupunkte_csv(path, neupunkte):
    """Speichert die transformierten Neupunkte 1:1 wie im Hauptskript."""
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

def lade_rohdaten_aus_datei(dateiname):
    """
    Liest die Rohdaten ein. Nutzt BASE_DIR für absolute Pfadfindung.
    Entspricht der Struktur, die schreibe_rohdaten_csv im Hauptskript erzeugt.
    """
    pfad = os.path.join(BASE_DIR, "rohdaten", dateiname)
    
    if not os.path.exists(pfad):
        raise FileNotFoundError(f"Datei nicht gefunden: {pfad}")

    roh_saetze = {}

    with open(pfad, "r", encoding="utf-8") as f:
        next(f)  # Header überspringen: "Satz Lage PNR HZ[gon] VZ[gon] Dist[m]"
        for line in f:
            parts = line.split()
            if len(parts) < 6: continue
            
            s_idx = int(parts[0])
            lage_label = parts[1]
            pnr = parts[2]
            hz_gon = float(parts[3])
            vz_gon = float(parts[4])
            dist = float(parts[5]) *0.5

            # Umrechnung in Radiant (identisch zum Hauptskript)
            hz_rad = hz_gon * math.pi / 200
            vz_rad = vz_gon * math.pi / 200

            if s_idx not in roh_saetze:
                roh_saetze[s_idx] = {"L1": Lage(1), "L2": Lage(2)}
            
            m = Messung(pnr, hz_rad, vz_rad, dist)
            if lage_label == "I":
                roh_saetze[s_idx]["L1"].addMessung(m)
            else:
                roh_saetze[s_idx]["L2"].addMessung(m)
    
    return roh_saetze

def run_simulation(dateiname):
    # 1. Parameter laden (Pfade wie im Hauptskript)
    param_pfad = os.path.join(BASE_DIR, "parameter", "params.txt")
    
    if not os.path.exists(param_pfad):
        print(f"Fehler: params.txt nicht gefunden unter {param_pfad}")
        return

    with open(param_pfad, "r", encoding="utf-8") as f:
        params_raw = json.load(f)
    
    # Normalisierung wie im Hauptskript
    params = {k.upper(): v for k, v in params_raw.items()}
    config = params.get("PARAMS", {})
    config = {k.upper(): v for k, v in config.items()}

    # 2. Rohdaten parsen
    print(f"--- Starte Simulation für: {dateiname} ---")
    try:
        roh_daten = lade_rohdaten_aus_datei(dateiname)
    except FileNotFoundError as e:
        print(e)
        return
    
    liste_saetze = []
    for s_idx in sorted(roh_daten.keys()):
        # mittelLage() entspricht der Verarbeitung in der aufnahme.execute
        s_obj = Satz(roh_daten[s_idx]["L1"], roh_daten[s_idx]["L2"])
        s_obj.mittelLage()
        liste_saetze.append(s_obj)

    # 3. Satzmessung prozessieren
    sm = Satzmessung(liste_saetze)
    
    # Genauigkeiten aus der Config (identische Keys zum Hauptskript)
    s_hz = float(config.get("S_HZ_GON", 0.001)) * math.pi / 200
    s_vz = float(config.get("S_VZ_GON", 0.001)) * math.pi / 200
    s_dist = float(config.get("S_DIST_M", 0.002))
    s_dist_ppm = float(config.get("S_DIST_PPM", 1.0))
    s_winkel_off = float(config.get("S_WINKEL_OFFSET_M", 0.0005))

    sm.mittelSaetze(s_hz, s_vz, s_dist, s_dist_ppm, s_winkel_off)
    sm.rechneLokal(s_hz, s_vz, s_dist, s_dist_ppm, s_winkel_off)

    # 4. Ausgleichung
    try:
        # Übergabe der Soll-Koordinaten von der Hauptebene der JSON
        gma = GaussMarkovAusgleichung(sm.koor_lokal, params.get("SOLL_KOORDINATEN", []))
        gma.berechne_und_eliminiere_ausreisser()
        
        if gma.konvergiert:
            print("\n--- Ergebnis der Simulation ---")
            # Neupunkte berechnen
            neupunkte = gma.transformiere_neupunkte(sm.koor_lokal)
            
            # Ordner für Ergebnisse sicherstellen
            ergebnis_ordner = os.path.join(BASE_DIR, "ergebnisse")
            if not os.path.exists(ergebnis_ordner):
                os.makedirs(ergebnis_ordner)

            # CSV-Pfad generieren (z.B. simulation_neupunkte.csv)
            csv_name = dateiname.replace("rohdaten", "neupunkte").replace(".txt", ".csv")
            csv_path = os.path.join(ergebnis_ordner, f"sim_{csv_name}")

            # CSV schreiben
            schreibe_neupunkte_csv(csv_path, neupunkte)
            
            # Konsolen-Output zur Kontrolle
            for npkt in neupunkte:
                print(f"  PNR {npkt['PNR']:<10}: X={npkt['x']:10.4f}, Y={npkt['y']:10.4f}, Z={npkt['z']:10.4f}")
        else:
            print("Ausgleichung fehlgeschlagen.")

        
            
    except Exception as e:
        import traceback
        print(f"Fehler in der Ausgleichung: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    # Beispiel-Datei aus deinem Ordner 'rohdaten'
    DATEI = "260616_1340_rohdaten.txt" 
    run_simulation(DATEI)