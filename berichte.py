import os
import math
from datetime import datetime

def schreibe_amberg_csv(path, neupunkte, ap_pnrs):
    """Speichert die reinen Neupunkte im Amberg Geodate Format. (Struktur unverändert)"""
    if not neupunkte:
        return
    
    # Nur Neupunkte ausgeben, keine APS (Festpunkte)
    echte_neupunkte = [p for p in neupunkte if str(p.get("PNR", p.get("pnr", ""))) not in ap_pnrs]
    if not echte_neupunkte:
        return
        
    dt_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write("DateTime;SensorName;CustomerName;Flags;SensorType;Unit;East;North;Height;km;VALUE1;VALUE2;VALUE3;CULTURE:US\n")
            for p in echte_neupunkte:
                pnr = p.get('PNR', p.get('pnr', ''))
                # Format: DateTime;PNR;;;Prism;m;;;;;X;Y;Z;;;
                f.write(f"{dt_str};{pnr};;;Prism;m;;;;;{p['x']:.3f};{p['y']:.3f};{p['z']:.3f};;;\n")
        print(f"Amberg Geodate Export erfolgreich: {path}")
    except Exception as e:
        print(f"Fehler beim Amberg Geodate Export: {e}")


def schreibe_ausgleichung_txt(path, gma, neupunkte, params):
    """
    Erstellt eine formatierte Textdatei mit Iterationen, Parametern, Ausreißern und Residuen.
    """
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write(" BERICHT: GAUSS-MARKOV AUSGLEICHUNG\n")
            f.write("="*70 + "\n\n")

            # 1. Status & Iterationen
            status = "Konvergenz ERREICHT" if getattr(gma, 'konvergiert', False) else "ACHTUNG: Konvergenz GESCHEITERT!"
            iterationen = getattr(gma, 'iterationen', 'Nicht erfasst')
            
            f.write(f"Status der Ausgleichung : {status}\n")
            f.write(f"Anzahl Iterationen      : {iterationen}\n\n")

            # 2. Transformationsparameter
            f.write("--- Transformationsparameter ---\n")
            if hasattr(gma, 'x') and gma.x is not None and len(gma.x) >= 6:
                labels = ['TX', 'TY', 'TZ', 'Omega', 'Phi', 'Kappa']
                for i, label in enumerate(labels):
                    val = gma.x[i] if i < 3 else gma.x[i] * 200 / math.pi
                    
                    std = 0.0
                    if hasattr(gma, 'std_dev') and gma.std_dev and len(gma.std_dev) > i:
                        std = gma.std_dev[i] if i < 3 else gma.std_dev[i] * 200 / math.pi
                        
                    unit = "[m]  " if i < 3 else "[gon]"
                    f.write(f"  {label:<5} = {val:12.4f} {unit} (Std-Abw: ± {std:.6f})\n")
            else:
                f.write("  Keine Parameter berechnet.\n")
            f.write("\n")

            # 3. Eliminierte Punkte / Ausreißer
            f.write("--- Eliminierte Punkte (Ausreißer) ---\n")
            elim_punkte = getattr(gma, 'ausreisser', getattr(gma, 'eliminierte_punkte', []))
            if elim_punkte:
                for ep in elim_punkte:
                    f.write(f"  - {ep}\n")
            else:
                f.write("  Keine Ausreißer erkannt / Punkte eliminiert.\n")
            f.write("\n")

            # 4. Residuen an den Passpunkten (Soll - Ist)
            f.write("--- Residuen an den Passpunkten (Soll - Ist) ---\n")
            soll_coords = params.get("SOLL_KOORDINATEN", [])
            soll_dict = {str(p.get("PNR", p.get("pnr"))): p for p in soll_coords}
            
            f.write(f"  {'PNR':<8} | {'dX [m]':<10} | {'dY [m]':<10} | {'dZ [m]':<10} | {'3D-Abw [m]':<10}\n")
            f.write("  " + "-"*65 + "\n")
            
            hat_residuen = False
            for npkt in neupunkte:
                pnr_str = str(npkt.get("PNR", npkt.get("pnr", "")))
                if pnr_str in soll_dict:
                    soll = soll_dict[pnr_str]
                    dx = soll.get("x", 0.0) - npkt["x"]
                    dy = soll.get("y", 0.0) - npkt["y"]
                    dz = soll.get("z", 0.0) - npkt["z"]
                    d3 = math.sqrt(dx**2 + dy**2 + dz**2)
                    f.write(f"  {pnr_str:<8} | {dx:10.4f} | {dy:10.4f} | {dz:10.4f} | {d3:10.4f}\n")
                    hat_residuen = True
                    
            if not hat_residuen:
                f.write("  Keine Passpunkt-Residuen zur Berechnung gefunden.\n")
            f.write("\n")

            # 5. Transformierte Neupunkte
            f.write("--- Transformierte Neupunkte (Globales System) ---\n")
            f.write(f"  {'PNR':<8} | {'X':<14} | {'Y':<14} | {'Z':<14}\n")
            f.write("  " + "-"*56 + "\n")
            for npkt in neupunkte:
                pnr = npkt.get('PNR', npkt.get('pnr', ''))
                f.write(f"  {pnr:<8} | {npkt['x']:14.4f} | {npkt['y']:14.4f} | {npkt['z']:14.4f}\n")

        print(f"Text-Bericht der Ausgleichung erfolgreich erstellt: {path}")
    except Exception as e:
        print(f"Fehler beim Erstellen des Text-Berichts: {e}")