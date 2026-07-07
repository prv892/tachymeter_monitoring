import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import math
import json

# ==========================================
# BERECHNUNGSTEIL (BACKEND)
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
# GUI TEIL
# ==========================================
class SurveyGui:
    def __init__(self, root):
        self.root = root
        self.root.title("Geodätische Polarberechnung (Gon)")
        try:
            self.root.state('zoomed')
        except:
            self.root.attributes('-zoomed', True)

        self.calc = PolarCalculator()
        self.station = None 
        self.points = {} # {pid: [e, n, h, hz_abs, hz_rel, vz, dist]}

        self._setup_ui()

    def _setup_ui(self):
        self.root.columnconfigure(1, weight=3)
        self.root.rowconfigure(0, weight=1)

        # --- LINKS: Import ---
        self.frame_left = ttk.LabelFrame(self.root, text="Datei / Import")
        self.frame_left.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        ttk.Button(self.frame_left, text="Punkte laden (.txt)", command=self.import_points).pack(fill="x", pady=5)

        # --- MITTE: Tabelle ---
        self.frame_mid = ttk.LabelFrame(self.root, text="Punktliste (Werte in Gon / m)")
        self.frame_mid.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        cols = ("pid", "east", "north", "height", "hz", "vz", "dist")
        self.tree = ttk.Treeview(self.frame_mid, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=90, anchor="center")
        self.tree.pack(expand=True, fill="both")

        # --- RECHTS: Funktionen ---
        self.frame_right = ttk.LabelFrame(self.root, text="Aktionen")
        self.frame_right.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        
        ttk.Button(self.frame_right, text="Standpunkt festlegen", command=self.set_station).pack(fill="x", pady=5)
        ttk.Button(self.frame_right, text="Orientierung setzen (Hz=0)", command=self.set_orientation).pack(fill="x", pady=5)
        
        ttk.Separator(self.frame_right, orient="horizontal").pack(fill="x", pady=15)
        
        ttk.Button(self.frame_right, text="+ Punkt hinzufügen", command=self.add_point_dialog).pack(fill="x", pady=2)
        ttk.Button(self.frame_right, text="✎ Punkt bearbeiten", command=self.edit_point_dialog).pack(fill="x", pady=2)
        ttk.Button(self.frame_right, text="🗑 Punkt löschen", command=self.delete_point).pack(fill="x", pady=2)
        
        self.lbl_stn = ttk.Label(self.frame_right, text="Standpunkt: -", font=("Arial", 10, "bold"))
        self.lbl_stn.pack(pady=20)

        # --- RECHTS UNTEN: Export Buttons ---
        export_frame = ttk.Frame(self.frame_right)
        export_frame.pack(side="bottom", fill="x", pady=10)
        
        ttk.Button(export_frame, text="📥 Export (.txt)", command=self.export_results).pack(fill="x", pady=2)
        ttk.Button(export_frame, text="⚙️ Export Params (.json)", command=self.export_params).pack(fill="x", pady=2)

    # ... [Funktionen für Import/Add/Edit identisch wie zuvor] ...
    def import_points(self):
        path = filedialog.askopenfilename()
        if not path: return
        try:
            with open(path, 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 4:
                        self.add_point_to_dict(str(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
            self.update_table()
            if self.station: self.calculate_all()
        except Exception as e:
            messagebox.showerror("Fehler", f"Datei konnte nicht gelesen werden: {e}")

    def add_point_to_dict(self, pid, e, n, h):
        self.points[str(pid)] = [e, n, h, 0.0, 0.0, 0.0, 0.0]

    def add_point_dialog(self):
        self._point_window("Neuer Punkt", self._save_new)

    def edit_point_dialog(self):
        sel = self.tree.focus()
        if not sel:
            messagebox.showwarning("Info", "Bitte Punkt zum Bearbeiten wählen!")
            return
        pid = str(self.tree.item(sel)['values'][0])
        self._point_window("Punkt bearbeiten", self._save_edit, edit_pid=pid)

    def _point_window(self, title, save_func, edit_pid=None):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("300x250")
        fields = ["PID", "Rechtswert", "Hochwert", "Hoehe"]
        entries = {}
        for f in fields:
            row = ttk.Frame(win)
            row.pack(fill="x", padx=10, pady=5)
            ttk.Label(row, text=f, width=12).pack(side="left")
            e = ttk.Entry(row)
            e.pack(side="right", expand=True, fill="x")
            entries[f] = e
            if edit_pid and f == "PID":
                e.insert(0, edit_pid); e.config(state="disabled")
            elif edit_pid:
                val = self.points[edit_pid][fields.index(f)-1]
                e.insert(0, str(val))
        ttk.Button(win, text="Speichern", command=lambda: save_func(entries, win)).pack(pady=10)

    def _save_new(self, entries, win):
        try:
            pid = entries["PID"].get()
            self.add_point_to_dict(pid, float(entries["Rechtswert"].get()), float(entries["Hochwert"].get()), float(entries["Hoehe"].get()))
            self.update_table(); win.destroy()
            if self.station: self.calculate_all()
        except: messagebox.showerror("Fehler", "Ungültige Werte")

    def _save_edit(self, entries, win):
        try:
            pid = entries["PID"].get()
            self.points[pid][0] = float(entries["Rechtswert"].get())
            self.points[pid][1] = float(entries["Hochwert"].get())
            self.points[pid][2] = float(entries["Hoehe"].get())
            self.update_table(); win.destroy()
            if self.station: self.calculate_all()
        except: messagebox.showerror("Fehler", "Ungültige Werte")

    def delete_point(self):
        sel = self.tree.focus()
        if not sel: return
        pid = str(self.tree.item(sel)['values'][0])
        if messagebox.askyesno("Löschen", f"Punkt {pid} wirklich löschen?"):
            del self.points[pid]
            if self.station and self.station[0] == pid:
                self.station = None
                self.lbl_stn.config(text="Standpunkt: -")
            self.update_table(); self.calculate_all()

    def update_table(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for pid, d in self.points.items():
            self.tree.insert("", "end", values=(pid, f"{d[0]:.3f}", f"{d[1]:.3f}", f"{d[2]:.3f}", f"{d[4]:.4f}", f"{d[5]:.4f}", f"{d[6]:.3f}"))

    def set_station(self):
        sel = self.tree.focus()
        if not sel: return
        pid = str(self.tree.item(sel)['values'][0])
        p = self.points[pid]
        self.station = (pid, p[0], p[1], p[2])
        self.lbl_stn.config(text=f"Standpunkt: {pid}", foreground="green")
        self.calculate_all()

    def calculate_all(self):
        if not self.station: return
        sid, se, sn, sh = self.station
        for pid in self.points:
            p = self.points[pid]
            hz, vz, dist = self.calc.calculate_single(se, sn, sh, p[0], p[1], p[2])
            self.points[pid][3] = hz; self.points[pid][4] = hz; self.points[pid][5] = vz; self.points[pid][6] = dist
        self.update_table()

    def set_orientation(self):
        sel = self.tree.focus()
        if not sel or not self.station: return
        ori_pid = str(self.tree.item(sel)['values'][0])
        shift = self.points[ori_pid][3]
        for pid in self.points:
            self.points[pid][4] = (self.points[pid][3] - shift) % 400
        self.update_table()

    # --- EXPORT FUNKTIONEN ---
    def export_results(self):
        if not self.station:
            messagebox.showwarning("Export", "Kein Standpunkt definiert – keine Polarwerte vorhanden.")
            return
        
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Textdatei", "*.txt")])
        if not path: return
        
        try:
            with open(path, 'w') as f:
                # Kopfzeile optional (kannst du entfernen wenn nicht gewünscht)
                f.write(f"# Standpunkt: {self.station[0]}\n")
                f.write(f"# PID HZ[gon] VZ[gon] DIST[m]\n")
                for pid, d in self.points.items():
                    # Wir exportieren nur Punkte, die nicht der Standpunkt selbst sind
                    if pid != self.station[0]:
                        line = f"{pid} {d[4]:.4f} {d[5]:.4f} {d[6]:.3f}\n"
                        f.write(line)
            messagebox.showinfo("Erfolg", "Daten erfolgreich exportiert.")
        except Exception as e:
            messagebox.showerror("Fehler", f"Export fehlgeschlagen: {e}")

    def export_params(self):
        if not self.station:
            messagebox.showwarning("Export", "Kein Standpunkt definiert – keine Polarwerte vorhanden.")
            return

        # 1. Datei auswählen (jetzt flexibler bei der Endung)
        path = filedialog.askopenfilename(
            title="Params-Datei (Text/JSON) wählen",
            filetypes=[("Alle Dateien", "*.*"), ("JSON-Datei", "*.json"), ("Textdatei", "*.txt")]
        )
        if not path: return

        try:
            # 2. Bestehende Daten laden
            # Wir öffnen sie als Textdatei und interpretieren den Inhalt als JSON
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    messagebox.showerror("Fehler", "Die gewählte Datei ist leer.")
                    return
                data = json.loads(content)

            # 3. Neue Punktliste vorbereiten
            new_pktliste = []
            for pid, d in self.points.items():
                if pid != self.station[0]:
                    # [PID, HZ, VZ, DIST]
                    new_pktliste.append([
                        str(pid), 
                        round(d[4], 4), 
                        round(d[5], 4), 
                        round(d[6], 4)
                    ])

            # 4. In das Objekt schreiben
            # Falls "PKTLISTE" nicht existiert, wird es neu angelegt
            data["PKTLISTE"] = new_pktliste
            
            import datetime
            data["_last_update"] = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

            # 5. Datei überschreiben (behält die JSON-Struktur in der Textdatei bei)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            messagebox.showinfo("Erfolg", f"Daten in {path} wurden aktualisiert.")

        except json.JSONDecodeError:
            messagebox.showerror("Fehler", "Die Datei enthält kein gültiges JSON-Format.")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Verarbeiten: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    SurveyGui(root)
    root.mainloop()