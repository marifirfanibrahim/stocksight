"""
callback functions for stocksight ui
"""


# ================ IMPORTS ================

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
from pathlib import Path
import threading
import time
import os
import sys
import pickle
from datetime import datetime, timedelta
import calendar
import pandas as pd
import traceback

# ---------- ADD PATH ----------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Paths, ExportConfig, DataConfig, DisplayConfig
from core.state import STATE
from core.data_operations import (
    clear_all_data, validate_forecast_requirements,
    export_results, calculate_dashboard_data, get_output_directory
)
from core.forecasting import (
    run_forecast_thread, 
    load_saved_model, 
    forecast_with_loaded_model,
    forecast_with_parallel_models
)
from core.charting import generate_forecast_chart, generate_sku_summary_chart, generate_seasonality_chart
from utils.preprocessing import (
    detect_data_format, convert_wide_to_long, validate_columns,
    validate_data_types, clean_dataframe, get_sku_list, prepare_for_autots,
    aggregate_before_forecast
)
from utils.features import detect_seasonality_pattern


# ================ CALLBACKS CLASS ================

class Callbacks:
    def __init__(self, app):
        self.app = app
        self.timer_running = False
        self.timer_start = None
    
    # ================ FILE OPERATIONS ================
    
    def upload_file(self):
        # open file dialog and load data
        file_path = filedialog.askopenfilename(
            title="Select Data File",
            filetypes=[
                ("All Supported", "*.csv *.xlsx *.xls"),
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx *.xls"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path):
        # load csv or excel file
        try:
            self.app.set_status(f"Loading: {Path(file_path).name}...")
            
            ext = Path(file_path).suffix.lower()
            
            if ext == '.csv':
                df = pd.read_csv(file_path)
                file_info = "CSV"
            elif ext in ['.xlsx', '.xls']:
                excel_file = pd.ExcelFile(file_path)
                sheet_names = excel_file.sheet_names
                
                if len(sheet_names) > 1:
                    from ui.dialogs import SheetSelectionDialog
                    dialog = SheetSelectionDialog(self.app.root, sheet_names)
                    self.app.root.wait_window(dialog.dialog)
                    
                    if dialog.selected_sheet:
                        df = pd.read_excel(file_path, sheet_name=dialog.selected_sheet)
                        file_info = f"Excel ({dialog.selected_sheet})"
                    else:
                        self.app.set_status("Loading cancelled")
                        return
                else:
                    df = pd.read_excel(file_path, sheet_name=0)
                    file_info = "Excel"
            else:
                self.app.set_status(f"Unsupported file type: {ext}", is_error=True)
                return
            
            # store original raw data before any conversion
            original_df = df.copy()
            
            # check for wide format
            data_format = detect_data_format(df)
            
            if data_format == 'wide':
                self.app.set_status("Converting wide format...")
                df = convert_wide_to_long(df)
                file_info += " (Wide->Long)"
            
            # always show column mapper to allow for selecting additional columns
            from ui.dialogs import ColumnMapperDialog
            dialog = ColumnMapperDialog(self.app.root, df)
            
            self.app.root.wait_window(dialog.dialog)
            
            if dialog.result_df is not None:
                STATE.raw_data = original_df.copy()
                self.process_loaded_data(dialog.result_df, file_path, file_info)
            else:
                self.app.set_status("Loading cancelled")
                    
        except Exception as e:
            self.app.set_status(f"Error loading file: {e}", is_error=True)
            import traceback
            traceback.print_exc()
    
    def process_loaded_data(self, df, file_path, file_info):
        # process and store loaded dataframe
        try:
            valid, msg = validate_columns(df)
            if not valid:
                self.app.set_status(f"Error: {msg}", is_error=True)
                return
            
            valid, msg = validate_data_types(df)
            if not valid:
                self.app.set_status(f"Error: {msg}", is_error=True)
                return
            
            STATE.clean_data = clean_dataframe(df, store_format=True)
            STATE.sku_list = get_sku_list(STATE.clean_data)
            
            STATE.seasonality_info = detect_seasonality_pattern(STATE.clean_data)
            self.update_seasonality_display()
            
            self.update_sku_dropdowns()
            self.update_data_preview()
            
            extra_cols = len(STATE.additional_columns) if hasattr(STATE, 'additional_columns') else 0
            info_str = f"Records: {len(STATE.clean_data)} | SKUs: {len(STATE.sku_list)}"
            if extra_cols > 0:
                info_str += f" | Extra cols: {extra_cols}"
            
            self.app.data_info_var.set(info_str)
            self.app.set_status(f"Loaded: {len(STATE.clean_data)} records", is_success=True)
            
        except Exception as e:
            self.app.set_status(f"Error processing data: {e}", is_error=True)
            import traceback
            traceback.print_exc()
    
    def on_granularity_changed(self, event=None):
        # update preview when granularity changes
        self.update_data_preview()
    
    def update_data_preview(self):
        # update data preview table respects granularity formats dates and numbers
        tree = self.app.preview_tree
        for item in tree.get_children():
            tree.delete(item)
        
        if STATE.clean_data is None:
            self.app.preview_info_var.set("Load a file to see data preview")
            return
        
        data_to_show = STATE.clean_data.copy()
        granularity = self.app.granularity_var.get()
        
        if granularity != 'Daily':
             data_to_show = aggregate_before_forecast(data_to_show, granularity)
        
        # use original column names from mapping for headers
        columns = list(STATE.column_mapping.values()) + STATE.additional_columns
        tree["columns"] = columns
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor=tk.W)

        self.app.preview_info_var.set(f"Showing first 100 rows ({granularity})")
        
        date_format_str = DisplayConfig.DATE_FORMAT

        preview_rows = data_to_show.head(100)
        for _, row in preview_rows.iterrows():
            values = []
            # map back to original column names for row lookup
            for col_name in columns:
                # find internal name date sku etc for original name
                internal_name = col_name
                for key, val in STATE.column_mapping.items():
                    if val == col_name:
                        internal_name = key
                        break
                
                if internal_name in row:
                    val = row[internal_name]
                    if internal_name == 'Date' and hasattr(val, 'strftime'):
                        try:
                            values.append(val.strftime(date_format_str))
                        except:
                            values.append(val.strftime('%Y-%m-%d'))
                    elif isinstance(val, (float, int)) and internal_name != 'Date':
                        values.append(f"{val:,.2f}")
                    else:
                        values.append(val)
                else:
                    values.append("")
            tree.insert("", "end", values=values)

    def update_sku_dropdowns(self, forecasted_skus=None):
        # update all sku dropdown menus
        # if forecasted_skus is provided use that for chart dashboard filters
        
        # scenario dropdown always shows all skus
        if STATE.sku_list:
            self.app.scenario_sku_combo["values"] = STATE.sku_list
            if not self.app.scenario_sku_var.get():
                self.app.scenario_sku_var.set(STATE.sku_list[0])
        else:
            self.app.scenario_sku_combo["values"] = []
            self.app.scenario_sku_var.set("")
            
        # determine list for chart and dashboard
        filter_list = forecasted_skus if forecasted_skus is not None else STATE.sku_list
        if not filter_list:
            filter_list = []
            
        sku_list_with_all = ["All SKUs"] + sorted(filter_list)
        
        self.app.chart_sku_combo["values"] = sku_list_with_all
        self.app.chart_sku_var.set("All SKUs")
        
        self.app.dash_sku_combo["values"] = sku_list_with_all
        self.app.dash_sku_var.set("All SKUs")
    
    def update_seasonality_display(self):
        # update seasonality info text
        if not STATE.seasonality_info:
            self.app.seasonality_var.set("No data analyzed")
            return
        
        info = STATE.seasonality_info
        lines = []
        
        if info.get('has_monthly_seasonality'):
            lines.append(f"Monthly: Seasonal (CV={info.get('monthly_cv', 0):.2f})")
        else:
            lines.append("Monthly: Stable")
        
        if info.get('has_weekly_seasonality'):
            lines.append(f"Weekly: Seasonal (CV={info.get('weekly_cv', 0):.2f})")
        else:
            lines.append("Weekly: Stable")
        
        self.app.seasonality_var.set("\n".join(lines))
    
    def remove_data(self):
        # clear all loaded data
        clear_all_data()
        
        self.app.preview_info_var.set("Load a file to see data preview")
        
        # also clear activity cards
        for widget in self.app.activity_card_frame.winfo_children():
            widget.destroy()

        self.app.chart_frame.clear()
        
        # reset sku dropdowns to original state
        self.update_sku_dropdowns()
        
        self.app.data_info_var.set("No data loaded")
        self.app.seasonality_var.set("No data analyzed")
        
        for key in self.app.stat_labels:
            self.app.stat_labels[key].configure(text="--", style="Neutral.TLabel")
        
        self.app.set_status("Data removed", is_success=True)
    
    def remove_model(self):
        # clear loaded model state and update ui
        STATE.clear_model_state()
        self.app.model_info_var.set("No model loaded")
        self.app.remove_model_btn.pack_forget()
        self.app.set_status("Loaded model removed.", is_success=True)

    def remap_columns(self):
        # reopen column mapping dialog
        if STATE.raw_data is None:
            self.app.set_status("No data loaded", is_error=True)
            return
        
        from ui.dialogs import ColumnMapperDialog
        dialog = ColumnMapperDialog(self.app.root, STATE.raw_data)
        self.app.root.wait_window(dialog.dialog)
        
        if dialog.result_df is not None:
            self.process_loaded_data(dialog.result_df, "Remapped", "Remapped")
    
    # ================ FORECAST ================
    
    def run_forecast(self):
        # run or cancel forecast auto-uses loaded model if available
        if STATE.is_forecasting:
            STATE.request_cancel()
            self.app.set_status("Cancelling forecast...")
            return
        
        if STATE.clean_data is None:
            self.app.set_status("Load data first", is_error=True)
            return

        valid, msg = validate_forecast_requirements()
        if not valid:
            self.app.set_status(f"Error: {msg}", is_error=True)
            return
        
        # update state from ui
        STATE.forecast_days = self.app.days_var.get()
        STATE.forecast_granularity = self.app.granularity_var.get()
        STATE.forecast_speed = self.app.speed_var.get()
        STATE.chart_grouping = self.app.granularity_var.get()
        
        # reset state
        STATE.reset_forecast_state()
        STATE.is_forecasting = True
        STATE.reset_cancel_flag()
        
        # update ui
        self.app.forecast_btn.configure(text="Cancel")
        self.app.remove_model_btn.configure(state="disabled")
        self.app.load_model_btn.configure(state="disabled")
        self.app.show_progress(True)
        self.start_timer()
        
        # auto-use loaded model if available single or parallel
        has_single_model = STATE.loaded_model is not None
        has_parallel_models = STATE.has_loaded_models and len(STATE.saved_models) > 0
        
        print(f"run_forecast: has_single_model={has_single_model}, has_parallel_models={has_parallel_models}")
        
        if has_single_model:
            self.app.set_status("Forecasting with loaded single model...")
            threading.Thread(target=self._use_single_model_thread, daemon=True).start()
        elif has_parallel_models:
            self.app.set_status("Forecasting with loaded parallel models...")
            threading.Thread(target=self._use_parallel_models_thread, daemon=True).start()
        else:
            self.app.set_status("Forecasting... please wait")
            threading.Thread(target=self._forecast_thread, daemon=True).start()

    def _forecast_thread(self):
        # forecast thread wrapper
        def on_complete(success, message, chart_path):
            self.app.root.after(0, lambda: self._on_forecast_complete(success, message, chart_path))
        
        run_forecast_thread(on_complete)
        
    def _use_single_model_thread(self):
        # use single model forecast thread wrapper
        def on_complete(success, message, chart_path):
            self.app.root.after(0, lambda: self._on_forecast_complete(success, message, chart_path))
        
        forecast_with_loaded_model(on_complete)
    
    def _use_parallel_models_thread(self):
        # use parallel models forecast thread wrapper
        def on_complete(success, message, chart_path):
            self.app.root.after(0, lambda: self._on_forecast_complete(success, message, chart_path))
        
        forecast_with_parallel_models(on_complete)
    
    def _on_forecast_complete(self, success, message, chart_path):
        # handle forecast completion on main ui thread
        elapsed = self.stop_timer()
        minutes, seconds = divmod(int(elapsed), 60)
        time_str = f"({minutes}m {seconds}s)" if minutes > 0 else f"({seconds}s)"
        
        # update timer label permanently
        self.app.timer_var.set(f"Finished in {minutes}m {seconds}s" if minutes > 0 else f"Finished in {seconds}s")
        
        self.app.forecast_btn.configure(text="Run Forecast")
        self.app.remove_model_btn.configure(state="normal")
        self.app.load_model_btn.configure(state="normal")
        self.app.show_progress(False)
        STATE.is_forecasting = False
        
        if success:
            self.app.set_status(f"{message} {time_str}", is_success=True)
            
            # update sku dropdowns with only forecasted skus
            if STATE.forecast_data is not None:
                forecasted_skus = STATE.forecast_data.columns.tolist()
                self.update_sku_dropdowns(forecasted_skus)
            
            # schedule ui updates to avoid blocking
            self.app.root.after(10, self.refresh_chart)
            self.app.root.after(20, self.refresh_dashboard)
            self.app.root.after(30, lambda: self.app.right_notebook.select(2))
        else:
            self.app.set_status(message, is_error=True)
            self.app.chart_frame.clear()
            # on failure reset dropdowns to all skus
            self.update_sku_dropdowns()
            
    def start_timer(self):
        self.timer_running = True
        self.timer_start = time.time()
        self._update_timer()
    
    def _update_timer(self):
        if self.timer_running:
            elapsed = time.time() - self.timer_start
            minutes, seconds = divmod(int(elapsed), 60)
            self.app.timer_var.set(f"Elapsed: {minutes:02d}:{seconds:02d}")
            self.app.root.after(100, self._update_timer)
    
    def stop_timer(self):
        elapsed = time.time() - self.timer_start if self.timer_start else 0
        self.timer_running = False
        self.timer_start = None
        return elapsed
    
    # ================ MODEL ================
    
    def load_model(self):
        file_path = filedialog.askopenfilename(
            title="Load Model",
            filetypes=[("Model files", "*.pkl"), ("All files", "*.*")]
        )
        if file_path:
            success, message = load_saved_model(file_path)
            if success:
                self.app.model_info_var.set(f"Loaded: {Path(file_path).name}")
                self.app.remove_model_btn.pack(side=tk.LEFT, padx=(0, 5))
                self.app.set_status(message, is_success=True)
            else:
                self.app.set_status(message, is_error=True)
    
    def export_model(self):
        model_to_save = None
        
        # check last trained model first
        if hasattr(STATE, 'last_trained_model') and STATE.last_trained_model:
            model_to_save = STATE.last_trained_model
        elif STATE.saved_models and not STATE.has_loaded_models:
            # only save trained models not loaded ones
            model_to_save = {'sku_models': STATE.saved_models}
            
        if model_to_save is None:
            self.app.set_status("No model to export.", is_error=True)
            return
        
        try:
            output_dir = get_output_directory()
            timestamp = datetime.now().strftime(ExportConfig.TIMESTAMP_FORMAT)
            model_path = output_dir / f"model_{timestamp}.pkl"
            with open(model_path, 'wb') as f:
                pickle.dump(model_to_save, f)
            self.app.set_status(f"Model saved: {model_path.name}", is_success=True)
        except Exception as e:
            self.app.set_status(f"Export error: {e}", is_error=True)
    
    # ================ EXPORT ================
    
    def export_results(self):
        if STATE.forecast_data is None:
            self.app.set_status("No forecast to export", is_error=True)
            return
        timestamp = datetime.now().strftime(ExportConfig.TIMESTAMP_FORMAT)
        success, message = export_results(timestamp)
        self.app.set_status(message, is_success=success, is_error=not success)
    
    # ================ CHART ================
    
    def refresh_chart(self):
        if STATE.forecast_data is None:
            return
        try:
            # use granularity from forecast settings
            grouping = self.app.granularity_var.get()
            sku_filter = self.app.chart_sku_var.get()
            df_pivot = prepare_for_autots(STATE.clean_data, use_features=False).set_index('Date')
            
            chart_path = generate_forecast_chart(
                df_pivot, STATE.forecast_data, STATE.upper_forecast, STATE.lower_forecast,
                grouping, sku_filter if sku_filter != "All SKUs" else None
            )
            if chart_path:
                self.app.chart_frame.load_image(str(chart_path))
        except Exception as e:
            self.app.set_status(f"Chart error: {e}", is_error=True)
            traceback.print_exc()
    
    def on_chart_sku_changed(self, event=None):
        self.app.root.focus_set()
        self.refresh_chart()
    
    def show_summary(self):
        if STATE.forecast_data is None:
            self.app.set_status("Run forecast first", is_error=True)
            return
        try:
            grouping = self.app.granularity_var.get()
            chart_path = generate_sku_summary_chart(STATE.forecast_data, grouping)
            if chart_path:
                if sys.platform == 'win32': os.startfile(str(chart_path))
                elif sys.platform == 'darwin': os.system(f'open "{chart_path}"')
                else: os.system(f'xdg-open "{chart_path}"')
        except Exception as e:
            self.app.set_status(f"Summary error: {e}", is_error=True)
    
    def zoom_chart(self):
        chart_path = get_output_directory() / "forecast.png"
        if chart_path.exists():
            try:
                if sys.platform == 'win32': os.startfile(str(chart_path))
                elif sys.platform == 'darwin': os.system(f'open "{chart_path}"')
                else: os.system(f'xdg-open "{chart_path}"')
                self.app.set_status("Chart opened", is_success=True)
            except Exception as e:
                self.app.set_status(f"Could not open chart: {e}", is_error=True)
        else:
            self.app.set_status("No chart found.", is_error=True)
    
    # ================ DASHBOARD ================
    
    def refresh_dashboard(self):
        if STATE.forecast_data is None: return
        try:
            # use granularity from forecast settings
            grouping = self.app.granularity_var.get()
            sku_filter = self.app.dash_sku_var.get()
            
            data = calculate_dashboard_data(grouping)
            if data is None: return
            
            fg = data['forecast_grouped'].copy()
            ug = data['upper_grouped'].copy()
            lg = data['lower_grouped'].copy()
            
            fg_stats = fg.copy()
            ug_stats = ug.copy()
            lg_stats = lg.copy()

            if sku_filter and sku_filter != "All SKUs" and sku_filter in fg.columns:
                fg_stats = fg[[sku_filter]]
                ug_stats = ug[[sku_filter]]
                lg_stats = lg[[sku_filter]]
            
            total_f = fg_stats.sum().sum()
            total_u = ug_stats.sum().sum()
            total_l = lg_stats.sum().sum()
            
            avg_err = 0
            if total_f > 0:
                avg_err = ((total_u - total_l) / total_f) * 100 
            
            avg_daily = STATE.forecast_data.mean().mean()
            
            self.app.stat_labels["total"].configure(text=f"{total_f:,.2f}")
            self.app.stat_labels["avg"].configure(text=f"{avg_daily:,.2f}")
            self.app.stat_labels["skus"].configure(text=str(len(fg.columns)))
            self.app.stat_labels["date_range"].configure(text=f"{fg.index.min():%d %b %Y} - {fg.index.max():%d %b %Y}")
            self.app.stat_labels["confidence"].configure(text=f"{total_l:,.2f} - {total_u:,.2f}")
            
            # update forecast activity card
            self.update_activity_cards(fg_stats, ug_stats, lg_stats)
            
        except Exception as e:
            self.app.set_status(f"Dashboard error: {e}", is_error=True)
            traceback.print_exc()

    def update_activity_cards(self, forecast_df, upper_df, lower_df):
        # create full-width vertical cards one per row
        for widget in self.app.activity_card_frame.winfo_children():
            widget.destroy()

        if forecast_df.empty: 
            ttk.Label(self.app.activity_card_frame, text="No forecast activity found.", 
                     foreground="gray", font=("", 10)).pack(pady=20)
            return
        
        non_zero = forecast_df[forecast_df > 0].stack().reset_index()
        non_zero.columns = ['Period', 'SKU', 'Value']
        
        if non_zero.empty:
            ttk.Label(self.app.activity_card_frame, text="No forecast activity found.", 
                     foreground="gray", font=("", 10)).pack(pady=20)
            return
        
        # add upper and lower values
        upper_stacked = upper_df.stack().reset_index()
        upper_stacked.columns = ['Period', 'SKU', 'Upper']
        lower_stacked = lower_df.stack().reset_index()
        lower_stacked.columns = ['Period', 'SKU', 'Lower']
        
        non_zero = non_zero.merge(upper_stacked, on=['Period', 'SKU'], how='left')
        non_zero = non_zero.merge(lower_stacked, on=['Period', 'SKU'], how='left')
        
        date_format = DisplayConfig.DATE_FORMAT
        
        # display up to 30 cards one per row full width
        for idx, row in enumerate(non_zero.head(30).itertuples()):
            card = ttk.Frame(self.app.activity_card_frame, style="ActivityCard.TFrame")
            card.pack(fill=tk.X, pady=4, padx=2, ipady=12)
            
            # left side date and sku
            left_frame = ttk.Frame(card)
            left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(15, 0))
            
            ttk.Label(left_frame, text=row.Period.strftime(date_format), 
                     font=("", 12, "bold")).pack(anchor=tk.W)
            ttk.Label(left_frame, text=row.SKU, foreground="gray", 
                     font=("", 10)).pack(anchor=tk.W)
            
            # right side values
            right_frame = ttk.Frame(card)
            right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 15))
            
            # forecast value
            value_text = f"{row.Value:,.2f}"
            if row.Value >= 1000000:
                value_text = f"{row.Value/1000000:.2f}M"
            elif row.Value >= 1000:
                value_text = f"{row.Value/1000:.2f}K"
            
            ttk.Label(right_frame, text=value_text, 
                     font=("", 20, "bold")).pack(anchor=tk.E)
            
            # error margin
            error = (row.Upper - row.Lower) / 2 if hasattr(row, 'Upper') and hasattr(row, 'Lower') else 0
            if error > 0:
                percent = (error * 2 / row.Value * 100) if row.Value > 0 else 0
                err_text = f"±{error:,.0f} ({percent:.0f}%)"
                if error >= 1000000:
                    err_text = f"±{error/1000000:.1f}M ({percent:.0f}%)"
                elif error >= 1000:
                    err_text = f"±{error/1000:.1f}K ({percent:.0f}%)"
                ttk.Label(right_frame, text=err_text, foreground="gray", 
                         font=("", 10)).pack(anchor=tk.E)
            
    def on_dash_sku_changed(self, event=None):
        self.app.root.focus_set()
        self.refresh_dashboard()
    
    def show_seasonality(self):
        if not STATE.seasonality_info:
            self.app.set_status("No seasonality data", is_error=True)
            return
        try:
            chart_path = generate_seasonality_chart(STATE.seasonality_info)
            if chart_path and os.path.exists(chart_path):
                if sys.platform == 'win32': os.startfile(str(chart_path))
                elif sys.platform == 'darwin': os.system(f'open "{chart_path}"')
                else: os.system(f'xdg-open "{chart_path}"')
        except Exception as e:
            self.app.set_status(f"Seasonality chart error: {e}", is_error=True)
    
    def show_diagnostics(self):
        from ui.dialogs import DiagnosticsDialog
        DiagnosticsDialog(self.app.root)
    
    # ================ SCENARIOS ================
    
    def on_scenario_type_changed(self, event=None):
        self.app.root.focus_set()
        if self.app.scenario_type_var.get() == "Demand Spike":
            self.delay_frame.pack_forget()
            self.app.multiplier_frame.pack(fill=tk.X)
        else:
            self.app.multiplier_frame.pack_forget()
            self.delay_frame.pack(fill=tk.X)
    
    def update_multiplier_label(self, value):
        self.app.multiplier_label.configure(text=f"{float(value):.1f}x")
    
    def update_delay_label(self, value):
        self.app.delay_label.configure(text=f"{int(float(value))} days")
    
    def set_date_week(self):
        today, start = datetime.now(), datetime.now() - timedelta(days=datetime.now().weekday())
        self.app.start_date_var.set(start.strftime("%Y-%m-%d"))
        self.app.end_date_var.set((start + timedelta(days=6)).strftime("%Y-%m-%d"))
    
    def set_date_month(self):
        today, start = datetime.now(), datetime.now().replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        self.app.start_date_var.set(start.strftime("%Y-%m-%d"))
        self.app.end_date_var.set(today.replace(day=last_day).strftime("%Y-%m-%d"))
    
    def set_date_next(self):
        today = datetime.now()
        start = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        last_day = calendar.monthrange(start.year, start.month)[1]
        self.app.start_date_var.set(start.strftime("%Y-%m-%d"))
        self.app.end_date_var.set(start.replace(day=last_day).strftime("%Y-%m-%d"))
    
    def apply_scenario(self):
        if STATE.forecast_data is None:
            self.app.set_status("Run forecast first", is_error=True)
            return
        sku = self.app.scenario_sku_var.get()
        if not sku:
            self.app.set_status("Select a SKU", is_error=True)
            return
        
        try:
            try:
                start_date = pd.to_datetime(self.app.start_date_var.get())
                end_date = pd.to_datetime(self.app.end_date_var.get())
            except (ValueError, pd.errors.ParserError):
                self.app.set_status("Invalid date format. Use YYYY-MM-DD", is_error=True)
                return

            if start_date > end_date:
                self.app.set_status("Start date must be before end date", is_error=True)
                return
            
            if not STATE.scenario_history:
                STATE.original_forecast = STATE.forecast_data.copy()
                STATE.original_upper = STATE.upper_forecast.copy() if STATE.upper_forecast is not None else None
                STATE.original_lower = STATE.lower_forecast.copy() if STATE.lower_forecast is not None else None
            
            scenario_type = self.app.scenario_type_var.get()
            if scenario_type == "Demand Spike":
                multiplier = self.app.multiplier_var.get()
                mask = (
                    (STATE.forecast_data.index >= start_date) &
                    (STATE.forecast_data.index <= end_date)
                )
                if sku in STATE.forecast_data.columns:
                    STATE.forecast_data.loc[mask, sku] *= multiplier
                    if STATE.upper_forecast is not None: STATE.upper_forecast.loc[mask, sku] *= multiplier
                    if STATE.lower_forecast is not None: STATE.lower_forecast.loc[mask, sku] *= multiplier
                STATE.scenario_history.append({'type': 'Demand Spike', 'sku': sku, 'multiplier': multiplier})
            else:
                delay_days = int(self.app.delay_var.get())
                if sku in STATE.forecast_data.columns:
                    STATE.forecast_data[sku] = STATE.forecast_data[sku].shift(delay_days, fill_value=0)
                    if STATE.upper_forecast is not None: STATE.upper_forecast[sku] = STATE.upper_forecast[sku].shift(delay_days, fill_value=0)
                    if STATE.lower_forecast is not None: STATE.lower_forecast[sku] = STATE.lower_forecast[sku].shift(delay_days, fill_value=0)
                STATE.scenario_history.append({'type': 'Supply Delay', 'sku': sku, 'delay_days': delay_days})
            
            self.refresh_chart()
            self.refresh_dashboard()
            self.app.set_status(f"Applied {scenario_type} to {sku}", is_success=True)
        except Exception as e:
            self.app.set_status(f"Scenario error: {e}", is_error=True)
            traceback.print_exc()
    
    def reset_scenarios(self):
        if not STATE.scenario_history: return
        if STATE.original_forecast is None:
            self.app.set_status("No original data stored", is_error=True)
            return
        
        STATE.forecast_data = STATE.original_forecast.copy()
        if STATE.original_upper is not None: STATE.upper_forecast = STATE.original_upper.copy()
        if STATE.original_lower is not None: STATE.lower_forecast = STATE.original_lower.copy()
        STATE.scenario_history = []
        
        self.refresh_chart()
        self.refresh_dashboard()
        self.app.set_status("All scenarios reset", is_success=True)