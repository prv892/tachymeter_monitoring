import os
import glob
import json
import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.ticker import MultipleLocator

# ==========================================
# DATEN-VERARBEITUNG (BACKEND)
# ==========================================
class DataManager:
    def __init__(self, folder="ergebnisse"):
        self.folder = folder
        self.df = None
        self.points = []
        self.soll_coords = []
    
    def load_and_process_data(self):
        """Liest CSV-Dateien und Soll-Koordinaten ein."""
        
        # 1. SOLL-KOORDINATEN LADEN (für die Netzübersicht)
        base_dir = os.path.dirname(os.path.abspath(self.folder))
        param_path = os.path.join(base_dir, "parameter", "params.txt")
        self.soll_coords = []
        if os.path.exists(param_path):
            try:
                with open(param_path, "r", encoding="utf-8") as f:
                    params_data = json.load(f)
                    self.soll_coords = params_data.get("SOLL_KOORDINATEN", params_data.get("soll_koordinaten", []))
            except Exception as e:
                print(f"Fehler beim Laden der params.txt: {e}")

        # 2. MESSDATEN LADEN
        search_pattern = os.path.join(self.folder, "*_neupunkte.csv")
        files = glob.glob(search_pattern)
        
        if not files:
            return False, "Keine CSV-Dateien im Ordner 'ergebnisse' gefunden."
            
        all_data = []
        for file in files:
            basename = os.path.basename(file)
            date_str = basename.split('_neupunkte')[0]
            
            if date_str.startswith("sim_"):
                date_str = date_str.replace("sim_", "")
                
            try:
                timestamp = datetime.strptime(date_str, "%y%m%d_%H%M")
            except ValueError:
                continue 
                
            df_temp = pd.read_csv(file, sep=';', dtype={'PNR': str})
            df_temp['Datum'] = timestamp
            all_data.append(df_temp)
            
        if not all_data:
            return False, "Konnte keine gültigen Daten extrahieren."
            
        self.df = pd.concat(all_data, ignore_index=True)
        self.df.sort_values(by='Datum', inplace=True)
        
        self.points = sorted(self.df['PNR'].unique())
        
        self.df['dX_mm'] = 0.0
        self.df['dY_mm'] = 0.0
        self.df['dZ_mm'] = 0.0
        self.df['d3D_mm'] = 0.0
        
        for pnr in self.points:
            mask = self.df['PNR'] == pnr
            if mask.sum() > 0:
                first_x = self.df.loc[mask, 'X'].iloc[0]
                first_y = self.df.loc[mask, 'Y'].iloc[0]
                first_z = self.df.loc[mask, 'Z'].iloc[0]
                
                self.df.loc[mask, 'dX_mm'] = (self.df.loc[mask, 'X'] - first_x) * 1000
                self.df.loc[mask, 'dY_mm'] = (self.df.loc[mask, 'Y'] - first_y) * 1000
                self.df.loc[mask, 'dZ_mm'] = (self.df.loc[mask, 'Z'] - first_z) * 1000
                self.df.loc[mask, 'd3D_mm'] = np.sqrt(self.df.loc[mask, 'dX_mm']**2 + 
                                                      self.df.loc[mask, 'dY_mm']**2 + 
                                                      self.df.loc[mask, 'dZ_mm']**2)
                
        return True, "Daten erfolgreich geladen."

# ==========================================
# GUI (FRONTEND)
# ==========================================
class MonitoringDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitoring Dashboard")
        self.root.geometry("1100x850")
        
        # Plattformübergreifendes Maximieren (Windows & Linux)
        try:
            self.root.state('zoomed')
        except tk.TclError:
            self.root.attributes('-zoomed', True)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.data_manager = DataManager()
        self.fig_map = None 
        self.fig_time = None
        self.fig_2d = None
        self.fig_3d = None
        self.fig_total = None
        
        self.canvas_map = None
        self.canvas_time = None
        self.canvas_2d = None
        self.canvas_3d = None
        self.canvas_total = None
        
        self.show_quiver_var = tk.BooleanVar(value=False)
        self.color_trend_var = tk.BooleanVar(value=False)
        
        self._setup_ui()
        self.refresh_data()

    def on_closing(self):
        plt.close('all') 
        self.root.quit() 
        self.root.destroy() 

    def _setup_ui(self):
        toolbar = ttk.Frame(self.root, padding="10 10 10 5")
        toolbar.pack(side="top", fill="x")
        
        # Gruppe 1: Punktauswahl
        frame_auswahl = ttk.LabelFrame(toolbar, text="  Punktauswahl ", padding=5)
        frame_auswahl.pack(side="left", padx=(0, 15), fill="y")
        
        self.cb_points = ttk.Combobox(frame_auswahl, state="readonly", width=15)
        self.cb_points.pack(side="left", padx=5, pady=2)
        self.cb_points.bind("<<ComboboxSelected>>", self.on_point_select)
        
        # Gruppe 2: Darstellungsoptionen (2D/3D)
        frame_opt = ttk.LabelFrame(toolbar, text="  Darstellungsoptionen (2D & 3D) ", padding=5)
        frame_opt.pack(side="left", padx=(0, 15), fill="y")
        
        self.cb_color = ttk.Checkbutton(frame_opt, text="Zeit-Farbverlauf", 
                                         variable=self.color_trend_var, 
                                         command=self.on_toggle_update)
        self.cb_color.pack(side="left", padx=10, pady=2)

        self.cb_quiver = ttk.Checkbutton(frame_opt, text="Vektorpfeile", 
                                         variable=self.show_quiver_var, 
                                         command=self.on_toggle_update)
        self.cb_quiver.pack(side="left", padx=10, pady=2)
        
        # Gruppe 3: Aktionen
        frame_act = ttk.LabelFrame(toolbar, text="  Aktionen ", padding=5)
        frame_act.pack(side="right", fill="y")
        
        ttk.Button(frame_act, text=" Daten neu laden", command=self.refresh_data).pack(side="left", padx=5, pady=2)
        
        # --- Tabs ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(side="top", fill="both", expand=True, padx=10, pady=5)
        
        self.tab_map = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_map, text="🗺️ Netzübersicht (Soll)")

        self.tab_time = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_time, text="XYZ Zeitverlauf")
        
        self.tab_2d = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_2d, text="2D Bewegung (X/Y)")

        self.tab_3d = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_3d, text="3D Bewegung (X/Y/Z)")
        
        self.tab_total = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_total, text="Totale Verschiebung (3D)")
        
    def refresh_data(self):
        success, msg = self.data_manager.load_and_process_data()
        if not success:
            messagebox.showwarning("Hinweis", msg)
            return
            
        self.cb_points['values'] = self.data_manager.points
        if self.data_manager.points:
            self.cb_points.set(self.data_manager.points[0])
            self.draw_plots(self.data_manager.points[0])
            
    def on_point_select(self, event):
        selected_point = self.cb_points.get()
        if selected_point:
            self.draw_plots(selected_point)
            
    def on_toggle_update(self):
        selected_point = self.cb_points.get()
        if selected_point:
            self.draw_plots(selected_point)
            
    def draw_plots(self, pnr):
        # Bereinigung alter Diagramme
        if self.canvas_map:
            self.canvas_map.get_tk_widget().destroy()
            for widget in self.tab_map.winfo_children(): widget.destroy()
        if self.fig_map: plt.close(self.fig_map)

        if self.canvas_time:
            self.canvas_time.get_tk_widget().destroy()
            for widget in self.tab_time.winfo_children(): widget.destroy()
        if self.fig_time: plt.close(self.fig_time)
            
        if self.canvas_2d:
            self.canvas_2d.get_tk_widget().destroy()
            for widget in self.tab_2d.winfo_children(): widget.destroy()
        if self.fig_2d: plt.close(self.fig_2d)

        if self.canvas_3d:
            self.canvas_3d.get_tk_widget().destroy()
            for widget in self.tab_3d.winfo_children(): widget.destroy()
        if self.fig_3d: plt.close(self.fig_3d)
        
        if self.canvas_total:
            self.canvas_total.get_tk_widget().destroy()
            for widget in self.tab_total.winfo_children(): widget.destroy()
        if self.fig_total: plt.close(self.fig_total)
            
        df_pnr = self.data_manager.df[self.data_manager.df['PNR'] == pnr].copy()
        if df_pnr.empty: return
        
        df_pnr['Datum_Str'] = df_pnr['Datum'].dt.strftime('%d.%m.%Y %H:%M')
        dates = df_pnr['Datum'].to_numpy()
        x_data = df_pnr['dX_mm'].to_numpy()
        y_data = df_pnr['dY_mm'].to_numpy()
        z_data = df_pnr['dZ_mm'].to_numpy()
        d3d_data = df_pnr['d3D_mm'].to_numpy()
        dates_list = df_pnr['Datum_Str'].to_list()

        epoch_indices = np.arange(len(x_data))

        loc_1mm = MultipleLocator(1)
        red_spines_color = "#FF0000"
        bg_color = "#F0F0F0"
        grid_color = "#A0A0A0" 
        
        # ==========================================
        # TAB 0: KARTENDARSTELLUNG / NETZÜBERSICHT
        # ==========================================
        self.fig_map, ax_map = plt.subplots(figsize=(8, 6))
        self.fig_map.suptitle("Kartendarstellung / Netzübersicht (Soll-Koordinaten)", fontsize=14)
        ax_map.set_facecolor(bg_color)
        ax_map.set_aspect('equal', adjustable='datalim') 
        
        if self.data_manager.soll_coords:
            for pt in self.data_manager.soll_coords:
                p_id = str(pt.get("PNR", pt.get("pnr", "")))
                px = pt.get("X", pt.get("x", 0.0))
                py = pt.get("Y", pt.get("y", 0.0))
                
                is_selected = (p_id == pnr)
                
                color = "red" if is_selected else "blue"
                size = 120 if is_selected else 50
                edge = "black" if is_selected else "none"
                z = 4 if is_selected else 3
                
                ax_map.scatter(px, py, c=color, s=size, edgecolors=edge, zorder=z)
                
                weight = "bold" if is_selected else "normal"
                ax_map.annotate(p_id, (px, py), xytext=(6, 6), textcoords='offset points', 
                                fontsize=10, weight=weight, color="black", 
                                bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7, ec="none"))
                                
            ax_map.set_xlabel('Rechtswert [m]')
            ax_map.set_ylabel('Hochwert [m]')
            ax_map.grid(True, linestyle='--', alpha=0.8, color=grid_color)
            ax_map.spines['left'].set_color(red_spines_color)
            ax_map.spines['bottom'].set_color(red_spines_color)
            
        else:
            ax_map.text(0.5, 0.5, "Keine Soll-Koordinaten gefunden\n(Bitte parameter/params.txt prüfen)", 
                        ha='center', va='center', fontsize=12, color='gray')
            
        self.fig_map.tight_layout()
        self.canvas_map = FigureCanvasTkAgg(self.fig_map, master=self.tab_map)
        self.canvas_map.draw()
        self.canvas_map.get_tk_widget().pack(fill="both", expand=True)
        toolbar_map = NavigationToolbar2Tk(self.canvas_map, self.tab_map)
        toolbar_map.update()
        toolbar_map.pack(side="top", fill="x")

        # ==========================================
        # TAB 1: ZEITVERLAUF (3 Graphen)
        # ==========================================
        self.fig_time, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(8, 6), sharex=True)
        self.fig_time.suptitle(f"Verschiebungen für Punkt: {pnr} (Referenz: {df_pnr['Datum_Str'].iloc[0]})", fontsize=14)
        
        axis_line_alpha = 0.5
        axhline_kwargs = {'color': red_spines_color, 'linewidth': 1, 'linestyle': '-', 'alpha': axis_line_alpha}

        for ax in (ax1, ax2, ax3):
            ax.set_facecolor(bg_color)
            ax.yaxis.set_major_locator(loc_1mm)
            ax.spines['left'].set_color(red_spines_color)
            ax.spines['bottom'].set_color(red_spines_color)
            ax.tick_params(axis='both', which='major', length=6, width=1.5, colors=red_spines_color, direction='out')
            ax.grid(True, linestyle='--', alpha=0.8, color=grid_color)
            ax.axhline(0, **axhline_kwargs)

        ax1.plot(dates, x_data, marker='o', color='blue', linestyle='-')
        ax1.set_ylabel('dX [mm]')
        
        ax2.plot(dates, y_data, marker='o', color='green', linestyle='-')
        ax2.set_ylabel('dY [mm]')
        
        ax3.plot(dates, z_data, marker='o', color='red', linestyle='-')
        ax3.set_ylabel('dZ [mm]')
        ax3.set_xlabel('Datum / Epoche')
        
        self.fig_time.autofmt_xdate()
        self.fig_time.tight_layout()
        
        self.canvas_time = FigureCanvasTkAgg(self.fig_time, master=self.tab_time)
        self.canvas_time.draw()
        self.canvas_time.get_tk_widget().pack(fill="both", expand=True)
        toolbar_time = NavigationToolbar2Tk(self.canvas_time, self.tab_time)
        toolbar_time.update()
        toolbar_time.pack(side="top", fill="x")

        # ==========================================
        # TAB 2: 2D BEWEGUNG
        # ==========================================
        self.fig_2d, ax_2d = plt.subplots(figsize=(8, 6))
        self.fig_2d.suptitle(f"2D Bewegungsverlauf (X/Y) für Punkt: {pnr}", fontsize=14)
        ax_2d.set_facecolor(bg_color)
        ax_2d.set_aspect('equal', adjustable='datalim')
        
        if self.color_trend_var.get():
            sc = ax_2d.scatter(x_data, y_data, c=epoch_indices, cmap='viridis', s=50, picker=True, zorder=3)
            cbar = self.fig_2d.colorbar(sc, ax=ax_2d, shrink=0.8, pad=0.05)
            cbar.set_label('Epochenverlauf (Alt → Neu)', rotation=270, labelpad=15)
            if len(epoch_indices) > 1:
                cbar.set_ticks([epoch_indices[0], epoch_indices[-1]])
                cbar.set_ticklabels([dates_list[0].split()[0], dates_list[-1].split()[0]])
        else:
            sc = ax_2d.scatter(x_data, y_data, c='blue', s=50, picker=True, zorder=3)
        
        if self.show_quiver_var.get() and len(x_data) > 1:
            u = np.diff(x_data)
            v = np.diff(y_data)
            ax_2d.quiver(x_data[:-1], y_data[:-1], u, v, angles='xy', scale_units='xy', scale=1, 
                         color='orange', alpha=0.9, width=0.005, zorder=2)
        
        ax_2d.xaxis.set_major_locator(loc_1mm)
        ax_2d.yaxis.set_major_locator(loc_1mm)
        ax_2d.set_xlabel('dX [mm]')
        ax_2d.set_ylabel('dY [mm]')
        
        min_x_2d = min(x_data.min(), -1.05)
        max_x_2d = max(x_data.max(), 1.05)
        min_y_2d = min(y_data.min(), -1.05)
        max_y_2d = max(y_data.max(), 1.05)
        ax_2d.set_xlim(min_x_2d, max_x_2d)
        ax_2d.set_ylim(min_y_2d, max_y_2d)
        
        ax_2d.spines['left'].set_color(red_spines_color)
        ax_2d.spines['bottom'].set_color(red_spines_color)
        ax_2d.tick_params(axis='both', which='major', length=6, width=1.5, colors=red_spines_color, direction='out')
        
        ax_2d.axhline(0, **axhline_kwargs) 
        ax_2d.axvline(0, **axhline_kwargs) 
        ax_2d.grid(True, linestyle='--', alpha=0.8, color=grid_color)
        
        annot = ax_2d.annotate("", xy=(0,0), xytext=(10,10), textcoords="offset points",
                               bbox=dict(boxstyle="round", fc="yellow", alpha=0.9),
                               arrowprops=dict(arrowstyle="->", connectionstyle="arc3"))
        annot.set_visible(False)

        def update_annot(ind):
            pos = sc.get_offsets()[ind["ind"][0]]
            annot.xy = pos
            idx = ind["ind"][0]
            annot.set_text(f"Epoche: {idx}\nDatum: {dates_list[idx]}\ndX: {x_data[idx]:.1f} mm\ndY: {y_data[idx]:.1f} mm")
            annot.get_bbox_patch().set_alpha(0.9)

        def hover(event):
            vis = annot.get_visible()
            if event.inaxes == ax_2d:
                cont, ind = sc.contains(event)
                if cont:
                    update_annot(ind)
                    annot.set_visible(True)
                    self.fig_2d.canvas.draw_idle()
                else:
                    if vis:
                        annot.set_visible(False)
                        self.fig_2d.canvas.draw_idle()

        self.fig_2d.canvas.mpl_connect("motion_notify_event", hover)
        self.fig_2d.tight_layout()
        
        self.canvas_2d = FigureCanvasTkAgg(self.fig_2d, master=self.tab_2d)
        self.canvas_2d.draw()
        self.canvas_2d.get_tk_widget().pack(fill="both", expand=True)
        toolbar_2d = NavigationToolbar2Tk(self.canvas_2d, self.tab_2d)
        toolbar_2d.update()
        toolbar_2d.pack(side="top", fill="x")

        # ==========================================
        # TAB 3: 3D BEWEGUNG 
        # ==========================================
        self.fig_3d, ax_3d = plt.subplots(figsize=(8, 6), subplot_kw={'projection': '3d'})
        self.fig_3d.suptitle(f"3D Bewegungsverlauf (X/Y/Z) für Punkt: {pnr}", fontsize=14)
        
        self.fig_3d.patch.set_facecolor(bg_color)

        if self.color_trend_var.get():
            sc_3d = ax_3d.scatter(x_data, y_data, z_data, c=epoch_indices, cmap='viridis', s=50)
            cbar3 = self.fig_3d.colorbar(sc_3d, ax=ax_3d, shrink=0.7, pad=0.1)
            cbar3.set_label('Epochenverlauf (Alt → Neu)', rotation=270, labelpad=15)
            if len(epoch_indices) > 1:
                cbar3.set_ticks([epoch_indices[0], epoch_indices[-1]])
                cbar3.set_ticklabels([dates_list[0].split()[0], dates_list[-1].split()[0]])
        else:
            ax_3d.scatter(x_data, y_data, z_data, c='blue', s=50)

        if self.show_quiver_var.get() and len(x_data) > 1:
            u = np.diff(x_data)
            v = np.diff(y_data)
            w = np.diff(z_data)
            ax_3d.quiver(x_data[:-1], y_data[:-1], z_data[:-1], u, v, w, 
                         color='orange', alpha=0.9, arrow_length_ratio=0.1)

        min_x_bnd = min(x_data.min(), -1.0)
        max_x_bnd = max(x_data.max(), 1.0)
        min_y_bnd = min(y_data.min(), -1.0)
        max_y_bnd = max(y_data.max(), 1.0)
        min_z_bnd = min(z_data.min(), -1.0)
        max_z_bnd = max(z_data.max(), 1.0)
        
        max_span = max(max_x_bnd - min_x_bnd, max_y_bnd - min_y_bnd, max_z_bnd - min_z_bnd) / 2.0
        
        mid_x = (max_x_bnd + min_x_bnd) / 2.0
        mid_y = (max_y_bnd + min_y_bnd) / 2.0
        mid_z = (max_z_bnd + min_z_bnd) / 2.0
        
        max_range = max_span * 1.05 
        
        min_x, max_x = mid_x - max_range, mid_x + max_range
        min_y, max_y = mid_y - max_range, mid_y + max_range
        min_z, max_z = mid_z - max_range, mid_z + max_range
        
        ax_3d.set_xlim(min_x, max_x)
        ax_3d.set_ylim(min_y, max_y)
        ax_3d.set_zlim(min_z, max_z)
        ax_3d.set_box_aspect((1, 1, 1)) 

        ax_3d.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax_3d.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax_3d.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        
        ax_3d.xaxis.line.set_color((1.0, 1.0, 1.0, 0.0))
        ax_3d.yaxis.line.set_color((1.0, 1.0, 1.0, 0.0))
        ax_3d.zaxis.line.set_color((1.0, 1.0, 1.0, 0.0))
        
        ax_3d.set_xticklabels([])
        ax_3d.set_yticklabels([])
        ax_3d.set_zticklabels([])
        ax_3d.tick_params(axis='both', length=0)

        ax_3d.quiver(min_x, 0, 0, max_x - min_x, 0, 0, color=red_spines_color, arrow_length_ratio=0.05, linewidth=1, alpha=0.8)
        ax_3d.quiver(0, min_y, 0, 0, max_y - min_y, 0, color=red_spines_color, arrow_length_ratio=0.05, linewidth=1, alpha=0.8)
        ax_3d.quiver(0, 0, min_z, 0, 0, max_z - min_z, color=red_spines_color, arrow_length_ratio=0.05, linewidth=1, alpha=0.8)

        tick_size = max_range * 0.03 
        
        for x_val in np.arange(np.ceil(min_x), np.floor(max_x) + 1):
            if x_val != 0: ax_3d.plot([x_val, x_val], [-tick_size, tick_size], [0, 0], color=red_spines_color, linewidth=1.5)
            
        for y_val in np.arange(np.ceil(min_y), np.floor(max_y) + 1):
            if y_val != 0: ax_3d.plot([-tick_size, tick_size], [y_val, y_val], [0, 0], color=red_spines_color, linewidth=1.5)
            
        for z_val in np.arange(np.ceil(min_z), np.floor(max_z) + 1):
            if z_val != 0: ax_3d.plot([-tick_size, tick_size], [0, 0], [z_val, z_val], color=red_spines_color, linewidth=1.5)

        ax_3d.text(max_x, 0, 0, '+dX [mm]', color=red_spines_color, ha='left', va='center')
        ax_3d.text(min_x, 0, 0, '-dX', color=red_spines_color, ha='right', va='center')
        
        ax_3d.text(0, max_y, 0, '+dY [mm]', color=red_spines_color, ha='center', va='center')
        ax_3d.text(0, min_y, 0, '-dY', color=red_spines_color, ha='center', va='center')
        
        ax_3d.text(0, 0, max_z, '+dZ [mm]', color=red_spines_color, ha='center', va='bottom')
        ax_3d.text(0, 0, min_z, '-dZ', color=red_spines_color, ha='center', va='top')
        
        ax_3d.xaxis.set_major_locator(loc_1mm)
        ax_3d.yaxis.set_major_locator(loc_1mm)
        ax_3d.zaxis.set_major_locator(loc_1mm)
        
        ax_3d.grid(True, linestyle='--', alpha=0.6, color=grid_color) 

        self.fig_3d.tight_layout()

        self.canvas_3d = FigureCanvasTkAgg(self.fig_3d, master=self.tab_3d)
        self.canvas_3d.draw()
        self.canvas_3d.get_tk_widget().pack(fill="both", expand=True)
        toolbar_3d = NavigationToolbar2Tk(self.canvas_3d, self.tab_3d)
        toolbar_3d.update()
        toolbar_3d.pack(side="top", fill="x")

        # ==========================================
        # TAB 4: TOTALE VERSCHIEBUNG (3D-Distanz)
        # ==========================================
        self.fig_total, ax_total = plt.subplots(figsize=(8, 6))
        self.fig_total.suptitle(f"Absolute 3D-Gesamtverschiebung für Punkt: {pnr}", fontsize=14)
        ax_total.set_facecolor(bg_color)
        
        ax_total.plot(dates, d3d_data, marker='o', color='purple', linestyle='-', linewidth=2)
        ax_total.set_ylabel('3D-Distanz [mm]')
        ax_total.set_xlabel('Datum / Epoche')
        ax_total.set_ylim(bottom=0) 
        
        ax_total.spines['left'].set_color(red_spines_color)
        ax_total.spines['bottom'].set_color(red_spines_color)
        
        ax_total.tick_params(axis='both', which='major', length=6, width=1.5, colors=red_spines_color, direction='out')
        
        ax_total.axhline(0, **axhline_kwargs) 
        ax_total.grid(True, linestyle='--', alpha=0.8, color=grid_color)
        
        self.fig_total.autofmt_xdate()
        self.fig_total.tight_layout()
        
        self.canvas_total = FigureCanvasTkAgg(self.fig_total, master=self.tab_total)
        self.canvas_total.draw()
        self.canvas_total.get_tk_widget().pack(fill="both", expand=True)
        toolbar_total = NavigationToolbar2Tk(self.canvas_total, self.tab_total)
        toolbar_total.update()
        toolbar_total.pack(side="top", fill="x")

if __name__ == "__main__":
    root = tk.Tk()
    app = MonitoringDashboard(root)
    root.mainloop()