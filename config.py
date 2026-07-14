import json
import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

APP_TITLE = "Monitoring-Konfigurator"

# ----------------------------- Datenmodell -----------------------------
def empty_model():
    return {
        "pktliste": [],           # Liste von {pnr:str, hz:float, vz:float, prism:float}
        "soll_koordinaten": [],   # Liste von {pnr:str, x:float, y:float, z:float}
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

# ----------------------------- Datei I/O -----------------------------
def load_params_from_file(path: str):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read().strip()
        
        data = json.loads(raw)
        model = empty_model() 
        
        # 1. Ziele (PKTLISTE) konvertieren
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

        # 2. SOLL_KOORDINATEN
        legacy_soll = data.get("SOLL_KOORDINATEN") or data.get("soll_koordinaten")
        if legacy_soll:
            for item in legacy_soll:
                new_item = {k.lower(): v for k, v in item.items()}
                model["soll_koordinaten"].append(new_item)

        # 3. Parameter (Key-Value)
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

# ----------------------------- Dialoge -----------------------------
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

class ParamsApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.minsize(1000, 600)
        self.file_path = None
        self.data = empty_model()
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

        self.tree_pkt = self._create_tree(self.nb, "Ziele (Richtungen)", ("pnr", "hz", "vz", "prism"), 
                                          ["PNR", "HZ (gon)", "VZ (gon)", "PRISM (m)"])
        self.tree_soll = self._create_tree(self.nb, "Soll-Koordinaten", ("pnr", "x", "y", "z"), 
                                           ["PNR", "X", "Y", "Z"])
        
        # Parameter Tab
        self.tab_param = ttk.Frame(self.nb, padding=8)
        self.nb.add(self.tab_param, text="Parameter")
        self.var_last = tk.StringVar(value="Stand: -")
        ttk.Label(self.tab_param, textvariable=self.var_last).pack(anchor="w", pady=(0,5))
        self.tree_param = ttk.Treeview(self.tab_param, columns=("k", "v"), show="headings")
        self.tree_param.heading("k", text="Schlüssel"); self.tree_param.heading("v", text="Wert")
        self.tree_param.pack(fill="both", expand=True)

        # Buttons rechts
        right = ttk.Frame(main)
        right.grid(row=0, column=2, sticky="ns", padx=(12, 0))
        ttk.Button(right, text="Hinzufügen", command=self.on_add).pack(fill="x", pady=2)
        ttk.Button(right, text="Bearbeiten", command=self.on_edit).pack(fill="x", pady=2)
        ttk.Button(right, text="Löschen", command=self.on_delete).pack(fill="x", pady=2)

    def _create_tree(self, parent, title, cols, headings):
        frame = ttk.Frame(parent, padding=8)
        parent.add(frame, text=title)
        tree = ttk.Treeview(frame, columns=cols, show="headings")
        for c, h in zip(cols, headings):
            tree.heading(c, text=h)
            tree.column(c, width=100, anchor="center")
        tree.pack(fill="both", expand=True)
        return tree

    def on_open(self):
        path = filedialog.askopenfilename(filetypes=[("Textdateien", "*.txt"), ("Alle", "*.*")])
        if path:
            self.data = load_params_from_file(path)
            self.file_path = path
            self._populate_all()
            self.lbl_status.config(text=f"Geladen:\n{os.path.basename(path)}")

    def on_save(self):
        if not self.file_path:
            self.file_path = filedialog.asksaveasfilename(defaultextension=".txt")
            if not self.file_path: return
        
        try:
            save_params_to_file(self.file_path, self.data)
            messagebox.showinfo("Erfolg", "Daten gespeichert.")
            self._populate_all()
        except Exception as e:
            messagebox.showerror("Fehler", str(e))

    def on_add(self):
        tid = self.nb.index(self.nb.select())
        if tid == 0:
            dlg = PointDialog(self.root, "Neues Ziel", "pktliste")
            if dlg.result: self.data["pktliste"].append(dlg.result)
        elif tid == 1:
            dlg = PointDialog(self.root, "Neuer Soll-Punkt", "soll")
            if dlg.result: self.data["soll_koordinaten"].append(dlg.result)
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
            sel = self.tree_soll.selection()
            if not sel: return
            idx = self.tree_soll.index(sel[0])
            dlg = PointDialog(self.root, "Soll-Punkt bearbeiten", "soll", self.data["soll_koordinaten"][idx])
            if dlg.result: self.data["soll_koordinaten"][idx] = dlg.result
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
        tree = [self.tree_pkt, self.tree_soll, self.tree_param][tid]
        sel = tree.selection()
        if not sel or not messagebox.askyesno("Löschen", "Eintrag wirklich entfernen?"): return
        
        if tid == 0:
            for s in reversed(sel): del self.data["pktliste"][tree.index(s)]
        elif tid == 1:
            for s in reversed(sel): del self.data["soll_koordinaten"][tree.index(s)]
        elif tid == 2:
            for s in sel: 
                key = tree.item(s)['values'][0]
                if key in self.data["params"]: del self.data["params"][key]
        self._populate_all()

    def _populate_all(self):
        for t in (self.tree_pkt, self.tree_soll, self.tree_param): t.delete(*t.get_children())
        for p in self.data["pktliste"]:
            self.tree_pkt.insert("", "end", values=(p["pnr"], f"{p['hz']:.4f}", f"{p['vz']:.4f}", f"{p['prism']:.3f}"))
        for p in self.data["soll_koordinaten"]:
            self.tree_soll.insert("", "end", values=(p["pnr"], f"{p['x']:.3f}", f"{p['y']:.3f}", f"{p['z']:.3f}"))
        for k in sorted(self.data["params"].keys()):
            self.tree_param.insert("", "end", values=(k, self.data["params"][k]))
        self.var_last.set(f"Stand: {self.data.get('_last_update', '-')}")

def main():
    root = tk.Tk()
    app = ParamsApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
