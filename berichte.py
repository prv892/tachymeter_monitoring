import os
import math
import numpy as np
from datetime import datetime

def schreibe_amberg_csv(path, neupunkte, ap_pnrs):
    """Speichert die reinen Neupunkte im Amberg Geodata Format."""
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
        print(f"Fehler beim Amberg Geodata Export: {e}")


def schreibe_ausgleichung_txt(path, gma, neupunkte, params):
    """
    Erstellt eine formatierte Textdatei mit Iterationen, Parametern, Ausreißern und Residuen.
    """
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write(" BERICHT: GAUSS-MARKOV AUSGLEICHUNG\n")
            f.write("="*70 + "\n\n")

            # 1. Status & Globale Statistik
            status = "GMM konvergiert" if getattr(gma, 'konvergiert', False) else "ACHTUNG: Konvergenz GESCHEITERT!"
            
            f.write(f"Status der Ausgleichung : {status}\n")
            f.write(f"Ausgleichungs-Durchläufe: {getattr(gma, 'protokoll_iterationen', 'Unbekannt')}\n")
            
            s0 = getattr(gma, 's0', 0.0)
            f.write(f"Sigma 0 (s0)            : {s0:.6f} m\n")
            f.write(f"Sigma 0 Quadrat (s0²)   : {s0**2:.12f} m²\n")
            if s0 > 0:
                f.write(f"1 / s0²                 : {1/(s0**2):.12f}\n")
            f.write("\n")

            # 2. Iterationen & Eliminierte Punkte / Ausreißer
            f.write("--- Protokoll der Ausreißer-Eliminierung ---\n")
            elim_protokoll = getattr(gma, 'eliminierungs_protokoll', [])
            if elim_protokoll:
                for ep in elim_protokoll:
                    f.write(f"  Durchlauf {ep['iteration']}: Punkt '{ep['pnr']}' eliminiert.\n")
                    f.write(f"    Grund: 2-Sigma-Verletzung (Faktor {ep['violation']:.2f})\n")
                    if ep['residuen'] is not None:
                        res_x, res_y, res_z = ep['residuen']
                        res_3d = math.sqrt(res_x**2 + res_y**2 + res_z**2)
                        f.write(f"    Residuen vor Eliminierung: dX={res_x:.4f}m, dY={res_y:.4f}m, dZ={res_z:.4f}m (3D={res_3d:.4f}m)\n")
                    f.write("\n")
            else:
                f.write("  Alle Punkte in ihrer a priori 2-Sigma Umgebung. Keine Punkte eliminiert.\n\n")

            # 3. Transformationsparameter der finalen Ausgleichung
            f.write("--- Finale Transformationsparameter ---\n")
            if hasattr(gma, 'x') and gma.x is not None and len(gma.x) >= 6:
                labels = ['TX', 'TY', 'TZ', 'Omega', 'Phi', 'Kappa']
                for i, label in enumerate(labels):
                    val = gma.x[i] if i < 3 else gma.x[i] * 200 / math.pi
                    
                    std = 0.0
                    if hasattr(gma, 'std_dev') and gma.std_dev is not None and len(gma.std_dev) > i:
                        std = gma.std_dev[i] if i < 3 else gma.std_dev[i] * 200 / math.pi
                        
                    unit = "[m]  " if i < 3 else "[gon]"
                    f.write(f"  {label:<5} = {val:12.4f} {unit} (Std-Abw: ± {std:.6f})\n")
            else:
                f.write("  Keine Parameter berechnet.\n")
            f.write("\n")

            # 4. Residuen der final verbliebenen Passpunkte
            f.write("--- Residuen der finalen Passpunkte (Soll - Ist) ---\n")
            f.write(f"  {'PNR':<10} | {'dX [m]':<10} | {'dY [m]':<10} | {'dZ [m]':<10} | {'3D-Abw [m]':<10}\n")
            f.write("  " + "-"*65 + "\n")
            
            hat_residuen = False
            final_ap_pnrs = []
            
            if hasattr(gma, 'punkte') and getattr(gma, 'konvergiert', False):
                dX_t, dY_t, dZ_t, om, ph, ka = gma.x
                R = gma.calculate_R(om, ph, ka)
                
                # Wir gehen alle Punkte durch, die die GMM-Klasse intern als FINALE Passpunkte hält
                for p in gma.punkte:
                    pnr_str = str(p['PNR'])
                    final_ap_pnrs.append(pnr_str)
                    
                    # Residuen (Soll - Ist) exakt berechnen wie bei der Konsolenausgabe
                    g_ber = np.array([dX_t, dY_t, dZ_t]) + R @ p['l']
                    v = p['g'] - g_ber
                    
                    dx, dy, dz = v[0], v[1], v[2]
                    d3 = math.sqrt(dx**2 + dy**2 + dz**2)
                    
                    f.write(f"  {pnr_str:<10} | {dx:10.4f} | {dy:10.4f} | {dz:10.4f} | {d3:10.4f}\n")
                    hat_residuen = True
                    
            if not hat_residuen:
                f.write("  Keine finalen Passpunkt-Residuen zur Berechnung gefunden.\n")
            f.write("\n")

            # 5. Transformierte Neupunkte
            f.write("--- Transformierte Neupunkte (Globales System) ---\n")
            f.write(f"  {'PNR':<10} | {'X':<14} | {'Y':<14} | {'Z':<14}\n")
            f.write("  " + "-"*56 + "\n")
            
            # Alle echten Neupunkte filtern, die KEINE Passpunkte waren 
            # (bzw. Passpunkte, die eliminiert wurden, gelten ab sofort auch wieder als "Neupunkt"!)
            echte_neupunkte = [p for p in neupunkte if str(p.get("PNR", p.get("pnr", ""))) not in final_ap_pnrs]
            
            if echte_neupunkte:
                for npkt in echte_neupunkte:
                    pnr = npkt.get('PNR', npkt.get('pnr', ''))
                    f.write(f"  {pnr:<10} | {npkt['x']:14.4f} | {npkt['y']:14.4f} | {npkt['z']:14.4f}\n")
            else:
                f.write("  Keine separaten Neupunkte (außer den Passpunkten) transformiert.\n")

        print(f"Text-Bericht der Ausgleichung erfolgreich erstellt: {path}")
    except Exception as e:
        print(f"Fehler beim Erstellen des Text-Berichts: {e}")