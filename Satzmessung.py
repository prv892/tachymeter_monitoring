import math as M
from datetime import datetime

"""
Hier erfolgt Datenverarbeitung und Mittelung
Anpassung: x = Rechtswert, y = Hochwert, z = Höhe
"""

class Messung:
    def __init__(self, pnr, hz, vz, dist):
        if not isinstance(pnr, str):
            raise TypeError("pnr muss ein String sein!")
        for wert in (hz, vz, dist):
            if not isinstance(wert, float):
                raise TypeError("hz, vz und dist müssen float sein!")

        self.pnr = pnr
        self.hz = hz
        self.vz = vz 
        self.dist = dist 
    
    def getMessung(self):
        output = {
                "PNR":self.pnr,
                "HZ":self.hz,
                "VZ":self.vz,
                "DIST":self.dist
        }
        return output 

class Lage:
    def __init__(self, lage): 
        if lage == 1:
            self.lage = 1
        elif lage == 2:
            self.lage = 2
        else:
            raise ValueError("Lage muss =1 oder =2 sein!") 
        
        self.messungsliste = []

    def addMessung(self,messung):
        if not isinstance(messung, Messung):
            raise Exception("messung muss vom Typ Messung sein!")
        self.messungsliste.append(messung)

    def getLage(self):
        return self.lage

    def getMessungen(self):
        return self.messungsliste

class Satz:
    def __init__(self, lage1, lage2):
        if not isinstance(lage1, Lage) or not isinstance(lage2, Lage):
            raise Exception("Lagen müssen Objekte der Klasse Lage sein!")
        
        self.lage1 = lage1
        self.lage2 = lage2
        self.lagenmittel = []
    
    def mittelLage(self):
        l1 = self.lage1.getMessungen()
        l2 = self.lage2.getMessungen()

        if not len(l1) == len(l2):
            raise Exception("Ungleiche Anzahl an Messungen in den Lagen!")

        for i in range(len(l1)):
            ml1 = l1[i].getMessung() 
            pnr = ml1["PNR"]

            index_l2 = next((j for j, m in enumerate(l2) if m.getMessung()["PNR"] == pnr), None)
            if index_l2 is None:
                raise Exception(f"Punkt {pnr} nicht in Lage 2 gefunden")
            ml2 = l2[index_l2].getMessung()

            hz1, hz2 = ml1["HZ"], ml2["HZ"]
            vz1, vz2 = ml1["VZ"], ml2["VZ"]
            dist1, dist2 = ml1["DIST"], ml2["DIST"]   

            # Winkelmittelung (Einheit: rad)
            if hz1 < hz2:
                mw_hz = (hz1 + hz2 - M.pi) / 2
            else:
                mw_hz = (hz1 + hz2 + M.pi) / 2
            
            mw_vz = (vz1 + (M.pi * 2) - vz2) / 2
            #print(pnr)
            #print(dist1)
            #print(dist2)
            mw_dist = (dist1 + dist2) / 2
            
            # Toleranzcheck (0.5 gon / 0.5 cm)
            tol_w = (M.pi / 200) * 0.5 
            tol_s = 0.01 * 0.5

            hz_ok = abs(mw_hz - hz1) <= tol_w
            vz_ok = abs(mw_vz - vz1) <= tol_w
            dist_ok = abs(mw_dist - dist1) <= tol_s

            if hz_ok and vz_ok and dist_ok:
                mw = {
                    "PNR": pnr,
                    "HZ_red": mw_hz,
                    "VZ_red": mw_vz,
                    "DIST_red": mw_dist
                }
                self.lagenmittel.append(mw)
            else:
                print(f"Punkt {pnr}: Lage-Toleranz überschritten!")
    
    def getLagenmittel(self):
        return self.lagenmittel

class Satzmessung:
    def __init__(self, saetze):
        for s in saetze:
            if not isinstance(s, Satz):
                raise Exception("Objekt in saetze nicht vom typ Satz!")
        self.saetze = saetze
        self.anz = len(saetze)
    
    def mittelSaetze(self, s_hz_base, s_vz_base, s_dist_base, s_dist_ppm, s_winkel_offset_m):
        alle_punkte = sorted({m["PNR"] for s in self.saetze for m in s.lagenmittel})
        self.saetze_mittel = []

        for pz in alle_punkte:
            hzl, vzl, distl = [], [], []
            for s in self.saetze:
                eintrag = next((m for m in s.lagenmittel if m["PNR"] == pz), None)
                if eintrag:
                    hzl.append(eintrag["HZ_red"])
                    vzl.append(eintrag["VZ_red"])
                    distl.append(eintrag["DIST_red"])

            if not hzl: continue 

            mw_hz = sum(hzl) / len(hzl)
            mw_vz = sum(vzl) / len(vzl)
            mw_dist = sum(distl) / len(distl)

            s_dist_eff = s_dist_base + (mw_dist * s_dist_ppm * 1e-6)
            s_hz_eff = M.sqrt(s_hz_base**2 + (s_winkel_offset_m / mw_dist)**2)
            s_vz_eff = M.sqrt(s_vz_base**2 + (s_winkel_offset_m / mw_dist)**2)

            hz_ok = all(abs(mw_hz - v) <= 2 * s_hz_eff for v in hzl)
            vz_ok = all(abs(mw_vz - v) <= 2 * s_vz_eff for v in vzl)
            dist_ok = all(abs(mw_dist - v) <= 2 * s_dist_eff for v in distl)

            if hz_ok and vz_ok and dist_ok:
                self.saetze_mittel.append({
                    "PNR": pz, "HZ_red": mw_hz, "VZ_red": mw_vz, "DIST_red": mw_dist
                })

    def rechneLokal(self, s_hz_base, s_vz_base, s_dist_base, s_dist_ppm, s_winkel_offset_m):
        # Beispiel-Standpunkt (Rechts, Hoch, Höhe)
        self.SP_lokal = (0, 0, 0)
        self.koor_lokal = []

        for messung in self.saetze_mittel:
            pnr, hz, vz, dist = messung["PNR"], messung["HZ_red"], messung["VZ_red"], messung["DIST_red"]

            # --- 1. Koordinatenberechnung (Geodätisch) ---
            # x = Rechtswert (East), y = Hochwert (North)
            dx = dist * M.sin(vz) * M.sin(hz)
            dy = dist * M.sin(vz) * M.cos(hz)
            dz = dist * M.cos(vz) 

            x = self.SP_lokal[0] + dx
            y = self.SP_lokal[1] + dy
            z = self.SP_lokal[2] + dz

            # --- 2. Genauigkeiten ---
            s_dist_eff = s_dist_base + (dist * s_dist_ppm * 1e-6)
            s_hz_eff = M.sqrt(s_hz_base**2 + (s_winkel_offset_m / dist)**2)
            s_vz_eff = M.sqrt(s_vz_base**2 + (s_winkel_offset_m / dist)**2)
            
            # --- 3. Partielle Ableitungen (Jacobi) ---
            # Ableitungen für x (Rechtswert)
            dx_dhz = dist * M.sin(vz) * M.cos(hz)
            dx_dvz = dist * M.cos(vz) * M.sin(hz)
            dx_dsd = M.sin(vz) * M.sin(hz)

            # Ableitungen für y (Hochwert)
            dy_dhz = -dist * M.sin(vz) * M.sin(hz)
            dy_dvz = dist * M.cos(vz) * M.cos(hz)
            dy_dsd = M.sin(vz) * M.cos(hz)

            # Ableitungen für z (Höhe)
            dz_dhz = 0
            dz_dvz = -dist * M.sin(vz)
            dz_dsd = M.cos(vz)

            # --- 4. Varianz-Kovarianz-Matrix Qll ---
            var_x = (dx_dhz**2 * s_hz_eff**2) + (dx_dvz**2 * s_vz_eff**2) + (dx_dsd**2 * s_dist_eff**2)
            var_y = (dy_dhz**2 * s_hz_eff**2) + (dy_dvz**2 * s_vz_eff**2) + (dy_dsd**2 * s_dist_eff**2)
            var_z = (dz_dhz**2 * s_hz_eff**2) + (dz_dvz**2 * s_vz_eff**2) + (dz_dsd**2 * s_dist_eff**2)
            
            cov_xy = (dx_dhz * dy_dhz * s_hz_eff**2) + (dx_dvz * dy_dvz * s_vz_eff**2) + (dx_dsd * dy_dsd * s_dist_eff**2)
            cov_xz = (dx_dhz * dz_dhz * s_hz_eff**2) + (dx_dvz * dz_dvz * s_vz_eff**2) + (dx_dsd * dz_dsd * s_dist_eff**2)
            cov_yz = (dy_dhz * dz_dhz * s_hz_eff**2) + (dy_dvz * dz_dvz * s_vz_eff**2) + (dy_dsd * dz_dsd * s_dist_eff**2)

            qll = [
                [var_x, cov_xy, cov_xz],
                [cov_xy, var_y, cov_yz],
                [cov_xz, cov_yz, var_z]
            ]

            self.koor_lokal.append({
                "PNR": pnr, "x": x, "y": y, "z": z, "qll": qll
            })