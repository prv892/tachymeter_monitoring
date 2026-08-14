import numpy as np
from scipy.linalg import block_diag

class GaussMarkovAusgleichung:
    def __init__(self, koor_lokal: list, koor_global_soll: list):
        # Flexibles Mapping der Keys (pnr/PNR und x/y/z/X/Y/Z)
        pnr_g = {str(p.get('pnr') or p.get('PNR')): p for p in koor_global_soll}
        self.punkte = []
        
        for p_l in koor_lokal:
            pnr = str(p_l.get('pnr') or p_l.get('PNR'))
            if pnr in pnr_g:
                p_g = pnr_g[pnr]
                try:
                    l_vec = np.array([float(p_l['x']), float(p_l['y']), float(p_l['z'])])
                    g_vec = np.array([
                        float(p_g.get('x', p_g.get('X'))), 
                        float(p_g.get('y', p_g.get('Y'))), 
                        float(p_g.get('z', p_g.get('Z')))
                    ])
                    # Nutze Qll falls vorhanden, sonst Einheitsmatrix (geringes Rauschen)
                    qll = p_l.get('qll', np.eye(3) * 1e-6)
                    self.punkte.append({'PNR': pnr, 'l': l_vec, 'g': g_vec, 'qll': qll})
                except (KeyError, ValueError) as e:
                    print(f"Fehler beim Einlesen von Punkt {pnr}: {e}")

        if len(self.punkte) < 4:
            raise ValueError(f"Mindestens 4 gemeinsame Passpunkte nötig. Gefunden: {len(self.punkte)}")

        self.konvergiert = False
        self.x = np.zeros(6) # dX, dY, dZ, omega, phi, kappa
        self.s0 = 0.0
        self.std_dev = np.zeros(6)
        
        
        self.protokoll_iterationen = 0
        self.eliminierungs_protokoll = []

    def berechne_naeherungswerte(self):
        """Stabilere Näherungswerte durch Schwerpunktzentrierung"""
        mean_l = np.mean([p['l'] for p in self.punkte], axis=0)
        mean_g = np.mean([p['g'] for p in self.punkte], axis=0)
        
        # Translation
        dT = mean_g - mean_l
        
        # Grobe Drehung Kappa (rz) über die ersten zwei Punkte
        p1, p2 = self.punkte[0], self.punkte[1]
        bearing_l = np.arctan2(p2['l'][1] - p1['l'][1], p2['l'][0] - p1['l'][0])
        bearing_g = np.arctan2(p2['g'][1] - p1['g'][1], p2['g'][0] - p1['g'][0])
        ka_start = bearing_g - bearing_l
        
        return np.array([dT[0], dT[1], dT[2], 0.0, 0.0, ka_start])

    def calculate_R(self, om, ph, ka):
        """Präzise Rotationsmatrix Rz * Ry * Rx (Rechtssystem)"""
        co, so = np.cos(om), np.sin(om)
        cp, sp = np.cos(ph), np.sin(ph)
        ck, sk = np.cos(ka), np.sin(ka)
        
        R = np.zeros((3, 3))
        R[0,0] = cp*ck
        R[0,1] = -cp*sk
        R[0,2] = sp
        R[1,0] = co*sk + so*sp*ck
        R[1,1] = co*ck - so*sp*sk
        R[1,2] = -so*cp
        R[2,0] = so*sk - co*sp*ck
        R[2,1] = so*ck + co*sp*sk
        R[2,2] = co*cp
        return R

    def iterative_loesung(self):
        max_iter = 50
        konvergenz_limit = 1e-8
        self.x = self.berechne_naeherungswerte()
        
        for i in range(max_iter):
            dX, dY, dZ, om, ph, ka = self.x
            R = self.calculate_R(om, ph, ka)
            
            A_list, l_list, P_list = [], [], []
            for p in self.punkte:
                L_rotated = R @ p['l']
                f_i = np.array([dX, dY, dZ]) + L_rotated
                v_i = p['g'] - f_i # Beobachtungsrestklaffung (l - f(x))
                
                Ai = np.zeros((3, 6))
                Ai[0:3, 0:3] = np.eye(3) # Ableitung nach dX, dY, dZ
                
                # Partielle Ableitungen nach Rotationswinkeln (analytisch angenähert)
                Ai[0, 4] =  L_rotated[2];  Ai[0, 5] = -L_rotated[1]
                Ai[1, 3] = -L_rotated[2];  Ai[1, 5] =  L_rotated[0]
                Ai[2, 3] =  L_rotated[1];  Ai[2, 4] = -L_rotated[0]
                
                A_list.append(Ai)
                l_list.append(v_i)
                P_list.append(np.linalg.inv(p['qll']))

            A = np.vstack(A_list)
            l = np.hstack(l_list)
            P = block_diag(*P_list)

            N = A.T @ P @ A
            n = A.T @ P @ l
            
            try:
                delta_x = np.linalg.solve(N, n)
            except np.linalg.LinAlgError:
                return False

            self.x += delta_x 
            if np.linalg.norm(delta_x) < konvergenz_limit:
                # Abschlussrechnung
                v_res = A @ delta_x - l
                freiheitsgrad = len(l) - 6
                if freiheitsgrad > 0:
                    self.s0 = np.sqrt((v_res.T @ P @ v_res) / freiheitsgrad)
                    Qxx = np.linalg.inv(N)
                    self.std_dev = self.s0 * np.sqrt(np.diag(Qxx))
                
                self.konvergiert = True
                return True
        return False

    def berechne_und_eliminiere_ausreisser(self):
        """Stochastische Eliminierung basierend auf dem 2-Sigma Kriterium"""
        self.protokoll_iterationen = 0
        self.eliminierungs_protokoll = []
        
        while len(self.punkte) >= 4:
            self.protokoll_iterationen += 1
            success = self.iterative_loesung()
            if not success: break
            
            dX, dY, dZ, om, ph, ka = self.x
            R = self.calculate_R(om, ph, ka)
            idx_to_remove = -1
            max_violation = 0
            
            
            elim_residuen = None
            
            for i, p in enumerate(self.punkte):
                p_ist = np.array([dX, dY, dZ]) + R @ p['l']
                v_vektor = p['g'] - p_ist
                # Sigma aus Qll (Beobachtungsgenauigkeit) skaliert mit s0
                sigma_p = self.s0 * np.sqrt(np.diag(p['qll']))
                
                for j in range(3):
                    violation_factor = np.abs(v_vektor[j]) / (2 * sigma_p[j])
                    if violation_factor > 1.0 and violation_factor > max_violation:
                        max_violation = violation_factor
                        idx_to_remove = i
                        elim_residuen = v_vektor.copy()

            if idx_to_remove != -1: 
                pnr = self.punkte[idx_to_remove]['PNR']
                print(f"--> ELIMINIERT: {pnr} (2-Sigma Verletzung Faktor {max_violation:.2f})")
                
                
                self.eliminierungs_protokoll.append({
                    "iteration": self.protokoll_iterationen,
                    "pnr": pnr,
                    "violation": max_violation,
                    "residuen": elim_residuen
                })
                
                self.punkte.pop(idx_to_remove)
                self.konvergiert = False
                continue 
            break
        
        self.debug_print_ergebnisse()
        self.debug_print_residuen()

    def transformiere_neupunkte(self, alle_koor_lokal: list):
        if not self.konvergiert: return []
        dX, dY, dZ, om, ph, ka = self.x
        R = self.calculate_R(om, ph, ka)
        
        res = []
        for p_l in alle_koor_lokal:
            pnr = str(p_l.get('pnr') or p_l.get('PNR'))
            
            l_vec = np.array([float(p_l['x']), float(p_l['y']), float(p_l['z'])])
            g = np.array([dX, dY, dZ]) + R @ l_vec
            
            res.append({
                "PNR": pnr, 
                "x": round(g[0], 4), 
                "y": round(g[1], 4), 
                "z": round(g[2], 4)
            })
        return res

    # --- Debugging Ausgaben ---
    def debug_print_ergebnisse(self):
        print("\n" + "="*50)
        print(f"{'TRANSFORMATIONS-PARAMETER (GAUSS-MARKOV)':^50}")
        print("-" * 50)
        labels = ["TX", "TY", "TZ", "Omega", "Phi", "Kappa"]
        for i, val in enumerate(self.x):
            unit = "m" if i < 3 else "deg"
            disp_val = val if i < 3 else np.degrees(val)
            print(f"{labels[i]:<10}: {disp_val:>12.4f} {unit} (+/- {self.std_dev[i]:.4f})")
        print(f"Sigma 0   : {self.s0:>12.6f} m")
        print("="*50)

    def debug_print_residuen(self):
        if not self.konvergiert: return
        R = self.calculate_R(self.x[3], self.x[4], self.x[5])
        print("\n" + "="*85)
        print(f"{'RESTKLAFFUNGEN AN PASSPUNKTEN':^85}")
        print("-" * 85)
        print(f"{'PNR':<10} | {'vx [mm]':>9} | {'vy [mm]':>9} | {'vz [mm]':>9} | {'3D [mm]':>12}")
        print("-" * 85)
        for p in self.punkte:
            g_ber = self.x[:3] + R @ p['l']
            v = (p['g'] - g_ber) * 1000 # In mm für bessere Lesbarkeit
            dist = np.linalg.norm(v)
            print(f"{p['PNR']:<10} | {v[0]:>9.1f} | {v[1]:>9.1f} | {v[2]:>9.1f} | {dist:>12.1f}")
        print("="*85)