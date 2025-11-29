"""
application callbacks
ui event handling logic
"""


# ================ IMPORTS ================

import dearpygui.dearpygui as dpg
import pandas as pd
import threading
import time
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import calendar
import json
import os
import pickle
import gc
import sys

from config import Paths, GUIConfig, DataConfig, AutoTSConfig, ScenarioConfig, ExportConfig, LargeDataConfig
from core.state import STATE
from core.data_operations import (
    clear_all_data,
    validate_forecast_requirements,
    export_results,
    calculate_dashboard_data,
    get_output_directory
)
from core.forecasting import run_forecast_thread, load_saved_model, forecast_with_loaded_model
from core.charting import generate_forecast_chart, generate_sku_summary_chart, generate_seasonality_chart

from utils.preprocessing import (
    validate_columns,
    validate_data_types,
    clean_dataframe,
    get_sku_list,
    apply_demand_spike, 
    apply_supply_delay,
    prepare_for_autots
)
from utils.features import (
    detect_additional_columns,
    detect_seasonality_pattern
)
import ui.column_mapper as mapper


# ================ TIMER STATE ================

TIMER_STATE = {
    'running': False,
    'start_time': None,
    'thread': None
}


# ================ HELPER FUNCTIONS ================

def force_gc():
    """
    force garbage collection
    """
    gc.collect()
    gc.collect()


# ================ SAFE UI HELPERS ================

def safe_set_value(tag, value):
    """
    set value of item if it exists
    """
    if dpg.does_item_exist(tag):
        dpg.set_value(tag, value)

def safe_configure_item(tag, **kwargs):
    """
    configure item if it exists
    """
    if dpg.does_item_exist(tag):
        dpg.configure_item(tag, **kwargs)

def safe_delete_item(tag):
    """
    delete item if it exists
    """
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)

def safe_set_label(tag, label):
    """
    set label of item if it exists
    """
    if dpg.does_item_exist(tag):
        dpg.set_item_label(tag, label)

def safe_bind_theme(item_tag, theme_tag):
    """
    bind theme to item if both exist
    """
    if dpg.does_item_exist(item_tag) and dpg.does_item_exist(theme_tag):
        dpg.bind_item_theme(item_tag, theme_tag)


# ================ UI UPDATE CALLBACKS ================

def update_status(message, error=False, success=False, warning=False):
    color = GUIConfig.ERROR_COLOR if error else (GUIConfig.SUCCESS_COLOR if success else (GUIConfig.WARNING_COLOR if warning else GUIConfig.STATUS_COLOR))
    safe_set_value("status_text", message)
    safe_configure_item("status_text", color=color)


def update_data_info(records, skus, mapping_info=""):
    info_text = f"Records: {records}  |  SKUs: {skus}"
    safe_set_value("data_info_text", info_text)
    safe_set_value("column_mapping_text", mapping_info)


def update_sku_dropdown():
    if STATE.sku_list:
        sku_list_with_all = ["All SKUs"] + STATE.sku_list
        safe_configure_item("scenario_sku", items=STATE.sku_list, default_value=STATE.sku_list[0])
        safe_configure_item("chart_sku_combo", items=sku_list_with_all, default_value="All SKUs")
        safe_configure_item("dashboard_sku_combo", items=sku_list_with_all, default_value="All SKUs")


def update_data_preview():
    """
    update data preview table
    show only chosen columns with original names and formats
    """
    safe_delete_item("preview_table")
    
    if dpg.does_item_exist("preview_group"):
        for child in dpg.get_item_children("preview_group", 1):
            if dpg.get_item_type(child) == "mvAppItemType::mvText":
                safe_delete_item(child)
    
    if STATE.raw_data is not None and hasattr(STATE, 'column_mapping') and STATE.column_mapping and dpg.does_item_exist("preview_group"):
        # get original column names from mapping
        display_columns = []
        
        # add mapped required columns
        if 'Date' in STATE.column_mapping:
            display_columns.append(STATE.column_mapping['Date'])
        if 'SKU' in STATE.column_mapping:
            display_columns.append(STATE.column_mapping['SKU'])
        if 'Quantity' in STATE.column_mapping:
            display_columns.append(STATE.column_mapping['Quantity'])
        
        # add selected additional columns
        if STATE.additional_columns:
            for col in STATE.additional_columns:
                if col not in display_columns and col in STATE.raw_data.columns:
                    display_columns.append(col)
        
        # filter to existing columns
        display_columns = [col for col in display_columns if col in STATE.raw_data.columns]
        
        # get preview data from raw data
        preview = STATE.raw_data[display_columns].head(DataConfig.PREVIEW_ROWS)
        
        with dpg.table(header_row=True, parent="preview_group", tag="preview_table", 
                       resizable=True, policy=dpg.mvTable_SizingStretchProp,
                       scrollX=True, scrollY=True):
            
            for col in preview.columns:
                dpg.add_table_column(label=str(col), width_stretch=True)
            
            for _, row in preview.iterrows():
                with dpg.table_row():
                    for val in row:
                        dpg.add_text(str(val))
    
    elif STATE.clean_data is not None and dpg.does_item_exist("preview_group"):
        # fallback: show clean data with standard names
        display_columns = ['Date', 'SKU', 'Quantity']
        
        if STATE.additional_columns:
            for col in STATE.additional_columns:
                if col in STATE.clean_data.columns and col not in display_columns:
                    display_columns.append(col)
        
        display_columns = [col for col in display_columns if col in STATE.clean_data.columns]
        preview = STATE.clean_data[display_columns].head(DataConfig.PREVIEW_ROWS)
        
        with dpg.table(header_row=True, parent="preview_group", tag="preview_table", 
                       resizable=True, policy=dpg.mvTable_SizingStretchProp,
                       scrollX=True, scrollY=True):
            
            for col in preview.columns:
                dpg.add_table_column(label=str(col), width_stretch=True)
            
            for _, row in preview.iterrows():
                with dpg.table_row():
                    for val in row:
                        dpg.add_text(str(val))


def safe_load_and_display_image(chart_path, parent_tag, image_tag, texture_tag):
    """
    safely load and display image with error handling
    properly manages texture memory
    """
    try:
        # cleanup old items
        safe_delete_item(image_tag)
        safe_delete_item(texture_tag)
        
        if not chart_path or not os.path.exists(chart_path) or not dpg.does_item_exist(parent_tag):
            return False
        
        file_size = os.path.getsize(chart_path)
        if file_size > 50 * 1024 * 1024:
            print(f"chart file too large: {file_size} bytes")
            return False
        
        width, height, channels, data = dpg.load_image(str(chart_path))
        
        if not data:
            print("failed to load image data")
            return False
        
        max_pixels = 20_000_000
        total_pixels = width * height
        
        if total_pixels > max_pixels:
            print(f"image too large: {width}x{height} = {total_pixels} pixels")
            return False
        
        # create texture registry once
        if not dpg.does_item_exist("main_texture_registry"):
            dpg.add_texture_registry(tag="main_texture_registry", show=False)
            
        # add texture and image
        dpg.add_static_texture(
            width=width, height=height, default_value=data,
            tag=texture_tag, parent="main_texture_registry"
        )
        
        dpg.add_image(texture_tag, parent=parent_tag, tag=image_tag)
        
        del data
        force_gc()
        return True
        
    except Exception as e:
        print(f"image load error: {e}")
        return False


def update_forecast_display(chart_path):
    if dpg.does_item_exist("chart_image_group"):
        for child in dpg.get_item_children("chart_image_group", 1):
            if dpg.get_item_type(child) in ["mvAppItemType::mvText", "mvAppItemType::mvButton"]:
                safe_delete_item(child)

    success = safe_load_and_display_image(
        chart_path, 
        "chart_image_group", 
        "forecast_image", 
        "forecast_texture"
    )
    
    if not success and chart_path and dpg.does_item_exist("chart_image_group"):
        dpg.add_text("Chart saved (too large for display).", 
                    parent="chart_image_group", color=(255, 200, 100))
        
        def open_folder():
            import subprocess
            folder = os.path.dirname(chart_path)
            if os.name == 'nt':
                subprocess.run(['explorer', folder])
            elif os.name == 'posix':
                subprocess.run(['xdg-open', folder])
        
        dpg.add_button(label="Open Folder", callback=lambda: open_folder(), 
                      parent="chart_image_group")


def clear_ui_data():
    safe_delete_item("preview_table")
    safe_delete_item("forecast_image")
    safe_delete_item("forecast_texture")
    safe_delete_item("summary_image")
    safe_delete_item("summary_texture")
    safe_delete_item("seasonality_image")
    safe_delete_item("seasonality_texture")
    
    safe_set_value("data_info_text", "No data loaded")
    safe_set_value("column_mapping_text", "")
    
    if dpg.does_item_exist("preview_group"):
        for child in dpg.get_item_children("preview_group", 1):
            safe_delete_item(child)
        dpg.add_text("Load a CSV or Excel file to see data preview.", parent="preview_group", color=(150, 150, 150))
    
    safe_set_value("seasonality_info_text", "No data analyzed")
    force_gc()


def clear_forecast_display():
    """
    clear forecast chart and dashboard before new forecast
    """
    safe_delete_item("forecast_image")
    safe_delete_item("forecast_texture")
    safe_delete_item("summary_image")
    safe_delete_item("summary_texture")
    
    if dpg.does_item_exist("chart_image_group"):
        for child in dpg.get_item_children("chart_image_group", 1):
            safe_delete_item(child)
        dpg.add_text("Running forecast...", parent="chart_image_group", color=(150, 150, 150))
    
    stat_tags = ["stat_total_forecast", "stat_avg_daily", "stat_num_periods", 
                 "stat_num_skus", "stat_date_range", "stat_confidence", "stat_error_pct"]
    for tag in stat_tags:
        safe_set_value(tag, "--")
    
    safe_delete_item("dashboard_table")
    safe_configure_item("summary_container", show=False)
    force_gc()


# ================ SEASONALITY FUNCTIONS ================

def update_seasonality_display():
    """
    update seasonality information display
    """
    if STATE.seasonality_info is None or not STATE.seasonality_info:
        safe_set_value("seasonality_info_text", "No seasonality data")
        return
    
    info = STATE.seasonality_info
    lines = []
    
    if info.get('has_monthly_seasonality'):
        cv = info.get('monthly_cv', 0)
        lines.append(f"Monthly: Seasonal (CV={cv:.2f})")
    else:
        lines.append("Monthly: Stable")
    
    if info.get('has_weekly_seasonality'):
        cv = info.get('weekly_cv', 0)
        lines.append(f"Weekly: Seasonal (CV={cv:.2f})")
    else:
        lines.append("Weekly: Stable")
    
    safe_set_value("seasonality_info_text", "\n".join(lines))


def show_seasonality_chart_callback():
    """
    generate and show seasonality chart
    """
    if STATE.seasonality_info is None or not STATE.seasonality_info:
        return update_status("No seasonality data", warning=True)
    
    try:
        chart_path = generate_seasonality_chart(STATE.seasonality_info)
        
        if chart_path and os.path.exists(chart_path):
            safe_configure_item("seasonality_chart_container", show=True)
            
            success = safe_load_and_display_image(
                chart_path, "seasonality_chart_group", "seasonality_image", "seasonality_texture"
            )
            
            if success:
                update_status("Seasonality chart generated", success=True)
            else:
                update_status("Chart saved to file", warning=True)
        else:
            update_status("Failed to generate chart", error=True)
            
    except Exception as e:
        print(f"seasonality chart error: {e}")
        update_status(f"Chart error: {e}", error=True)


def hide_seasonality_chart():
    safe_configure_item("seasonality_chart_container", show=False)
    safe_delete_item("seasonality_image")
    safe_delete_item("seasonality_texture")


# ================ TIMER FUNCTIONS ================

def start_forecast_timer():
    TIMER_STATE['running'] = True
    TIMER_STATE['start_time'] = time.time()
    
    def timer_loop():
        while TIMER_STATE['running']:
            elapsed = time.time() - TIMER_STATE['start_time']
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            
            try:
                safe_set_label("forecast_btn", f"Cancel ({minutes:02d}:{seconds:02d})")
            except:
                pass
            
            time.sleep(0.1)
    
    TIMER_STATE['thread'] = threading.Thread(target=timer_loop, daemon=True)
    TIMER_STATE['thread'].start()


def stop_forecast_timer():
    """
    stop timer and return elapsed time
    """
    elapsed = 0
    if TIMER_STATE['start_time'] is not None:
        elapsed = time.time() - TIMER_STATE['start_time']
    
    TIMER_STATE['running'] = False
    TIMER_STATE['start_time'] = None
    
    try:
        safe_set_label("forecast_btn", "Run Forecast")
        safe_bind_theme("forecast_btn", "forecast_button_theme")
    except:
        pass
    
    return elapsed


# ================ FILE LOADING ================

def detect_file_type(file_path):
    ext = Path(file_path).suffix.lower()
    if ext == '.csv':
        return 'csv'
    elif ext in ['.xlsx', '.xls']:
        return 'excel'
    else:
        return 'unknown'


def load_file(file_path):
    try:
        file_type = detect_file_type(file_path)
        
        if file_type == 'csv':
            df = pd.read_csv(file_path)
            file_info = "CSV"
            
        elif file_type == 'excel':
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            
            if len(sheet_names) > 1:
                show_sheet_selection_dialog(file_path, sheet_names)
                return
            else:
                df = pd.read_excel(file_path, sheet_name=0)
                file_info = "Excel"
        else:
            update_status(f"Unsupported file type: {Path(file_path).suffix}", error=True)
            return
        
        if all(col in df.columns for col in ['Date', 'SKU', 'Quantity']):
            mapper.TEMP_DATA.additional_columns = []
            mapper.TEMP_DATA.original_data = df.copy()
            process_loaded_data(df, file_path, f"{file_info} - Standard")
        else:
            mapper.TEMP_DATA.pending_df = df
            mapper.TEMP_DATA.original_data = df.copy()
            mapper.TEMP_DATA.pending_path = file_path
            mapper.show_column_mapping_dialog(df, mapper.suggest_column_mapping(df.columns))
            
    except ImportError as e:
        if 'openpyxl' in str(e):
            update_status("Install openpyxl: pip install openpyxl", error=True)
        elif 'xlrd' in str(e):
            update_status("Install xlrd: pip install xlrd", error=True)
        else:
            update_status(f"Missing library: {e}", error=True)
    except Exception as e:
        update_status(f"Error loading file: {e}", error=True)


def load_excel_sheet(file_path, sheet_name):
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        
        safe_configure_item("sheet_dialog", show=False)
        
        if all(col in df.columns for col in ['Date', 'SKU', 'Quantity']):
            mapper.TEMP_DATA.additional_columns = []
            mapper.TEMP_DATA.original_data = df.copy()
            process_loaded_data(df, file_path, f"Excel ({sheet_name})")
        else:
            mapper.TEMP_DATA.pending_df = df
            mapper.TEMP_DATA.original_data = df.copy()
            mapper.TEMP_DATA.pending_path = file_path
            mapper.show_column_mapping_dialog(df, mapper.suggest_column_mapping(df.columns))
            
    except Exception as e:
        update_status(f"Error loading sheet: {e}", error=True)


def show_sheet_selection_dialog(file_path, sheet_names):
    mapper.TEMP_DATA.pending_path = file_path
    
    safe_delete_item("sheet_dialog")
    
    with dpg.window(label="Select Sheet", tag="sheet_dialog", modal=True,
                   width=350, height=200, pos=[525, 300], no_resize=True):
        
        dpg.add_text("EXCEL SHEET SELECTION", color=GUIConfig.HEADER_COLOR)
        dpg.add_separator()
        dpg.add_spacer(height=10)
        
        dpg.add_text("This file has multiple sheets.", color=(200, 200, 200))
        dpg.add_text("Select which sheet to load:", color=(200, 200, 200))
        
        dpg.add_spacer(height=10)
        
        dpg.add_combo(sheet_names, default_value=sheet_names[0], 
                     tag="sheet_combo", width=-1)
        
        dpg.add_spacer(height=15)
        
        with dpg.group(horizontal=True):
            load_btn = dpg.add_button(label="Load Sheet", width=100, height=30,
                                      callback=lambda: load_excel_sheet(
                                          mapper.TEMP_DATA.pending_path,
                                          dpg.get_value("sheet_combo")
                                      ))
            safe_bind_theme(load_btn, "forecast_button_theme")
            
            dpg.add_spacer(width=10)
            
            cancel_btn = dpg.add_button(label="Cancel", width=80, height=30,
                                        callback=lambda: safe_configure_item("sheet_dialog", show=False))
            safe_bind_theme(cancel_btn, "danger_button_theme")


# ================ DATA CALLBACKS ================

def process_loaded_data(df, file_path, mapping_info=""):
    valid, msg = validate_columns(df)
    if not valid:
        return update_status(f"Error: {msg}", error=True)
    valid, msg = validate_data_types(df)
    if not valid:
        return update_status(f"Error: {msg}", error=True)
    
    # store ORIGINAL data before any renaming
    if hasattr(mapper.TEMP_DATA, 'original_data') and mapper.TEMP_DATA.original_data is not None:
        STATE.raw_data = mapper.TEMP_DATA.original_data.copy()
    else:
        STATE.raw_data = df.copy()
    
    STATE.clean_data = clean_dataframe(df, store_format=True)
    STATE.sku_list = get_sku_list(STATE.clean_data)
    
    if hasattr(mapper, 'TEMP_DATA') and mapper.TEMP_DATA.additional_columns:
        STATE.additional_columns = mapper.TEMP_DATA.additional_columns
    else:
        STATE.additional_columns = []
    
    # if no mapping was set (standard columns), create identity mapping
    if not hasattr(STATE, 'column_mapping') or not STATE.column_mapping:
        STATE.column_mapping = {
            'Date': 'Date',
            'SKU': 'SKU',
            'Quantity': 'Quantity'
        }
    
    STATE.seasonality_info = detect_seasonality_pattern(STATE.clean_data)
    update_seasonality_display()
    
    update_sku_dropdown()
    update_data_preview()
    update_data_info(len(STATE.clean_data), len(STATE.sku_list), mapping_info)
    update_status(f"Loaded: {len(STATE.clean_data)} records", success=True)


def load_file_callback(sender, app_data):
    load_file(app_data['file_path_name'])


def load_csv_callback(sender, app_data):
    load_file_callback(sender, app_data)


def upload_callback():
    dpg.show_item("file_dialog")


def cancel_load_callback(sender, app_data):
    pass


def remove_data_callback():
    clear_all_data()
    clear_ui_data()
    STATE.additional_columns = []
    STATE.seasonality_info = {}
    update_status("All data removed", success=True)


def remap_columns_callback():
    """
    reopen column mapper for current data
    """
    if STATE.raw_data is None:
        return update_status("No data loaded", error=True)
    
    import ui.column_mapper as mapper
    
    mapper.TEMP_DATA.pending_df = STATE.raw_data.copy()
    mapper.TEMP_DATA.pending_path = "Current Data"
    
    current_suggestions = mapper.suggest_column_mapping(STATE.raw_data.columns)
    mapper.show_column_mapping_dialog(STATE.raw_data, current_suggestions)
    
    update_status("Remapping columns...", warning=True)


# ================ FORECAST CALLBACKS ================

def forecast_callback():
    if STATE.is_forecasting:
        STATE.request_cancel()
        update_status("Cancelling forecast...", warning=True)
        return
    
    if STATE.clean_data is None:
        return update_status("Load data first", error=True)
    
    valid, msg = validate_forecast_requirements()
    if not valid:
        return update_status(f"Error: {msg}", error=True)
    
    STATE.reset_forecast_state()
    clear_forecast_display()
    
    STATE.is_forecasting = True
    STATE.reset_cancel_flag()
    
    safe_set_label("forecast_btn", "Cancel (00:00)")
    safe_bind_theme("forecast_btn", "danger_button_theme")
    
    start_forecast_timer()
    update_status("Forecasting... please wait")
    
    def on_forecast_complete(success, message, chart_path):
        elapsed = stop_forecast_timer()
        
        # format elapsed time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        if minutes > 0:
            time_str = f"({minutes}m {seconds}s)"
        else:
            time_str = f"({seconds}s)"
        
        dpg.split_frame()
        
        try:
            if success:
                update_forecast_display(chart_path)
                update_dashboard()
                update_seasonality_display()
                message = f"{message} {time_str}"
            else:
                if dpg.does_item_exist("chart_image_group"):
                    for child in dpg.get_item_children("chart_image_group", 1):
                        safe_delete_item(child)
                    dpg.add_text("Run forecast to see chart.", parent="chart_image_group", color=(150, 150, 150))
            
            update_status(message, success=success, error=not success)
        except Exception as e:
            print(f"ui update error: {e}")
            update_status(f"Display error: {e}", error=True)
        
        STATE.is_forecasting = False
        force_gc()
    
    threading.Thread(target=run_forecast_thread, args=(on_forecast_complete,), daemon=True).start()


def forecast_with_model_callback():
    if STATE.loaded_model is None:
        return update_status("Load a model first", error=True)
    
    if STATE.clean_data is None:
        return update_status("Load data first", error=True)
    
    if STATE.is_forecasting:
        STATE.request_cancel()
        update_status("Cancelling forecast...", warning=True)
        return
    
    STATE.reset_forecast_state()
    clear_forecast_display()
    
    STATE.is_forecasting = True
    STATE.reset_cancel_flag()
    
    safe_set_label("forecast_btn", "Cancel (00:00)")
    safe_bind_theme("forecast_btn", "danger_button_theme")
    
    start_forecast_timer()
    update_status("Forecasting with loaded model...")
    
    def on_forecast_complete(success, message, chart_path):
        elapsed = stop_forecast_timer()
        
        # format elapsed time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        if minutes > 0:
            time_str = f"({minutes}m {seconds}s)"
        else:
            time_str = f"({seconds}s)"
        
        dpg.split_frame()
        
        try:
            if success:
                update_forecast_display(chart_path)
                update_dashboard()
                message = f"{message} {time_str}"
            
            update_status(message, success=success, error=not success)
        except Exception as e:
            print(f"ui update error: {e}")
            update_status(f"Display error: {e}", error=True)
        
        STATE.is_forecasting = False
        force_gc()
    
    threading.Thread(target=forecast_with_loaded_model, args=(on_forecast_complete,), daemon=True).start()


def forecast_days_callback(sender, app_data):
    STATE.forecast_days = app_data


def forecast_granularity_callback(sender, app_data):
    STATE.forecast_granularity = app_data


def export_model_callback():
    from core.forecasting import last_model
    
    if last_model is None:
        return update_status("No model to export", error=True)
    
    try:
        output_dir = get_output_directory()
        timestamp = datetime.now().strftime(ExportConfig.TIMESTAMP_FORMAT)
        model_path = output_dir / f"model_{timestamp}.pkl"
        
        with open(model_path, 'wb') as f:
            pickle.dump(last_model, f)
        
        print(f"model exported: {model_path}")
        update_status(f"Model exported: {model_path.name}", success=True)
        
    except Exception as e:
        print(f"model export error: {e}")
        update_status(f"Export error: {e}", error=True)


def load_model_callback():
    dpg.show_item("model_file_dialog")


def load_model_file_callback(sender, app_data):
    file_path = app_data.get('file_path_name', '')
    if file_path:
        success, message = load_saved_model(file_path)
        if success:
            model_name = Path(file_path).name
            safe_set_value("loaded_model_text", f"Loaded: {model_name}")
            safe_configure_item("use_model_btn", show=True)
        update_status(message, success=success, error=not success)


def export_callback():
    if STATE.forecast_data is None:
        return update_status("No forecast to export", error=True)
    
    success, message = export_results(datetime.now().strftime(ExportConfig.TIMESTAMP_FORMAT))
    update_status(message, success=success, error=not success)


# ================ EXPORT DIRECTORY CALLBACKS ================

def select_export_dir_callback():
    dpg.show_item("folder_dialog")


def folder_selected_callback(sender, app_data):
    selected_path = app_data.get('file_path_name', '')
    if selected_path:
        STATE.custom_output_dir = selected_path
        safe_set_value("export_dir_text", str(selected_path))
        update_status("Export directory set", success=True)


def folder_cancel_callback(sender, app_data):
    pass


def reset_export_dir_callback():
    STATE.custom_output_dir = None
    safe_set_value("export_dir_text", str(Paths.USER_OUTPUT))
    update_status("Export directory reset", success=True)


# ================ SCENARIO CALLBACKS ================

def scenario_type_changed_callback(sender, app_data):
    if app_data == "Demand Spike":
        safe_configure_item("spike_multiplier_group", show=True)
        safe_configure_item("delay_days_group", show=False)
    elif app_data == "Supply Delay":
        safe_configure_item("spike_multiplier_group", show=False)
        safe_configure_item("delay_days_group", show=True)


def apply_scenario_callback():
    if STATE.forecast_data is None:
        return update_status("Run forecast first", error=True)
    
    scenario_type = dpg.get_value("scenario_type")
    sku = dpg.get_value("scenario_sku")
    
    if not sku:
        return update_status("Select a SKU", error=True)
    
    try:
        start_date = get_date_from_picker("scenario_start")
        end_date = get_date_from_picker("scenario_end")
        
        if start_date is None or end_date is None:
            return update_status("Set date range", error=True)
        
        if not STATE.scenario_history:
            STATE.original_forecast = STATE.forecast_data.copy()
            STATE.original_upper = STATE.upper_forecast.copy() if STATE.upper_forecast is not None else None
            STATE.original_lower = STATE.lower_forecast.copy() if STATE.lower_forecast is not None else None
        
        if scenario_type == "Demand Spike":
            multiplier = dpg.get_value("spike_multiplier")
            mask = (STATE.forecast_data.index >= pd.Timestamp(start_date)) & \
                   (STATE.forecast_data.index <= pd.Timestamp(end_date))
            
            if sku in STATE.forecast_data.columns:
                STATE.forecast_data.loc[mask, sku] *= multiplier
                if STATE.upper_forecast is not None and sku in STATE.upper_forecast.columns:
                    STATE.upper_forecast.loc[mask, sku] *= multiplier
                if STATE.lower_forecast is not None and sku in STATE.lower_forecast.columns:
                    STATE.lower_forecast.loc[mask, sku] *= multiplier
            
            scenario_info = {'type': 'Demand Spike', 'sku': sku, 'multiplier': multiplier,
                             'start': str(start_date), 'end': str(end_date)}
            
        elif scenario_type == "Supply Delay":
            delay_days = int(dpg.get_value("delay_days"))
            if sku in STATE.forecast_data.columns:
                sku_data = STATE.forecast_data[sku].copy()
                STATE.forecast_data[sku] = sku_data.shift(delay_days, fill_value=0)
                if STATE.upper_forecast is not None and sku in STATE.upper_forecast.columns:
                    STATE.upper_forecast[sku] = STATE.upper_forecast[sku].shift(delay_days, fill_value=0)
                if STATE.lower_forecast is not None and sku in STATE.lower_forecast.columns:
                    STATE.lower_forecast[sku] = STATE.lower_forecast[sku].shift(delay_days, fill_value=0)
            
            scenario_info = {'type': 'Supply Delay', 'sku': sku, 'delay_days': delay_days,
                             'start': str(start_date)}
        
        STATE.scenario_history.append(scenario_info)
        regenerate_chart()
        update_dashboard()
        update_status(f"Applied {scenario_type} to {sku}", success=True)
        
    except Exception as e:
        print(f"scenario error: {e}")
        import traceback
        traceback.print_exc()
        update_status(f"Scenario error: {e}", error=True)


def reset_all_scenarios_callback():
    if not STATE.scenario_history:
        return update_status("No scenarios to reset", warning=True)
    
    if not hasattr(STATE, 'original_forecast') or STATE.original_forecast is None:
        return update_status("No original data stored", error=True)
    
    try:
        STATE.forecast_data = STATE.original_forecast.copy()
        if hasattr(STATE, 'original_upper') and STATE.original_upper is not None:
            STATE.upper_forecast = STATE.original_upper.copy()
        if hasattr(STATE, 'original_lower') and STATE.original_lower is not None:
            STATE.lower_forecast = STATE.original_lower.copy()
        
        STATE.scenario_history = []
        regenerate_chart()
        update_dashboard()
        update_status("All scenarios reset", success=True)
        
    except Exception as e:
        print(f"reset error: {e}")
        update_status(f"Reset error: {e}", error=True)


def get_date_from_picker(tag_prefix):
    try:
        date_dict = dpg.get_value(f"{tag_prefix}_date")
        if date_dict:
            year = date_dict.get('year', 0) + 1900
            month = date_dict.get('month', 0) + 1
            day = date_dict.get('month_day', 1)
            return datetime(year, month, day)
    except:
        pass
    return None


def set_date_this_week():
    today = datetime.now()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    set_date_picker("scenario_start", start)
    set_date_picker("scenario_end", end)


def set_date_this_month():
    today = datetime.now()
    start = today.replace(day=1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    end = today.replace(day=last_day)
    set_date_picker("scenario_start", start)
    set_date_picker("scenario_end", end)


def set_date_next_month():
    today = datetime.now()
    if today.month == 12:
        start = datetime(today.year + 1, 1, 1)
    else:
        start = datetime(today.year, today.month + 1, 1)
    
    last_day = calendar.monthrange(start.year, start.month)[1]
    end = start.replace(day=last_day)
    set_date_picker("scenario_start", start)
    set_date_picker("scenario_end", end)


def set_date_picker(tag_prefix, date_value):
    try:
        date_dict = {
            'year': date_value.year - 1900,
            'month': date_value.month - 1,
            'month_day': date_value.day
        }
        safe_set_value(f"{tag_prefix}_date", date_dict)
    except Exception as e:
        print(f"date picker error: {e}")


# ================ CHART CALLBACKS ================

def zoom_chart_callback():
    """
    open forecast chart image in default viewer
    """
    output_dir = get_output_directory()
    chart_path = output_dir / "forecast.png"
    
    if chart_path.exists():
        try:
            os.startfile(chart_path)
            update_status("Chart opened in default viewer", success=True)
        except AttributeError:
            # for non-windows systems
            import subprocess
            if sys.platform == "darwin":
                subprocess.run(["open", chart_path])
            else:
                subprocess.run(["xdg-open", chart_path])
            update_status("Chart opened in default viewer", success=True)
        except Exception as e:
            update_status(f"Could not open chart: {e}", error=True)
    else:
        update_status("No chart found, run forecast first", warning=True)


def regenerate_chart():
    if STATE.forecast_data is None:
        return
    
    try:
        grouping = dpg.get_value("chart_grouping_combo")
        sku_filter = dpg.get_value("chart_sku_combo")
        
        # prepare historical data
        df_pivot = prepare_for_autots(STATE.clean_data, use_features=False)
        df_pivot = df_pivot.set_index('Date')
        
        # ensure sku_filter is valid
        if sku_filter and sku_filter != "All SKUs":
            # check if SKU exists in forecast
            if sku_filter not in STATE.forecast_data.columns:
                update_status(f"SKU {sku_filter} not found in forecast", warning=True)
                return
        
        chart_path = generate_forecast_chart(
            df_pivot, 
            STATE.forecast_data, 
            STATE.upper_forecast, 
            STATE.lower_forecast, 
            grouping, 
            sku_filter
        )
        update_forecast_display(chart_path)
        
    except Exception as e:
        print(f"chart regeneration error: {e}")
        update_status(f"Chart error: {e}", error=True)


def chart_grouping_changed_callback(sender, app_data):
    regenerate_chart()
    hide_summary_chart()


def chart_sku_changed_callback(sender, app_data):
    regenerate_chart()
    hide_summary_chart()


def toggle_summary_callback():
    if STATE.forecast_data is None:
        return update_status("Run forecast first", error=True)
    
    if dpg.does_item_exist("summary_container") and dpg.is_item_shown("summary_container"):
        hide_summary_chart()
        return
    
    try:
        grouping = dpg.get_value("chart_grouping_combo")
        chart_path = generate_sku_summary_chart(STATE.forecast_data, grouping)
        
        safe_configure_item("summary_container", show=True)
        
        success = safe_load_and_display_image(
            chart_path, "summary_image_group", "summary_image", "summary_texture"
        )
        
        if success:
            safe_set_label("summary_toggle_btn", "Hide Summary")
        else:
            if dpg.does_item_exist("summary_image_group"):
                dpg.add_text("Summary chart too large to display.", parent="summary_image_group", color=(255, 200, 100))
        
    except Exception as e:
        print(f"summary chart error: {e}")
        update_status(f"Summary error: {e}", error=True)


def hide_summary_chart():
    safe_configure_item("summary_container", show=False)
    safe_set_label("summary_toggle_btn", "Show Summary")
    safe_delete_item("summary_image")
    safe_delete_item("summary_texture")
    force_gc()


# ================ DASHBOARD CALLBACKS ================

def dashboard_sku_changed_callback(sender, app_data):
    update_dashboard()


def update_dashboard():
    if STATE.forecast_data is None:
        return
    
    try:
        grouping = dpg.get_value("dashboard_grouping_combo") if dpg.does_item_exist("dashboard_grouping_combo") else "Daily"
        sku_filter = dpg.get_value("dashboard_sku_combo") if dpg.does_item_exist("dashboard_sku_combo") else "All SKUs"
        
        data = calculate_dashboard_data(grouping)
        if data is None:
            return
        
        forecast_grouped = data['forecast_grouped'].copy()
        upper_grouped = data['upper_grouped'].copy()
        lower_grouped = data['lower_grouped'].copy()
        
        # filter by sku if selected
        if sku_filter and sku_filter != "All SKUs":
            if sku_filter in forecast_grouped.columns:
                forecast_grouped = forecast_grouped[[sku_filter]]
                upper_grouped = upper_grouped[[sku_filter]]
                lower_grouped = lower_grouped[[sku_filter]]
        
        total_forecast = forecast_grouped.sum().sum()
        total_upper = upper_grouped.sum().sum()
        total_lower = lower_grouped.sum().sum()
        
        avg_error_pct = ((total_upper - total_lower) / total_forecast) * 50 if total_forecast > 0 else 0
        
        # calculate avg daily from ORIGINAL forecast data
        avg_daily = STATE.forecast_data.mean().mean()
        if sku_filter and sku_filter != "All SKUs" and sku_filter in STATE.forecast_data.columns:
            avg_daily = STATE.forecast_data[sku_filter].mean()
        
        # update stats
        safe_set_value("stat_total_forecast", f"{total_forecast:,.0f}")
        safe_set_value("stat_avg_daily", f"{avg_daily:,.1f}")
        safe_set_value("stat_num_periods", str(len(forecast_grouped)))
        safe_set_value("stat_num_skus", str(len(forecast_grouped.columns)))
        
        # format dates properly
        start_date = forecast_grouped.index.min()
        end_date = forecast_grouped.index.max()
        safe_set_value("stat_date_range", f"{start_date:%d %b %Y} to {end_date:%d %b %Y}")
        safe_set_value("stat_confidence", f"{total_lower:,.0f} - {total_upper:,.0f}")
        safe_set_value("stat_error_pct", f"+/-{avg_error_pct:.1f}%")
        
        # color stats
        safe_configure_item("stat_total_forecast", color=GUIConfig.HEADER_COLOR)
        safe_configure_item("stat_avg_daily", color=GUIConfig.HEADER_COLOR)
        
        error_color = GUIConfig.SUCCESS_COLOR if avg_error_pct < 15 else (GUIConfig.WARNING_COLOR if avg_error_pct < 30 else GUIConfig.ERROR_COLOR)
        safe_configure_item("stat_error_pct", color=error_color)
        
        update_dashboard_table(forecast_grouped, upper_grouped, lower_grouped, grouping)
        
    except Exception as e:
        print(f"dashboard update error: {e}")
        import traceback
        traceback.print_exc()


def update_dashboard_table(forecast_grouped, upper_grouped, lower_grouped, grouping):
    safe_delete_item("dashboard_table")
    
    if not dpg.does_item_exist("dashboard_table_group"):
        return
    
    for child in dpg.get_item_children("dashboard_table_group", 1):
        if dpg.get_item_type(child) == "mvAppItemType::mvText":
            safe_delete_item(child)
    
    # get current SKU filter
    sku_filter = dpg.get_value("dashboard_sku_combo") if dpg.does_item_exist("dashboard_sku_combo") else "All SKUs"
    
    # determine which SKUs to show
    if sku_filter and sku_filter != "All SKUs":
        # single SKU selected
        if sku_filter in forecast_grouped.columns:
            skus_to_show = [sku_filter]
        else:
            dpg.add_text(f"SKU {sku_filter} not found", parent="dashboard_table_group", color=(255, 100, 100))
            return
    else:
        # all SKUs - limit to max
        max_sku_cols = LargeDataConfig.MAX_SKUS_DASHBOARD
        skus_to_show = forecast_grouped.columns.tolist()
        if len(skus_to_show) > max_sku_cols:
            totals = forecast_grouped.sum().sort_values(ascending=False)
            skus_to_show = totals.head(max_sku_cols).index.tolist()
    
    with dpg.table(header_row=True, parent="dashboard_table_group", 
                   tag="dashboard_table", resizable=True,
                   borders_innerH=True, borders_outerH=True,
                   borders_innerV=True, borders_outerV=True,
                   scrollY=True, scrollX=True, height=-1):
        
        dpg.add_table_column(label="Period", width_stretch=True)
        
        for sku in skus_to_show:
            sku_total = forecast_grouped[sku].sum()
            sku_upper = upper_grouped[sku].sum() if sku in upper_grouped.columns else sku_total
            sku_lower = lower_grouped[sku].sum() if sku in lower_grouped.columns else sku_total
            
            if sku_total > 0:
                sku_error = ((sku_upper - sku_lower) / sku_total) * 50
                label = f"{str(sku)[:12]} (+/-{sku_error:.0f}%)"
            else:
                label = str(sku)[:15]
            
            dpg.add_table_column(label=label, width_stretch=True)
        
        if len(skus_to_show) > 1:
            dpg.add_table_column(label="Total", width_stretch=True)
        
        for idx in forecast_grouped.index:
            with dpg.table_row():
                if hasattr(idx, 'strftime'):
                    if grouping == 'Monthly':
                        dpg.add_text(idx.strftime('%b %Y'))
                    elif grouping == 'Quarterly':
                        quarter = (idx.month - 1) // 3 + 1
                        dpg.add_text(f"Q{quarter} {idx.year}")
                    else:
                        dpg.add_text(idx.strftime('%d %b %Y'))
                else:
                    dpg.add_text(str(idx))
                
                row_total = 0
                for sku in skus_to_show:
                    val = forecast_grouped.loc[idx, sku]
                    row_total += val
                    dpg.add_text(f"{val:,.0f}")
                
                if len(skus_to_show) > 1:
                    dpg.add_text(f"{row_total:,.0f}")


def update_dashboard_callback():
    update_dashboard()
    update_status("Dashboard updated", success=True)


def grouping_changed_callback(sender, app_data):
    update_dashboard()


def show_forecast_diagnostics_callback():
    """
    show sku forecast diagnostics window
    """
    if STATE.clean_data is None:
        return update_status("No data loaded", error=True)
    
    # analyze all skus
    diagnostics = []
    
    for sku in STATE.sku_list:
        sku_data = STATE.clean_data[STATE.clean_data['SKU'] == sku]
        
        total_qty = sku_data['Quantity'].sum()
        record_count = len(sku_data)
        date_range = (sku_data['Date'].min(), sku_data['Date'].max())
        
        # determine status
        if sku in STATE.successful_skus:
            status = "Forecasted"
            status_color = GUIConfig.SUCCESS_COLOR
        elif sku in STATE.skipped_skus:
            status = STATE.skipped_skus[sku]
            status_color = GUIConfig.ERROR_COLOR
        elif STATE.forecast_data is not None:
            status = "Not processed"
            status_color = GUIConfig.WARNING_COLOR
        else:
            # analyze potential issues
            if total_qty == 0:
                status = "All zeros (no sales)"
                status_color = (180, 180, 180)
            elif record_count < DataConfig.MIN_DATA_POINTS:
                status = f"Only {record_count} records (need {DataConfig.MIN_DATA_POINTS})"
                status_color = (180, 180, 180)
            else:
                status = "Ready"
                status_color = (200, 200, 200)
        
        diagnostics.append({
            'sku': sku,
            'status': status,
            'status_color': status_color,
            'records': record_count,
            'total_qty': total_qty,
            'date_range': date_range
        })
    
    # create diagnostics window
    safe_delete_item("diagnostics_window")
    
    with dpg.window(label="SKU Forecast Diagnostics", tag="diagnostics_window",
                   width=800, height=600, pos=[300, 100]):
        
        dpg.add_text("SKU FORECAST DIAGNOSTICS", color=GUIConfig.HEADER_COLOR)
        dpg.add_separator()
        dpg.add_spacer(height=5)
        
        # summary
        total_skus = len(diagnostics)
        successful = len(STATE.successful_skus)
        skipped = len(STATE.skipped_skus)
        
        dpg.add_text(f"Total SKUs: {total_skus}")
        if STATE.forecast_data is not None:
            dpg.add_text(f"Forecasted: {successful}", color=GUIConfig.SUCCESS_COLOR)
            if skipped > 0:
                dpg.add_text(f"Skipped: {skipped}", color=GUIConfig.ERROR_COLOR)
        
        dpg.add_spacer(height=10)
        dpg.add_separator()
        dpg.add_spacer(height=5)
        
        # table
        with dpg.table(header_row=True, resizable=True, 
                       borders_innerH=True, borders_outerH=True,
                       borders_innerV=True, borders_outerV=True,
                       scrollY=True, height=-50):
            
            dpg.add_table_column(label="SKU", width_fixed=True, init_width_or_weight=120)
            dpg.add_table_column(label="Status", width_stretch=True)
            dpg.add_table_column(label="Records", width_fixed=True, init_width_or_weight=80)
            dpg.add_table_column(label="Total Qty", width_fixed=True, init_width_or_weight=100)
            dpg.add_table_column(label="Date Range", width_stretch=True)
            
            for diag in diagnostics:
                with dpg.table_row():
                    dpg.add_text(str(diag['sku']))
                    dpg.add_text(str(diag['status']), color=diag['status_color'])
                    dpg.add_text(f"{diag['records']}")
                    dpg.add_text(f"{diag['total_qty']:,.0f}")
                    
                    date_start = diag['date_range'][0]
                    date_end = diag['date_range'][1]
                    if hasattr(date_start, 'strftime'):
                        dpg.add_text(f"{date_start:%Y-%m-%d} to {date_end:%Y-%m-%d}")
                    else:
                        dpg.add_text(f"{date_start} to {date_end}")
        
        dpg.add_spacer(height=10)
        
        close_btn = dpg.add_button(label="Close", width=100,
                                   callback=lambda: safe_delete_item("diagnostics_window"))
        dpg.bind_item_theme(close_btn, "danger_button_theme")


def forecast_speed_callback(sender, app_data):
    STATE.forecast_speed = app_data