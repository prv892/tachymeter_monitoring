import os
import sys
import subprocess
from datetime import datetime

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

def schreibe_amberg_csv(path, neupunkte, ap_pnrs):
    """Speichert die reinen Neupunkte im Amberg Geodate Format."""
    if not neupunkte:
        return
    
    echte_neupunkte = [p for p in neupunkte if str(p["PNR"]) not in ap_pnrs]
    if not echte_neupunkte:
        return
        
    dt_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write("DateTime;SensorName;CustomerName;Flags;SensorType;Unit;East;North;Height;km;VALUE1;VALUE2;VALUE3;CULTURE:US\n")
            for p in echte_neupunkte:
                # Format: DateTime;PNR;;;Prism;m;;;;;X;Y;Z;;;
                f.write(f"{dt_str};{p['PNR']};;;Prism;m;;;;;{p['x']:.3f};{p['y']:.3f};{p['z']:.3f};;;\n")
        print(f"Amberg Geodate Export erfolgreich: {path}")
    except Exception as e:
        print(f"Fehler beim Amberg Geodate Export: {e}")


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
            dist = float(parts[5]) 
            hz_gon = float(parts[3])
            vz_gon = float(parts[4])

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

    # --- ZUSÄTZLICHE AUSGABE: Soll-Koordinaten ---
    print(f"\n{'='*50}\n--- 1. GELADENE SOLL-KOORDINATEN ---")
    soll_coords = params.get("SOLL_KOORDINATEN", [])
    for pkt in soll_coords:
        print(f"  PNR {pkt.get('PNR', pkt.get('pnr')):<5}: X={pkt.get('x'):12.3f}, Y={pkt.get('y'):12.3f}, Z={pkt.get('z'):12.3f}")
    
    # 2. Rohdaten parsen
    print(f"\n{'='*50}\n--- 2. ROHDATEN PARSEN ({dateiname}) ---")
    try:
        roh_daten = lade_rohdaten_aus_datei(dateiname)
        print(f"  Erfolgreich {len(roh_daten)} Satz/Sätze geladen.")
    except FileNotFoundError as e:
        print(e)
        return
    
    liste_saetze = []
    for s_idx in sorted(roh_daten.keys()):
        s_obj = Satz(roh_daten[s_idx]["L1"], roh_daten[s_idx]["L2"])
        s_obj.mittelLage()
        liste_saetze.append(s_obj)

    # 3. Satzmessung prozessieren
    sm = Satzmessung(liste_saetze)
    
    s_hz = float(config.get("S_HZ_GON", 0.001)) * math.pi / 200
    s_vz = float(config.get("S_VZ_GON", 0.001)) * math.pi / 200
    s_dist = float(config.get("S_DIST_M", 0.002))
    s_dist_ppm = float(config.get("S_DIST_PPM", 1.0))
    s_winkel_off = float(config.get("S_WINKEL_OFFSET_M", 0.0005))

    sm.mittelSaetze(s_hz, s_vz, s_dist, s_dist_ppm, s_winkel_off)
    
    # --- ZUSÄTZLICHE AUSGABE: Gemittelte Sätze (Lage I/II) ---
    print(f"\n{'='*50}\n--- 3. BERECHNETE SATZMITTEL (Nach Lagen- & Satzmittelung) ---")
    print(f"  {'PNR':<5} | {'HZ [gon]':<12} | {'VZ [gon]':<12} | {'DIST [m]':<10}")
    print("  " + "-"*45)
    for mw in sm.saetze_mittel:
        hz_gon = (mw.get("HZ_red", 0) * 200 / math.pi)
        vz_gon = (mw.get("VZ_red", 0) * 200 / math.pi)
        dist_m = mw.get("Dist", mw.get("DIST", mw.get("dist", 0.0)))
        print(f"  {mw.get('PNR'):<5} | {hz_gon:12.4f} | {vz_gon:12.4f} | {dist_m:10.4f}")

    sm.rechneLokal(s_hz, s_vz, s_dist, s_dist_ppm, s_winkel_off)

    # --- ZUSÄTZLICHE AUSGABE: Lokale Koordinaten ---
    print(f"\n{'='*50}\n--- 4. BERECHNETE LOKALE KOORDINATEN (Tachymeter-System) ---")
    print(f"  {'PNR':<5} | {'x_lokal':<10} | {'y_lokal':<10} | {'z_lokal':<10}")
    print("  " + "-"*45)
    for lokal_pkt in sm.koor_lokal:
        print(f"  {lokal_pkt.get('PNR'):<5} | {lokal_pkt.get('x'):10.4f} | {lokal_pkt.get('y'):10.4f} | {lokal_pkt.get('z'):10.4f}")

    # 4. Ausgleichung
    print(f"\n{'='*50}\n--- 5. GAUSS-MARKOV AUSGLEICHUNG (Transformation) ---")
    try:
        gma = GaussMarkovAusgleichung(sm.koor_lokal, params.get("SOLL_KOORDINATEN", []))
        gma.berechne_und_eliminiere_ausreisser()
        
        # --- ZUSÄTZLICHE AUSGABE: Parameter & Status ---
        if hasattr(gma, "x") and gma.x is not None and len(gma.x) >= 6:
            print("  Berechnete Transformationsparameter:")
            print(f"    TX    = {gma.x[0]:12.4f} m")
            print(f"    TY    = {gma.x[1]:12.4f} m")
            print(f"    TZ    = {gma.x[2]:12.4f} m")
            print(f"    Omega = {gma.x[3]*200/math.pi:12.4f} gon")
            print(f"    Phi   = {gma.x[4]*200/math.pi:12.4f} gon")
            print(f"    Kappa = {gma.x[5]*200/math.pi:12.4f} gon")
        
        if gma.konvergiert:
            print(f"\n  >> STATUS: Konvergenz ERFOLGREICH! <<")
            print(f"{'='*50}\n--- 6. FINALE NEUPUNKTE (Globales System) ---")
            
            # Neupunkte berechnen
            neupunkte = gma.transformiere_neupunkte(sm.koor_lokal)
            
            # Ordner für Ergebnisse sicherstellen
            ergebnis_ordner = os.path.join(BASE_DIR, "ergebnisse")
            if not os.path.exists(ergebnis_ordner):
                os.makedirs(ergebnis_ordner)

            # CSV-Pfad generieren
            csv_name = dateiname.replace("rohdaten", "neupunkte").replace(".txt", ".csv")
            csv_path = os.path.join(ergebnis_ordner, f"sim_{csv_name}")
            schreibe_neupunkte_csv(csv_path, neupunkte)
            
            # --- AMBERG GEODATE EXPORT & UPLOAD ---
            ap_pnrs = {str(p.get("PNR") or p.get("pnr")) for p in params.get("SOLL_KOORDINATEN", [])}
            amberg_csv_name = dateiname.replace("rohdaten", "amberg").replace(".txt", ".csv")
            amberg_path = os.path.join(ergebnis_ordner, f"sim_{amberg_csv_name}")
            schreibe_amberg_csv(amberg_path, neupunkte, ap_pnrs)
            
            try:
                subprocess.Popen([sys.executable, "upload.py", amberg_path])
                print(f"Upload-Skript (upload.py) für {amberg_path} aufgerufen.")
            except Exception as e:
                print(f"Fehler beim Aufruf von upload.py: {e}")
            
            # Konsolen-Output zur Kontrolle
            print(f"\n  {'PNR':<5} | {'X_global':<14} | {'Y_global':<14} | {'Z_global':<14}")
            print("  " + "-"*55)
            for npkt in neupunkte:
                print(f"  {npkt['PNR']:<5} | {npkt['x']:14.4f} | {npkt['y']:14.4f} | {npkt['z']:14.4f}")

            # --- ZUSÄTZLICHE AUSGABE: Residuen an den Passpunkten ---
            print(f"\n{'='*50}\n--- 7. RESIDUEN AN DEN PASSPUNKTEN (Soll - Ist) ---")
            print(f"  {'PNR':<5} | {'dX [m]':<10} | {'dY [m]':<10} | {'dZ [m]':<10} | {'3D-Abw [m]':<10}")
            print("  " + "-"*65)
            
            # dictionary für schnellen zugriff auf die Soll-Koordinaten bauen
            soll_dict = {str(p.get("PNR", p.get("pnr"))): p for p in params.get("SOLL_KOORDINATEN", [])}
            
            for npkt in neupunkte:
                pnr_str = str(npkt.get("PNR"))
                if pnr_str in soll_dict:
                    soll = soll_dict[pnr_str]
                    dx = soll["x"] - npkt["x"]
                    dy = soll["y"] - npkt["y"]
                    dz = soll["z"] - npkt["z"]
                    d3 = math.sqrt(dx**2 + dy**2 + dz**2)
                    print(f"  {pnr_str:<5} | {dx:10.4f} | {dy:10.4f} | {dz:10.4f} | {d3:10.4f}")

        else:
            print(f"\n  >> STATUS: Konvergenz FEHLGESCHLAGEN (Nicht genügend/gute Passpunkte) <<")
            
    except Exception as e:
        import traceback
        print(f"Fehler in der Ausgleichung: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    # Beispiel-Datei aus deinem Ordner 'rohdaten'
    DATEI = "260808_1530_rohdaten.txt" 
    run_simulation(DATEI)