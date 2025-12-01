"""
main window for stocksight
fixed size layout, optimized performance
"""


# ================ IMPORTS ================

import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import pandas as pd

# add project root to system path for consistent imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Paths, DataConfig, AutoTSConfig, ScenarioConfig
from core.state import STATE
from ui.callbacks import Callbacks
from ui.chart_frame import ChartFrame
from ui.tooltip import Tooltip
from datetime import datetime, timedelta
import calendar


# ================ MAIN APPLICATION ================

class StocksightApp:
    # color constants for status
    COLOR_SUCCESS = "#4caf50"
    COLOR_ERROR = "#f44336"
    COLOR_DEFAULT = ""

    def __init__(self, root):
        self.root = root
        self.root.title("Stocksight - Inventory Forecast")
        
        # ---------- FIXED SIZE FOR PERFORMANCE ----------
        self.root.geometry("1400x850")
        self.root.resizable(False, False)
        
        # ---------- APPLY THEME AND CREATE UI WIDGETS ----------
        self.apply_theme()
        self.create_custom_styles()
        self.create_ui()
        
        # get default label color after ui creation
        self.COLOR_DEFAULT = self.status_label.cget("foreground")

        # ---------- INITIALIZE CALLBACKS AFTER UI CREATION ----------
        self.callbacks = Callbacks(self)
        self.bind_ui_callbacks()
        
        # ---------- FINAL UI SETUP ----------
        self.add_tooltips()
        
        # ---------- BIND EVENTS ----------
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind("<Button-1>", self._clear_focus, add='+')
    
    def _clear_focus(self, event):
        # clear focus from widgets when clicking elsewhere
        widget = event.widget
        if not isinstance(widget, (ttk.Combobox, tk.Spinbox, ttk.Entry)):
            self.root.focus_set()
    
    def apply_theme(self):
        # apply sv-ttk theme if available
        try:
            import sv_ttk
            sv_ttk.set_theme("dark")
            self.has_sv_ttk = True
            print("sv-ttk dark theme applied")
        except ImportError:
            print("sv-ttk not found, using default theme")
            self.has_sv_ttk = False
            style = ttk.Style()
            style.configure("Accent.TButton", font=("", 10, "bold"))
            
    def create_custom_styles(self):
        # create custom colored styles for labels and frames
        style = ttk.Style()
        
        # frames cards
        style.configure("BigCard.TFrame", relief="raised", borderwidth=1)
        style.configure("Card.TFrame", relief="groove", borderwidth=1)
        style.configure("ActivityCard.TFrame", relief="groove", borderwidth=1)
    
    def toggle_theme(self):
        # toggle between dark and light theme
        if self.has_sv_ttk:
            import sv_ttk
            current = sv_ttk.get_theme()
            new_theme = "light" if current == "dark" else "dark"
            sv_ttk.set_theme(new_theme)
            bg = "#fafafa" if new_theme == "light" else "#1c1c1c"
            self.chart_frame.canvas.config(bg=bg)
            
            # update color constants if needed for visibility
            self.COLOR_DEFAULT = ttk.Label(self.root).cget("foreground")
            self.status_label.config(foreground=self.COLOR_DEFAULT)

    def on_closing(self):
        # handle window close
        if STATE.is_forecasting:
            if messagebox.askokcancel("Quit", "Forecast is running. Quit anyway?"):
                STATE.request_cancel()
                self.root.destroy()
        else:
            self.root.destroy()
    
    # ================ MAIN UI ================
    
    def create_ui(self):
        # create main user interface fixed layout
        # ---------- MAIN CONTAINER ----------
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # ---------- LEFT PANEL (FIXED 320px) ----------
        left_frame = ttk.Frame(main_frame, width=320)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_frame.pack_propagate(False)
        
        self.create_left_panel(left_frame)
        
        # ---------- RIGHT PANEL ----------
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.create_right_panel(right_frame)
        self.create_status_bar()

    def bind_ui_callbacks(self):
        # bind all widget commands to their callback functions
        # controls tab
        self.upload_btn.config(command=self.callbacks.upload_file)
        self.remap_btn.config(command=self.callbacks.remap_columns)
        self.remove_data_btn.config(command=self.callbacks.remove_data)
        self.gran_combo.bind("<<ComboboxSelected>>", self.callbacks.on_granularity_changed)
        self.forecast_btn.config(command=self.callbacks.run_forecast)
        self.load_model_btn.config(command=self.callbacks.load_model)
        self.remove_model_btn.config(command=self.callbacks.remove_model)
        self.export_btn.config(command=self.callbacks.export_results)
        self.save_model_btn.config(command=self.callbacks.export_model)
        self.theme_btn.config(command=self.toggle_theme)

        # scenarios tab
        self.scenario_type_combo.bind("<<ComboboxSelected>>", self.callbacks.on_scenario_type_changed)
        self.multiplier_scale.config(command=self.callbacks.update_multiplier_label)
        self.delay_scale.config(command=self.callbacks.update_delay_label)
        self.week_btn.config(command=self.callbacks.set_date_week)
        self.month_btn.config(command=self.callbacks.set_date_month)
        self.next_btn.config(command=self.callbacks.set_date_next)
        self.apply_scenario_btn.config(command=self.callbacks.apply_scenario)
        self.reset_scenarios_btn.config(command=self.callbacks.reset_scenarios)
        
        # chart tab
        self.chart_sku_combo.bind("<<ComboboxSelected>>", self.callbacks.on_chart_sku_changed)
        self.refresh_chart_btn.config(command=self.callbacks.refresh_chart)
        self.summary_chart_btn.config(command=self.callbacks.show_summary)
        self.zoom_chart_btn.config(command=self.callbacks.zoom_chart)

        # dashboard tab
        self.dash_sku_combo.bind("<<ComboboxSelected>>", self.callbacks.on_dash_sku_changed)
        self.refresh_dash_btn.config(command=self.callbacks.refresh_dashboard)
        self.seasonality_btn.config(command=self.callbacks.show_seasonality)
        self.report_btn.config(command=self.callbacks.show_diagnostics)

    def add_tooltips(self):
        # add descriptive tooltips to complex widgets
        Tooltip(self.gran_combo, "Group data before forecasting.\nWeekly/Monthly is faster and smoother for noisy data.")
        Tooltip(self.speed_combo, "Superfast: Quickest, least accurate.\nFast: Good balance.\nBalanced: More thorough.\nAccurate: Slowest, most comprehensive.")
        Tooltip(self.scenario_type_combo, "Demand Spike: Increase demand by a multiplier for a period.\nSupply Delay: Shift incoming supply forward by N days.")
        Tooltip(self.multiplier_scale, "Factor to multiply demand by (e.g., 2.0 = 200% of normal).")
        Tooltip(self.delay_scale, "Number of days to delay supply for a SKU.")
        Tooltip(self.days_spinbox, "Number of future periods to forecast, based on the selected Granularity.")

    def create_left_panel(self, parent):
        # create left control panel
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # ---------- CONTROLS TAB ----------
        controls_frame = ttk.Frame(notebook, padding=(15, 10))
        notebook.add(controls_frame, text="Controls")
        self.create_controls_tab(controls_frame)
        
        # ---------- SCENARIOS TAB ----------
        scenarios_frame = ttk.Frame(notebook, padding=(15, 10))
        notebook.add(scenarios_frame, text="Scenarios")
        self.create_scenarios_tab(scenarios_frame)
    
    def create_controls_tab(self, parent):
        # create controls tab content compact layout
        # ---------- DATA ----------
        ttk.Label(parent, text="DATA", font=("", 10, "bold")).pack(anchor=tk.W)
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(3, 8))
        
        self.upload_btn = ttk.Button(parent, text="Upload CSV/Excel", style="Accent.TButton")
        self.upload_btn.pack(fill=tk.X, pady=1)
        self.remap_btn = ttk.Button(parent, text="Remap Columns")
        self.remap_btn.pack(fill=tk.X, pady=1)
        self.remove_data_btn = ttk.Button(parent, text="Remove Data")
        self.remove_data_btn.pack(fill=tk.X, pady=1)
        
        self.data_info_var = tk.StringVar(value="No data loaded")
        ttk.Label(parent, textvariable=self.data_info_var, 
                  foreground="gray", wraplength=270, font=("", 8)).pack(anchor=tk.W, pady=(5, 0))
        
        ttk.Label(parent, text="").pack(pady=3)
        
        # ---------- SEASONALITY ----------
        ttk.Label(parent, text="SEASONALITY", font=("", 10, "bold")).pack(anchor=tk.W)
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(3, 8))
        
        self.seasonality_var = tk.StringVar(value="No data analyzed")
        ttk.Label(parent, textvariable=self.seasonality_var,
                  foreground="gray", wraplength=270, font=("", 8)).pack(anchor=tk.W)
        
        ttk.Label(parent, text="").pack(pady=3)
        
        # ---------- FORECAST ----------
        ttk.Label(parent, text="FORECAST", font=("", 10, "bold")).pack(anchor=tk.W)
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(3, 8))
        
        ttk.Label(parent, text="Periods to Forecast:", font=("", 8)).pack(anchor=tk.W)
        self.days_var = tk.IntVar(value=AutoTSConfig.DEFAULT_FORECAST_DAYS)
        self.days_spinbox = ttk.Spinbox(parent, from_=1, to=365, textvariable=self.days_var, width=12)
        self.days_spinbox.pack(anchor=tk.W, pady=1)
        
        ttk.Label(parent, text="Granularity:", font=("", 8)).pack(anchor=tk.W, pady=(5, 0))
        self.granularity_var = tk.StringVar(value="Daily")
        self.gran_combo = ttk.Combobox(parent, textvariable=self.granularity_var,
                     values=DataConfig.GROUP_OPTIONS, state="readonly", width=16)
        self.gran_combo.pack(anchor=tk.W, pady=1)
        
        ttk.Label(parent, text="Speed:", font=("", 8)).pack(anchor=tk.W, pady=(5, 0))
        self.speed_var = tk.StringVar(value="Fast")
        self.speed_combo = ttk.Combobox(parent, textvariable=self.speed_var,
                     values=["Superfast", "Fast", "Balanced", "Accurate"],
                     state="readonly", width=16)
        self.speed_combo.pack(anchor=tk.W, pady=1)
        
        ttk.Label(parent, text="").pack(pady=3)
        
        self.forecast_btn = ttk.Button(parent, text="Run Forecast", style="Accent.TButton")
        self.forecast_btn.pack(fill=tk.X, pady=2, ipady=5)
        
        self.timer_var = tk.StringVar(value="")
        ttk.Label(parent, textvariable=self.timer_var, foreground="gray", font=("", 8)).pack(anchor=tk.W)
        
        ttk.Label(parent, text="").pack(pady=3)
        
        # ---------- MODEL ----------
        ttk.Label(parent, text="MODEL", font=("", 10, "bold")).pack(anchor=tk.W)
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(3, 8))
        
        self.model_info_var = tk.StringVar(value="No model loaded")
        ttk.Label(parent, textvariable=self.model_info_var,
                  foreground="gray", wraplength=270, font=("", 8)).pack(anchor=tk.W)
        
        model_btns = ttk.Frame(parent)
        model_btns.pack(fill=tk.X, pady=3)
        
        self.load_model_btn = ttk.Button(model_btns, text="Load Model")
        self.load_model_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.remove_model_btn = ttk.Button(model_btns, text="Remove Model")
        
        # hide remove button initially
        self.remove_model_btn.pack_forget()

        ttk.Label(parent, text="").pack(pady=3)
        
        # ---------- EXPORT & SETTINGS ----------
        ttk.Label(parent, text="UTILITIES", font=("", 10, "bold")).pack(anchor=tk.W)
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(3, 8))
        
        export_btns = ttk.Frame(parent)
        export_btns.pack(fill=tk.X, pady=3)
        
        self.export_btn = ttk.Button(export_btns, text="Export")
        self.export_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.save_model_btn = ttk.Button(export_btns, text="Save Model")
        self.save_model_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.theme_btn = ttk.Button(export_btns, text="Theme")
        self.theme_btn.pack(side=tk.LEFT)
    
    def create_scenarios_tab(self, parent):
        # create scenarios tab content
        # ---------- SCENARIO TYPE ----------
        ttk.Label(parent, text="SCENARIO", font=("", 10, "bold")).pack(anchor=tk.W)
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(3, 8))
        
        ttk.Label(parent, text="Type:", font=("", 8)).pack(anchor=tk.W)
        self.scenario_type_var = tk.StringVar(value="Demand Spike")
        self.scenario_type_combo = ttk.Combobox(parent, textvariable=self.scenario_type_var,
                                                 values=["Demand Spike", "Supply Delay"],
                                                 state="readonly", width=16)
        self.scenario_type_combo.pack(anchor=tk.W, pady=1)
        
        ttk.Label(parent, text="").pack(pady=3)
        
        ttk.Label(parent, text="Target SKU:", font=("", 8)).pack(anchor=tk.W)
        self.scenario_sku_var = tk.StringVar()
        self.scenario_sku_combo = ttk.Combobox(parent, textvariable=self.scenario_sku_var,
                                                state="readonly", width=20)
        self.scenario_sku_combo.pack(anchor=tk.W, pady=1)
        
        ttk.Label(parent, text="").pack(pady=3)
        
        # ---------- PARAMETERS ----------
        ttk.Label(parent, text="PARAMETERS", font=("", 10, "bold")).pack(anchor=tk.W)
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(3, 8))
        
        self.multiplier_frame = ttk.Frame(parent)
        self.multiplier_frame.pack(fill=tk.X)
        
        ttk.Label(self.multiplier_frame, text="Multiplier:", font=("", 8)).pack(anchor=tk.W)
        self.multiplier_var = tk.DoubleVar(value=ScenarioConfig.DEFAULT_SPIKE_MULTIPLIER)
        self.multiplier_scale = ttk.Scale(self.multiplier_frame, from_=0.1, to=5.0,
                                      variable=self.multiplier_var, orient=tk.HORIZONTAL)
        self.multiplier_scale.pack(fill=tk.X, pady=1)
        self.multiplier_label = ttk.Label(self.multiplier_frame, text="1.5x", font=("", 8))
        self.multiplier_label.pack(anchor=tk.W)
        
        self.delay_frame = ttk.Frame(parent)
        ttk.Label(self.delay_frame, text="Delay Days:", font=("", 8)).pack(anchor=tk.W)
        self.delay_var = tk.IntVar(value=ScenarioConfig.DEFAULT_DELAY_DAYS)
        self.delay_scale = ttk.Scale(self.delay_frame, from_=1, to=90,
                                 variable=self.delay_var, orient=tk.HORIZONTAL)
        self.delay_scale.pack(fill=tk.X, pady=1)
        self.delay_label = ttk.Label(self.delay_frame, text="7 days", font=("", 8))
        self.delay_label.pack(anchor=tk.W)
        
        ttk.Label(parent, text="").pack(pady=3)
        
        # ---------- DATE RANGE ----------
        ttk.Label(parent, text="DATE RANGE", font=("", 10, "bold")).pack(anchor=tk.W)
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(3, 8))
        
        quick_btns = ttk.Frame(parent)
        quick_btns.pack(anchor=tk.W, pady=3)
        self.week_btn = ttk.Button(quick_btns, text="Week", width=6)
        self.week_btn.pack(side=tk.LEFT, padx=(0, 3))
        self.month_btn = ttk.Button(quick_btns, text="Month", width=6)
        self.month_btn.pack(side=tk.LEFT, padx=(0, 3))
        self.next_btn = ttk.Button(quick_btns, text="Next", width=6)
        self.next_btn.pack(side=tk.LEFT)
        
        ttk.Label(parent, text="Start:", font=("", 8)).pack(anchor=tk.W, pady=(5, 0))
        self.start_date_var = tk.StringVar(value="2024-01-01")
        ttk.Entry(parent, textvariable=self.start_date_var, width=15).pack(anchor=tk.W, pady=1)
        
        ttk.Label(parent, text="End:", font=("", 8)).pack(anchor=tk.W, pady=(5, 0))
        self.end_date_var = tk.StringVar(value="2024-01-31")
        ttk.Entry(parent, textvariable=self.end_date_var, width=15).pack(anchor=tk.W, pady=1)
        
        ttk.Label(parent, text="").pack(pady=10)
        
        # ---------- ACTION BUTTONS ----------
        action_btns = ttk.Frame(parent)
        action_btns.pack(anchor=tk.W, pady=5)
        self.apply_scenario_btn = ttk.Button(action_btns, text="Apply Scenario", style="Accent.TButton")
        self.apply_scenario_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.reset_scenarios_btn = ttk.Button(action_btns, text="Reset All")
        self.reset_scenarios_btn.pack(side=tk.LEFT)
    
    def create_right_panel(self, parent):
        # create right content panel
        self.right_notebook = ttk.Notebook(parent)
        self.right_notebook.pack(fill=tk.BOTH, expand=True)
        
        preview_frame = ttk.Frame(self.right_notebook, padding=10)
        self.right_notebook.add(preview_frame, text="Data Preview")
        self.create_preview_tab(preview_frame)
        
        chart_tab = ttk.Frame(self.right_notebook, padding=10)
        self.right_notebook.add(chart_tab, text="Forecast Chart")
        self.create_chart_tab(chart_tab)
        
        dashboard_frame = ttk.Frame(self.right_notebook, padding=10)
        self.right_notebook.add(dashboard_frame, text="Dashboard")
        self.create_dashboard_tab(dashboard_frame)
    
    def create_preview_tab(self, parent):
        # create data preview tab
        self.preview_info_var = tk.StringVar(value="Load a file to see data preview")
        ttk.Label(parent, textvariable=self.preview_info_var, foreground="gray").pack(anchor=tk.W, pady=(0, 5))
        
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("Date", "SKU", "Quantity")
        self.preview_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        
        for col in columns:
            self.preview_tree.heading(col, text=col)
            self.preview_tree.column(col, width=150)
        
        y_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.preview_tree.yview)
        x_scroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.preview_tree.xview)
        self.preview_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        
        self.preview_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
    
    def create_chart_tab(self, parent):
        # create forecast chart tab
        controls = ttk.Frame(parent)
        controls.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(controls, text="SKU:").pack(side=tk.LEFT)
        self.chart_sku_var = tk.StringVar(value="All SKUs")
        self.chart_sku_combo = ttk.Combobox(controls, textvariable=self.chart_sku_var,
                                             values=["All SKUs"], state="readonly", width=15)
        self.chart_sku_combo.pack(side=tk.LEFT, padx=(5, 20))
        
        self.refresh_chart_btn = ttk.Button(controls, text="Refresh")
        self.refresh_chart_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.summary_chart_btn = ttk.Button(controls, text="Summary")
        self.summary_chart_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.zoom_chart_btn = ttk.Button(controls, text="Zoom")
        self.zoom_chart_btn.pack(side=tk.LEFT)
        
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        self.chart_frame = ChartFrame(parent)
        self.chart_frame.pack(fill=tk.BOTH, expand=True)
    
    def create_dashboard_tab(self, parent):
        # create dashboard tab with big card and box-styled stats
        controls = ttk.Frame(parent)
        controls.pack(fill=tk.X, pady=(0, 10))
        
        # no separate grouping for dashboard syncs with main granularity
        ttk.Label(controls, text="SKU Filter:").pack(side=tk.LEFT)
        self.dash_sku_var = tk.StringVar(value="All SKUs")
        self.dash_sku_combo = ttk.Combobox(controls, textvariable=self.dash_sku_var,
                                            values=["All SKUs"], state="readonly", width=15)
        self.dash_sku_combo.pack(side=tk.LEFT, padx=(5, 20))
        
        self.refresh_dash_btn = ttk.Button(controls, text="Refresh")
        self.refresh_dash_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.seasonality_btn = ttk.Button(controls, text="Seasonality")
        self.seasonality_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.report_btn = ttk.Button(controls, text="SKU Report")
        self.report_btn.pack(side=tk.LEFT)
        
        # ---------- STATS IN BOXES ----------
        ttk.Label(parent, text="STATISTICS", font=("", 11, "bold")).pack(anchor=tk.W, pady=(10, 5))
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 10))
        
        stats_container = ttk.Frame(parent)
        stats_container.pack(fill=tk.X)
        self.stat_labels = {}
        
        def create_stat_card(container, title, key, big_font=("", 14, "bold")):
            card = ttk.Frame(container, style="Card.TFrame", padding=10)
            card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
            ttk.Label(card, text=title, foreground="gray", font=("", 9)).pack(anchor=tk.W)
            lbl = ttk.Label(card, text="--", font=big_font)
            lbl.pack(anchor=tk.W, pady=(5, 0))
            self.stat_labels[key] = lbl
            return card

        row1 = ttk.Frame(stats_container)
        row1.pack(fill=tk.X, pady=5)
        create_stat_card(row1, "Total Forecast", "total")
        create_stat_card(row1, "Avg Daily (Overall)", "avg")
        create_stat_card(row1, "Unique SKUs", "skus")
        create_stat_card(row1, "Avg Error Margin", "error", big_font=("", 12, "bold"))

        row2 = ttk.Frame(stats_container)
        row2.pack(fill=tk.X, pady=5)
        create_stat_card(row2, "Date Range", "date_range", big_font=("", 11))
        create_stat_card(row2, "95% Confidence Range", "confidence", big_font=("", 11))
            
        ttk.Label(parent, text="").pack(pady=5)
        
        # ---------- ACTIVITY CARDS VERTICAL FULL WIDTH ----------
        canvas_container = ttk.Frame(parent)
        canvas_container.pack(fill=tk.BOTH, expand=True)
        
        self.activity_canvas = tk.Canvas(canvas_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=self.activity_canvas.yview)
        self.activity_card_frame = ttk.Frame(self.activity_canvas)
        
        self.canvas_window_id = self.activity_canvas.create_window((0, 0), window=self.activity_card_frame, anchor="nw")
        
        self.activity_card_frame.bind("<Configure>", lambda e: self.activity_canvas.configure(scrollregion=self.activity_canvas.bbox("all")))
        self.activity_canvas.bind("<Configure>", self._on_canvas_configure)
        self.activity_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.activity_canvas.bind("<Enter>", self._bind_mousewheel_activity)
        self.activity_canvas.bind("<Leave>", self._unbind_mousewheel_activity)
        
        self.activity_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _on_canvas_configure(self, event):
        # make inner frame match canvas width
        self.activity_canvas.itemconfig(self.canvas_window_id, width=event.width)
    
    def _on_activity_mousewheel(self, event):
        # scroll activity canvas
        self.activity_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _bind_mousewheel_activity(self, event):
        # bind mousewheel for activity canvas
        self.activity_canvas.bind_all("<MouseWheel>", self._on_activity_mousewheel)
    
    def _unbind_mousewheel_activity(self, event):
        # unbind mousewheel for activity canvas
        self.activity_canvas.unbind_all("<MouseWheel>")
    
    # ================ STATUS BAR ================
    
    def create_status_bar(self):
        # create status bar at bottom
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)
        
        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT)
        
        self.progress_bar = ttk.Progressbar(status_frame, length=200, mode="indeterminate")
    
    def set_status(self, message, is_error=False, is_success=False):
        # update status bar message and color
        self.status_label.config(text=message)
        
        if is_error:
            self.status_label.config(foreground=self.COLOR_ERROR)
        elif is_success:
            self.status_label.config(foreground=self.COLOR_SUCCESS)
        else:
            self.status_label.config(foreground=self.COLOR_DEFAULT)
        
        print(f"[STATUS] {message}")
    
    def show_progress(self, show=True):
        # show or hide progress bar
        if show:
            self.progress_bar.pack(side=tk.RIGHT, padx=10)
            self.progress_bar.start(10)
        else:
            self.progress_bar.stop()
            self.progress_bar.pack_forget()