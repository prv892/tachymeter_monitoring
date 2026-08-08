import json
import os
import math
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

APP_TITLE = "Monitoring-Konfigurator"

# ==========================================
# BERECHNUNGSTEIL
# ==========================================
class PolarCalculator:
    @staticmethod
    def calculate_single(s_e, s_n, s_h, p_e, p_n, p_h):
        de = p_e - s_e
        dn = p_n - s_n
        dh = p_h - s_h
        
        dist_3d = math.sqrt(de**2 + dn**2 + dh**2)
        if dist_3d == 0: return 0.0, 0.0, 0.0
        
        hz_gon = (math.atan2(de, dn) * 200 / math.pi) % 400
        vz_gon = (math.acos(dh / dist_3d) * 200 / math.pi)
            
        return hz_gon, vz_gon, dist_3d

# ==========================================
# DATENMODELL & I/O
# ==========================================
def empty_model():
    return {
        "pktliste": [],           
        "soll_koordinaten": [],   
        "params": {
            "S_HZ_GON": 0.0004,
            "S_VZ_GON": 0.0004,
            "S_DIST_M": 0.001,
            "S_DIST_PPM": 1.0,
            "S_WINKEL_OFFSET_M": 0.0005,
            "ANZ_SAETZE": 1,
            "START_TEMP": 20.0,
            "START_DRUCK": 1000.0
        },
        "_last_update": ""
    }

def load_params_from_file(path: str):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read().strip()
        
        data = json.loads(raw)
        model = empty_model() 
        
        legacy_pkt = data.get("PKTLISTE") or data.get("pktliste")
        if legacy_pkt:
            for item in legacy_pkt:
                if isinstance(item, list) and len(item) >= 4:
                    model["pktliste"].append({"pnr": str(item[0]), "hz": item[1], "vz": item[2], "prism": item[3]})
                elif isinstance(item, dict):
                    model["pktliste"].append({
                        "pnr": str(item.get("pnr") or item.get("name", "")),
                        "hz": float(item.get("hz", 0)),
                        "vz": float(item.get("vz", 0)),
                        "prism": float(item.get("prism", 0))
                    })

        legacy_soll = data.get("SOLL_KOORDINATEN") or data.get("soll_koordinaten")
        if legacy_soll:
            for item in legacy_soll:
                new_item = {k.lower(): v for k, v in item.items()}
                model["soll_koordinaten"].append(new_item)

        file_params = data.get("params", {})
        for k in model["params"].keys():
            if k in file_params:
                model["params"][k] = file_params[k]
            elif k in data:
                model["params"][k] = data[k]

        model["_last_update"] = data.get("_last_update", "Unbekannt")
        return model
    except Exception as e:
        messagebox.showerror("Fehler", f"Datei konnte nicht gelesen werden: {e}")
        return empty_model()

def save_params_to_file(path: str, data: dict):
    save_data = dict(data)
    save_data["_last_update"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)


# ==========================================
# DIALOGE
# ==========================================
class PointDialog(simpledialog.Dialog):
    def __init__(self, master, title, mode, init=None):
        self.mode = mode
        self.init = init or {}
        super().__init__(master, title)

    def body(self, master):
        pad = {"padx": 6, "pady": 4}
        if self.mode == "pktliste":
            labels = ["PNR", "HZ (gon)", "VZ (gon)", "Prismenkonstante (m)"]
            keys = ["pnr", "hz", "vz", "prism"]
        else:
            labels = ["PNR", "X", "Y", "Z"]
            keys = ["pnr", "x", "y", "z"]

        self.entries = {}
        for i, (lbl, key) in enumerate(zip(labels, keys)):
            ttk.Label(master, text=lbl).grid(row=i, column=0, sticky="w", **pad)
            
            if key == "prism":
                ent = ttk.Combobox(master, values=["0.0", "-0.0175"], width=21)
                ent.grid(row=i, column=1, **pad)
                val = self.init.get(key, "0.0")
                ent.insert(0, str(val))
            else:
                ent = ttk.Entry(master, width=24)
                ent.grid(row=i, column=1, **pad)
                val = self.init.get(key, "")
                ent.insert(0, str(val))
                
            self.entries[key] = ent
        return self.entries["pnr"]

    def validate(self):
        try:
            res = {}
            for key, ent in self.entries.items():
                val = ent.get().replace(",", ".").strip()
                if key == "pnr":
                    if not val: raise ValueError
                    res[key] = val
                else:
                    res[key] = float(val)
            self.result = res
            return True
        except ValueError:
            messagebox.showerror("Eingabefehler", "Bitte gültige Werte eingeben.")
            return False

class ParamDialog(simpledialog.Dialog):
    def __init__(self, master, title, init_key="", init_val="", readonly_key=False):
        self.init_key = init_key
        self.init_val = init_val
        self.readonly_key = readonly_key
        super().__init__(master, title)

    def body(self, master):
        pad = {"padx": 6, "pady": 4}
        ttk.Label(master, text="Schlüssel:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Label(master, text="Wert:").grid(row=1, column=0, sticky="w", **pad)
        
        self.e_key = ttk.Entry(master, width=30)
        self.e_val = ttk.Entry(master, width=30)
        self.e_key.grid(row=0, column=1, **pad)
        self.e_val.grid(row=1, column=1, **pad)
        
        self.e_key.insert(0, self.init_key)
        self.e_val.insert(0, str(self.init_val))
        
        if self.readonly_key:
            self.e_key.config(state="readonly")
            return self.e_val
        return self.e_key

    def validate(self):
        key = self.e_key.get().strip()
        val = self.e_val.get().strip()
        if not key: return False
        self.result = (key, val)
        return True


# ==========================================
# HAUPT-GUI
# ==========================================
class ParamsApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.minsize(1050, 650)
        self.file_path = None
        self.data = empty_model()
        self.coords_db = {} # Format: pnr -> {'x':, 'y':, 'z':, 'type': 'AP'/'Neupunkt'/'Standpunkt'}
        
        self._build_layout()
        self._populate_all()

        try:
            self.root.state('zoomed')
        except tk.TclError:
            self.root.attributes('-zoomed', True)

    def _build_layout(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # Toolbar links
        left = ttk.Frame(main)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        ttk.Button(left, text="Datei öffnen", command=self.on_open).pack(fill="x", pady=2)
        ttk.Button(left, text="Speichern", command=self.on_save).pack(fill="x", pady=2)
        self.lbl_status = ttk.Label(left, text="Bereit.", wraplength=150)
        self.lbl_status.pack(anchor="w", pady=10)

        # Tab-System
        center = ttk.Frame(main)
        center.grid(row=0, column=1, sticky="nsew")
        self.nb = ttk.Notebook(center)
        self.nb.pack(fill="both", expand=True)
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

        self.tab_pkt = ttk.Frame(self.nb, padding=8)
        self.nb.add(self.tab_pkt, text="Ziele (Richtungen)")
        self.tree_pkt = ttk.Treeview(self.tab_pkt, columns=("pnr", "hz", "vz", "prism"), show="headings")
        for c, h in zip(("pnr", "hz", "vz", "prism"), ["PNR", "HZ (gon)", "VZ (gon)", "PRISM (m)"]):
            self.tree_pkt.heading(c, text=h)
            self.tree_pkt.column(c, width=100, anchor="center")
        self.tree_pkt.pack(fill="both", expand=True)

        self.tab_coords = ttk.Frame(self.nb, padding=8)
        self.nb.add(self.tab_coords, text="Koordinaten (APs & Neupunkte)")
        self.tree_coords = ttk.Treeview(self.tab_coords, columns=("pnr", "x", "y", "z", "type"), show="headings")
        for c, h in zip(("pnr", "x", "y", "z", "type"), ["PNR", "X", "Y", "Z", "Typ"]):
            self.tree_coords.heading(c, text=h)
            self.tree_coords.column(c, width=100, anchor="center")
        self.tree_coords.pack(fill="both", expand=True)

        self.tab_param = ttk.Frame(self.nb, padding=8)
        self.nb.add(self.tab_param, text="Parameter")
        self.var_last = tk.StringVar(value="Stand: -")
        ttk.Label(self.tab_param, textvariable=self.var_last).pack(anchor="w", pady=(0,5))
        self.tree_param = ttk.Treeview(self.tab_param, columns=("k", "v"), show="headings")
        self.tree_param.heading("k", text="Schlüssel"); self.tree_param.heading("v", text="Wert")
        self.tree_param.pack(fill="both", expand=True)

        # Frame Rechts (dynamisch)
        self.frame_right = ttk.LabelFrame(main, text="Aktionen")
        self.frame_right.grid(row=0, column=2, sticky="ns", padx=(12, 0), ipadx=5, ipady=5)

    def _on_tab_change(self, event=None):
        for widget in self.frame_right.winfo_children():
            widget.destroy()
            
        tid = self.nb.index(self.nb.select())
        
        if tid == 0:  # Ziele
            ttk.Button(self.frame_right, text="Hinzufügen", command=self.on_add).pack(fill="x", pady=2, padx=5)
            ttk.Button(self.frame_right, text="Bearbeiten", command=self.on_edit).pack(fill="x", pady=2, padx=5)
            ttk.Button(self.frame_right, text="Löschen", command=self.on_delete).pack(fill="x", pady=2, padx=5)
            ttk.Separator(self.frame_right).pack(fill="x", pady=10, padx=5)
            ttk.Button(self.frame_right, text="📥 Ziele exportieren", command=self.on_export_ziele).pack(fill="x", pady=2, padx=5)
            
        elif tid == 1:  # Koordinaten
            ttk.Button(self.frame_right, text="TXT Importieren", command=self.on_import_coords).pack(fill="x", pady=2, padx=5)
            ttk.Button(self.frame_right, text="Manuell Hinzufügen", command=self.on_add).pack(fill="x", pady=2, padx=5)
            ttk.Button(self.frame_right, text="Bearbeiten", command=self.on_edit).pack(fill="x", pady=2, padx=5)
            ttk.Button(self.frame_right, text="Löschen", command=self.on_delete).pack(fill="x", pady=2, padx=5)
            
            ttk.Separator(self.frame_right).pack(fill="x", pady=10, padx=5)
            ttk.Label(self.frame_right, text="Punkt-Rolle setzen:").pack(anchor="w", padx=5)
            ttk.Button(self.frame_right, text="Als AP markieren", command=lambda: self.on_set_role("AP")).pack(fill="x", pady=2, padx=5)
            ttk.Button(self.frame_right, text="Als Neupunkt markieren", command=lambda: self.on_set_role("Neupunkt")).pack(fill="x", pady=2, padx=5)
            ttk.Button(self.frame_right, text="Als Standpunkt markieren", command=lambda: self.on_set_role("Standpunkt")).pack(fill="x", pady=2, padx=5)
            
            ttk.Separator(self.frame_right).pack(fill="x", pady=10, padx=5)
            ttk.Button(self.frame_right, text="⚙️ Polarwerte berechnen", command=self.on_calculate_polar).pack(fill="x", pady=2, padx=5)
            
            ttk.Separator(self.frame_right).pack(fill="x", pady=10, padx=5)
            ttk.Button(self.frame_right, text="📥 Alle Koord. exportieren", command=lambda: self.on_export_coords("all")).pack(fill="x", pady=2, padx=5)
            ttk.Button(self.frame_right, text="📥 AP-Koord. exportieren", command=lambda: self.on_export_coords("ap")).pack(fill="x", pady=2, padx=5)
            
        elif tid == 2:  # Params
            ttk.Button(self.frame_right, text="Hinzufügen", command=self.on_add).pack(fill="x", pady=2, padx=5)
            ttk.Button(self.frame_right, text="Bearbeiten", command=self.on_edit).pack(fill="x", pady=2, padx=5)
            ttk.Button(self.frame_right, text="Löschen", command=self.on_delete).pack(fill="x", pady=2, padx=5)


    # --- DATEI I/O ---
    def on_open(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Parameter", "*.txt *.json"), ("Alle", "*.*")])
        if path:
            self.data = load_params_from_file(path)
            self.file_path = path
            
            # Populate internal Coords-DB with APs from soll_koordinaten
            self.coords_db = {}
            for p in self.data["soll_koordinaten"]:
                self.coords_db[p["pnr"]] = {"x": p["x"], "y": p["y"], "z": p["z"], "type": "AP"}
                
            self._populate_all()
            self.lbl_status.config(text=f"Geladen:{os.path.basename(path)}")

    def on_save(self):
        if not self.file_path:
            self.file_path = filedialog.asksaveasfilename(defaultextension=".txt")
            if not self.file_path: return
        
        # Snyc soll_koordinaten -> Only save points flagged as "AP"
        self.data["soll_koordinaten"] = []
        for pnr, d in self.coords_db.items():
            if d['type'] == 'AP':
                self.data["soll_koordinaten"].append({
                    "pnr": pnr, "x": d['x'], "y": d['y'], "z": d['z']
                })
        
        try:
            save_params_to_file(self.file_path, self.data)
            messagebox.showinfo("Erfolg", "Daten gespeichert. Hinweis: Neupunkte (nicht AP) werden nur mit ihren Richtungen in den Zielen gespeichert, ihre Koordinaten werden nicht übernommen.")
            self._populate_all()
        except Exception as e:
            messagebox.showerror("Fehler", str(e))

    def on_import_coords(self):
        path = filedialog.askopenfilename(filetypes=[("Textdateien", "*.txt"), ("Alle", "*.*")])
        if not path: return
        try:
            with open(path, 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 4:
                        pnr, x, y, z = parts[0], float(parts[1]), float(parts[2]), float(parts[3])
                        ctype = self.coords_db.get(pnr, {}).get('type', 'Neupunkt') # default to Neupunkt
                        self.coords_db[pnr] = {'x': x, 'y': y, 'z': z, 'type': ctype}
            self._populate_all()
            messagebox.showinfo("Erfolg", "Koordinaten importiert.")
        except Exception as e:
            messagebox.showerror("Fehler", f"Datei konnte nicht gelesen werden: {e}")

    # --- DATEN-MANIPULATION ---
    def on_add(self):
        tid = self.nb.index(self.nb.select())
        if tid == 0:
            dlg = PointDialog(self.root, "Neues Ziel", "pktliste")
            if dlg.result: self.data["pktliste"].append(dlg.result)
        elif tid == 1:
            dlg = PointDialog(self.root, "Neue Koordinate", "soll")
            if dlg.result:
                pnr = dlg.result["pnr"]
                self.coords_db[pnr] = {"x": dlg.result["x"], "y": dlg.result["y"], "z": dlg.result["z"], "type": "Neupunkt"}
        elif tid == 2:
            dlg = ParamDialog(self.root, "Neuer Parameter")
            if dlg.result: self.data["params"][dlg.result[0]] = dlg.result[1]
        self._populate_all()

    def on_edit(self):
        tid = self.nb.index(self.nb.select())
        if tid == 0:
            sel = self.tree_pkt.selection()
            if not sel: return
            idx = self.tree_pkt.index(sel[0])
            dlg = PointDialog(self.root, "Ziel bearbeiten", "pktliste", self.data["pktliste"][idx])
            if dlg.result: self.data["pktliste"][idx] = dlg.result
        elif tid == 1:
            sel = self.tree_coords.selection()
            if not sel: return
            pnr = self.tree_coords.item(sel[0])['values'][0]
            pnr = str(pnr)
            d = self.coords_db[pnr]
            init_data = {"pnr": pnr, "x": d["x"], "y": d["y"], "z": d["z"]}
            dlg = PointDialog(self.root, "Koordinate bearbeiten", "soll", init_data)
            if dlg.result:
                new_pnr = dlg.result["pnr"]
                if new_pnr != pnr: del self.coords_db[pnr]
                self.coords_db[new_pnr] = {"x": dlg.result["x"], "y": dlg.result["y"], "z": dlg.result["z"], "type": d["type"]}
        elif tid == 2:
            sel = self.tree_param.selection()
            if not sel: return
            key = self.tree_param.item(sel[0])['values'][0]
            val = self.data["params"][key]
            dlg = ParamDialog(self.root, "Wert bearbeiten", key, val, readonly_key=True)
            if dlg.result: self.data["params"][key] = dlg.result[1]
        self._populate_all()

    def on_delete(self):
        tid = self.nb.index(self.nb.select())
        if tid == 0:
            sel = self.tree_pkt.selection()
            if not sel or not messagebox.askyesno("Löschen", "Eintrag entfernen?"): return
            for s in reversed(sel): del self.data["pktliste"][self.tree_pkt.index(s)]
        elif tid == 1:
            sel = self.tree_coords.selection()
            if not sel or not messagebox.askyesno("Löschen", "Eintrag entfernen?"): return
            for s in sel:
                pnr = str(self.tree_coords.item(s)['values'][0])
                if pnr in self.coords_db: del self.coords_db[pnr]
        elif tid == 2:
            sel = self.tree_param.selection()
            if not sel or not messagebox.askyesno("Löschen", "Eintrag entfernen?"): return
            for s in sel: 
                key = self.tree_param.item(s)['values'][0]
                if key in self.data["params"]: del self.data["params"][key]
        self._populate_all()

    def on_set_role(self, role):
        sel = self.tree_coords.selection()
        if not sel:
            messagebox.showwarning("Achtung", "Bitte mindestens einen Punkt auswählen.")
            return
            
        if role == "Standpunkt":
            for pnr, d in self.coords_db.items():
                if d['type'] == 'Standpunkt': d['type'] = 'Neupunkt'
        
        for s in sel:
            pnr = str(self.tree_coords.item(s)['values'][0])
            if pnr in self.coords_db:
                self.coords_db[pnr]['type'] = role
        self._populate_all()

    # --- BERECHNUNG ---
    def on_calculate_polar(self):
        stn = None
        for pnr, d in self.coords_db.items():
            if d['type'] == 'Standpunkt':
                stn = (pnr, d['x'], d['y'], d['z'])
                break
        
        if not stn:
            messagebox.showerror("Fehler", "Kein Standpunkt definiert! Bitte einen Punkt als Standpunkt markieren.")
            return
            
        ori_pnr = simpledialog.askstring("Orientierung", "PNR des Orientierungspunktes (HZ=0):")
        if not ori_pnr or str(ori_pnr) not in self.coords_db:
            messagebox.showerror("Fehler", "Ungültiger oder fehlender Orientierungspunkt!")
            return
            
        ori_x, ori_y, ori_z = self.coords_db[ori_pnr]['x'], self.coords_db[ori_pnr]['y'], self.coords_db[ori_pnr]['z']
        base_hz, _, _ = PolarCalculator.calculate_single(stn[1], stn[2], stn[3], ori_x, ori_y, ori_z)
        
        count = 0
        for pnr, d in self.coords_db.items():
            if pnr == stn[0]: continue
            
            hz, vz, _ = PolarCalculator.calculate_single(stn[1], stn[2], stn[3], d['x'], d['y'], d['z'])
            hz_rel = (hz - base_hz) % 400
            
            existing_prism = 0.0
            for pkt in self.data["pktliste"]:
                if pkt["pnr"] == pnr:
                    existing_prism = pkt["prism"]
                    self.data["pktliste"].remove(pkt)
                    break
            
            self.data["pktliste"].append({
                "pnr": pnr, "hz": hz_rel, "vz": vz, "prism": existing_prism
            })
            count += 1
            
        self._populate_all()
        self.nb.select(self.tab_pkt)
        messagebox.showinfo("Erfolg", f"Polarwerte für {count} Ziele berechnet und in die Ziel-Liste übertragen.")

    # --- EXPORT ---
    def on_export_ziele(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Textdatei", "*.txt")])
        if not path: return
        with open(path, 'w', encoding='utf-8') as f:
            for p in self.data["pktliste"]:
                pnr = str(p.get("pnr", ""))
                hz = p.get("hz", 0.0)
                vz = p.get("vz", 0.0)
                prism = p.get("prism", 0.0)
                f.write(f"{pnr} {hz:.4f} {vz:.4f} {prism:.4f}\n")
        messagebox.showinfo("Erfolg", "Ziele exportiert.")

    def on_export_coords(self, mode="all"):
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Textdatei", "*.txt")])
        if not path: return
        with open(path, 'w', encoding='utf-8') as f:
            for pnr, d in self.coords_db.items():
                if mode == "ap" and d.get('type') != "AP": 
                    continue
                x = d.get('x', 0.0)
                y = d.get('y', 0.0)
                z = d.get('z', 0.0)
                f.write(f"{str(pnr)} {x:.3f} {y:.3f} {z:.3f}\n")
        messagebox.showinfo("Erfolg", "Koordinaten exportiert.")

    # --- UI UPDATE ---
    def _populate_all(self):
        for t in (self.tree_pkt, self.tree_coords, self.tree_param): t.delete(*t.get_children())
        
        for p in self.data["pktliste"]:
            self.tree_pkt.insert("", "end", values=(p["pnr"], f"{p['hz']:.4f}", f"{p['vz']:.4f}", f"{p['prism']:.4f}"))
            
        for pnr, d in self.coords_db.items():
            tag = "stn" if d["type"] == "Standpunkt" else "ap" if d["type"] == "AP" else "neu"
            self.tree_coords.insert("", "end", values=(pnr, f"{d['x']:.3f}", f"{d['y']:.3f}", f"{d['z']:.3f}", d['type']), tags=(tag,))
            
        self.tree_coords.tag_configure("stn", background="#d4edda")
        self.tree_coords.tag_configure("ap", background="#cce5ff")
        
        for k in sorted(self.data["params"].keys()):
            self.tree_param.insert("", "end", values=(k, self.data["params"][k]))
            
        self.var_last.set(f"Stand: {self.data.get('_last_update', '-')}")
        self._on_tab_change()

def main():
    root = tk.Tk()
    app = ParamsApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()