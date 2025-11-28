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

from config import Paths, GUIConfig, DataConfig, AutoTSConfig, ScenarioConfig, ExportConfig
from core.state import STATE
from core.data_operations import (
    clear_all_data,
    validate_forecast_requirements,
    export_results,
    calculate_dashboard_data,
    get_output_directory
)
from core.forecasting import run_forecast_thread, load_saved_model, forecast_with_loaded_model
from core.charting import generate_forecast_chart, generate_sku_summary_chart

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


# ================ UI UPDATE CALLBACKS ================

def update_status(message, error=False, success=False, warning=False):
    color = GUIConfig.ERROR_COLOR if error else (GUIConfig.SUCCESS_COLOR if success else (GUIConfig.WARNING_COLOR if warning else GUIConfig.STATUS_COLOR))
    dpg.set_value("status_text", message)
    dpg.configure_item("status_text", color=color)


def update_data_info(records, skus, mapping_info=""):
    info_text = f"Records: {records}  |  SKUs: {skus}"
    dpg.set_value("data_info_text", info_text)
    
    if mapping_info:
        dpg.set_value("column_mapping_text", mapping_info)
    else:
        dpg.set_value("column_mapping_text", "")


def update_sku_dropdown():
    if STATE.sku_list:
        sku_list_with_all = ["All SKUs"] + STATE.sku_list
        dpg.configure_item("scenario_sku", items=STATE.sku_list, default_value=STATE.sku_list[0])
        dpg.configure_item("chart_sku_combo", items=sku_list_with_all, default_value="All SKUs")


def update_data_preview():
    """
    update data preview table
    only show selected columns (Date, SKU, Quantity + additional)
    """
    if dpg.does_item_exist("preview_table"):
        dpg.delete_item("preview_table")
    
    # clear placeholder text
    for child in dpg.get_item_children("preview_group", 1):
        if dpg.get_item_type(child) == "mvAppItemType::mvText":
            dpg.delete_item(child)
    
    if STATE.clean_data is not None:
        # get columns to display
        display_columns = ['Date', 'SKU', 'Quantity']
        
        # add additional selected columns
        if STATE.additional_columns:
            for col in STATE.additional_columns:
                if col in STATE.clean_data.columns and col not in display_columns:
                    display_columns.append(col)
        
        # filter to only existing columns
        display_columns = [col for col in display_columns if col in STATE.clean_data.columns]
        
        # get preview data with only selected columns
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


def update_forecast_display(chart_path):
    if dpg.does_item_exist("forecast_texture"):
        dpg.delete_item("forecast_texture")
    if dpg.does_item_exist("forecast_image"):
        dpg.delete_item("forecast_image")
    
    # clear placeholder text
    for child in dpg.get_item_children("chart_image_group", 1):
        if dpg.get_item_type(child) == "mvAppItemType::mvText":
            dpg.delete_item(child)
    
    if chart_path and os.path.exists(chart_path):
        width, height, channels, data = dpg.load_image(str(chart_path))
        if data:
            with dpg.texture_registry():
                dpg.add_static_texture(width=width, height=height, default_value=data, tag="forecast_texture")
            dpg.add_image("forecast_texture", parent="chart_image_group", tag="forecast_image")


def clear_ui_data():
    if dpg.does_item_exist("preview_table"):
        dpg.delete_item("preview_table")
    if dpg.does_item_exist("forecast_image"):
        dpg.delete_item("forecast_image")
    if dpg.does_item_exist("forecast_texture"):
        dpg.delete_item("forecast_texture")
    if dpg.does_item_exist("summary_image"):
        dpg.delete_item("summary_image")
    if dpg.does_item_exist("summary_texture"):
        dpg.delete_item("summary_texture")
    
    dpg.set_value("data_info_text", "No data loaded")
    dpg.set_value("column_mapping_text", "")
    
    # restore placeholder
    for child in dpg.get_item_children("preview_group", 1):
        dpg.delete_item(child)
    dpg.add_text("Load a CSV to see data preview.", parent="preview_group", color=(150, 150, 150))


def clear_forecast_display():
    """
    clear forecast chart and dashboard before new forecast
    """
    # clear chart
    if dpg.does_item_exist("forecast_image"):
        dpg.delete_item("forecast_image")
    if dpg.does_item_exist("forecast_texture"):
        dpg.delete_item("forecast_texture")
    if dpg.does_item_exist("summary_image"):
        dpg.delete_item("summary_image")
    if dpg.does_item_exist("summary_texture"):
        dpg.delete_item("summary_texture")
    
    # add placeholder
    for child in dpg.get_item_children("chart_image_group", 1):
        dpg.delete_item(child)
    dpg.add_text("Running forecast...", parent="chart_image_group", color=(150, 150, 150))
    
    # clear dashboard stats
    stat_tags = ["stat_total_forecast", "stat_avg_daily", "stat_num_periods", 
                 "stat_num_skus", "stat_date_range", "stat_confidence",
                 "stat_error_pct", "stat_upper_pct", "stat_lower_pct"]
    for tag in stat_tags:
        if dpg.does_item_exist(tag):
            dpg.set_value(tag, "--")
    
    # clear dashboard table
    if dpg.does_item_exist("dashboard_table"):
        dpg.delete_item("dashboard_table")
    
    # hide summary
    if dpg.does_item_exist("summary_container"):
        dpg.configure_item("summary_container", show=False)


# ================ TIMER FUNCTIONS ================

def start_forecast_timer():
    """
    start timer for forecast duration
    """
    TIMER_STATE['running'] = True
    TIMER_STATE['start_time'] = time.time()
    
    def timer_loop():
        while TIMER_STATE['running']:
            elapsed = time.time() - TIMER_STATE['start_time']
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            
            try:
                if dpg.does_item_exist("forecast_btn"):
                    dpg.set_item_label("forecast_btn", f"Cancel ({minutes:02d}:{seconds:02d})")
            except:
                pass
            
            time.sleep(0.1)
    
    TIMER_STATE['thread'] = threading.Thread(target=timer_loop, daemon=True)
    TIMER_STATE['thread'].start()


def stop_forecast_timer():
    """
    stop forecast timer
    """
    TIMER_STATE['running'] = False
    
    try:
        if dpg.does_item_exist("forecast_btn"):
            dpg.set_item_label("forecast_btn", "Run Forecast")
            dpg.bind_item_theme("forecast_btn", "forecast_button_theme")
    except:
        pass


# ================ DATA CALLBACKS ================

def process_loaded_data(df, file_path, mapping_info=""):
    valid, msg = validate_columns(df)
    if not valid:
        return update_status(f"Error: {msg}", error=True)
    valid, msg = validate_data_types(df)
    if not valid:
        return update_status(f"Error: {msg}", error=True)
    
    STATE.raw_data = df
    STATE.clean_data = clean_dataframe(df, store_format=True)
    STATE.sku_list = get_sku_list(STATE.clean_data)
    
    # store additional columns from mapper
    if hasattr(mapper, 'TEMP_DATA') and mapper.TEMP_DATA.additional_columns:
        STATE.additional_columns = mapper.TEMP_DATA.additional_columns
    else:
        # detect additional columns if not mapped
        STATE.additional_columns = detect_additional_columns(STATE.clean_data)
    
    update_sku_dropdown()
    update_data_preview()
    update_data_info(len(STATE.clean_data), len(STATE.sku_list), mapping_info)
    update_status(f"Loaded: {len(STATE.clean_data)} records", success=True)


def load_csv(file_path):
    try:
        df = pd.read_csv(file_path)
        if all(col in df.columns for col in ['Date', 'SKU', 'Quantity']):
            # standard columns, clear additional
            mapper.TEMP_DATA.additional_columns = []
            process_loaded_data(df, file_path, "Standard columns")
        else:
            mapper.TEMP_DATA.pending_df = df
            mapper.TEMP_DATA.pending_path = file_path
            mapper.show_column_mapping_dialog(df, mapper.suggest_column_mapping(df.columns))
    except Exception as e:
        update_status(f"Error loading file: {e}", error=True)


def upload_callback():
    dpg.show_item("file_dialog")


def load_csv_callback(sender, app_data):
    load_csv(app_data['file_path_name'])


def cancel_load_callback(sender, app_data):
    pass


def remove_data_callback():
    clear_all_data()
    clear_ui_data()
    STATE.additional_columns = []
    update_status("All data removed", success=True)


# ================ FORECAST CALLBACKS ================

def forecast_callback():
    """
    run or cancel forecast
    """
    # if running, cancel
    if STATE.is_forecasting:
        STATE.request_cancel()
        update_status("Cancelling forecast...", warning=True)
        return
    
    if STATE.clean_data is None:
        return update_status("Load data first", error=True)
    
    valid, msg = validate_forecast_requirements()
    if not valid:
        return update_status(f"Error: {msg}", error=True)
    
    # clear previous results
    STATE.reset_forecast_state()
    clear_forecast_display()
    
    STATE.is_forecasting = True
    STATE.reset_cancel_flag()
    
    # update button appearance
    if dpg.does_item_exist("forecast_btn"):
        dpg.set_item_label("forecast_btn", "Cancel (00:00)")
        dpg.bind_item_theme("forecast_btn", "danger_button_theme")
    
    start_forecast_timer()
    update_status("Forecasting... please wait")
    
    def on_forecast_complete(success, message, chart_path):
        stop_forecast_timer()
        dpg.split_frame()
        
        if success:
            update_forecast_display(chart_path)
            update_dashboard()
        else:
            # restore placeholder on failure
            for child in dpg.get_item_children("chart_image_group", 1):
                dpg.delete_item(child)
            dpg.add_text("Run forecast to see chart.", parent="chart_image_group", color=(150, 150, 150))
        
        update_status(message, success=success, error=not success)
        STATE.is_forecasting = False
        gc.collect()
    
    threading.Thread(target=run_forecast_thread, args=(on_forecast_complete,), daemon=True).start()


def forecast_with_model_callback():
    """
    run forecast using loaded model
    """
    if STATE.loaded_model is None:
        return update_status("Load a model first", error=True)
    
    if STATE.clean_data is None:
        return update_status("Load data first", error=True)
    
    if STATE.is_forecasting:
        STATE.request_cancel()
        update_status("Cancelling forecast...", warning=True)
        return
    
    # clear previous results
    STATE.reset_forecast_state()
    clear_forecast_display()
    
    STATE.is_forecasting = True
    STATE.reset_cancel_flag()
    
    if dpg.does_item_exist("forecast_btn"):
        dpg.set_item_label("forecast_btn", "Cancel (00:00)")
        dpg.bind_item_theme("forecast_btn", "danger_button_theme")
    
    start_forecast_timer()
    update_status("Forecasting with loaded model...")
    
    def on_forecast_complete(success, message, chart_path):
        stop_forecast_timer()
        dpg.split_frame()
        
        if success:
            update_forecast_display(chart_path)
            update_dashboard()
        
        update_status(message, success=success, error=not success)
        STATE.is_forecasting = False
        gc.collect()
    
    threading.Thread(target=forecast_with_loaded_model, args=(on_forecast_complete,), daemon=True).start()


def forecast_days_callback(sender, app_data):
    STATE.forecast_days = app_data


def forecast_granularity_callback(sender, app_data):
    STATE.forecast_granularity = app_data


def export_model_callback():
    """
    export trained model to file
    """
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
    """
    show model file dialog
    """
    dpg.show_item("model_file_dialog")


def load_model_file_callback(sender, app_data):
    """
    handle model file selection
    """
    file_path = app_data.get('file_path_name', '')
    if file_path:
        success, message = load_saved_model(file_path)
        if success:
            model_name = Path(file_path).name
            dpg.set_value("loaded_model_text", f"Loaded: {model_name}")
            if dpg.does_item_exist("use_model_btn"):
                dpg.configure_item("use_model_btn", show=True)
        update_status(message, success=success, error=not success)


def export_callback():
    if STATE.forecast_data is None:
        return update_status("No forecast to export", error=True)
    
    success, message = export_results(datetime.now().strftime(ExportConfig.TIMESTAMP_FORMAT))
    update_status(message, success=success, error=not success)


# ================ EXPORT DIRECTORY CALLBACKS ================

def select_export_dir_callback():
    """
    show folder selection dialog
    """
    dpg.show_item("folder_dialog")


def folder_selected_callback(sender, app_data):
    """
    handle folder selection
    """
    selected_path = app_data.get('file_path_name', '')
    if selected_path:
        STATE.custom_output_dir = selected_path
        dpg.set_value("export_dir_text", str(selected_path))
        update_status("Export directory set", success=True)


def folder_cancel_callback(sender, app_data):
    pass


def reset_export_dir_callback():
    """
    reset to default export directory
    """
    STATE.custom_output_dir = None
    dpg.set_value("export_dir_text", str(Paths.USER_OUTPUT))
    update_status("Export directory reset", success=True)


# ================ SCENARIO CALLBACKS ================

def scenario_type_changed_callback(sender, app_data):
    if app_data == "Demand Spike":
        dpg.configure_item("spike_multiplier_group", show=True)
        dpg.configure_item("delay_days_group", show=False)
    elif app_data == "Supply Delay":
        dpg.configure_item("spike_multiplier_group", show=False)
        dpg.configure_item("delay_days_group", show=True)


def apply_scenario_callback():
    """
    apply selected scenario to forecast
    """
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
            
            scenario_info = {
                'type': 'Demand Spike',
                'sku': sku,
                'multiplier': multiplier,
                'start': str(start_date),
                'end': str(end_date)
            }
            
        elif scenario_type == "Supply Delay":
            delay_days = int(dpg.get_value("delay_days"))
            
            if sku in STATE.forecast_data.columns:
                sku_data = STATE.forecast_data[sku].copy()
                STATE.forecast_data[sku] = sku_data.shift(delay_days, fill_value=0)
                
                if STATE.upper_forecast is not None and sku in STATE.upper_forecast.columns:
                    STATE.upper_forecast[sku] = STATE.upper_forecast[sku].shift(delay_days, fill_value=0)
                
                if STATE.lower_forecast is not None and sku in STATE.lower_forecast.columns:
                    STATE.lower_forecast[sku] = STATE.lower_forecast[sku].shift(delay_days, fill_value=0)
            
            scenario_info = {
                'type': 'Supply Delay',
                'sku': sku,
                'delay_days': delay_days,
                'start': str(start_date)
            }
        
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
    """
    reset all applied scenarios
    """
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
    """
    extract date from dpg date picker
    """
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
        dpg.set_value(f"{tag_prefix}_date", date_dict)
    except Exception as e:
        print(f"date picker error: {e}")


# ================ CHART CALLBACKS ================

def regenerate_chart():
    """
    regenerate forecast chart with current settings
    """
    if STATE.forecast_data is None:
        return
    
    try:
        grouping = dpg.get_value("chart_grouping_combo")
        sku_filter = dpg.get_value("chart_sku_combo")
        
        df_pivot = prepare_for_autots(STATE.clean_data, use_features=False)
        df_pivot = df_pivot.set_index('Date')
        
        forecast = STATE.forecast_data
        upper = STATE.upper_forecast
        lower = STATE.lower_forecast
        
        if sku_filter and sku_filter != "All SKUs":
            if sku_filter in forecast.columns:
                forecast = forecast[[sku_filter]]
                df_pivot = df_pivot[[sku_filter]] if sku_filter in df_pivot.columns else df_pivot
                if upper is not None and sku_filter in upper.columns:
                    upper = upper[[sku_filter]]
                if lower is not None and sku_filter in lower.columns:
                    lower = lower[[sku_filter]]
        
        chart_path = generate_forecast_chart(df_pivot, forecast, upper, lower, grouping)
        update_forecast_display(chart_path)
        
    except Exception as e:
        print(f"chart regeneration error: {e}")


def chart_grouping_changed_callback(sender, app_data):
    regenerate_chart()
    hide_summary_chart()


def chart_sku_changed_callback(sender, app_data):
    regenerate_chart()
    hide_summary_chart()


def toggle_summary_callback():
    """
    toggle sku summary chart display
    """
    if STATE.forecast_data is None:
        return update_status("Run forecast first", error=True)
    
    if dpg.does_item_exist("summary_container"):
        is_visible = dpg.is_item_shown("summary_container")
        if is_visible:
            hide_summary_chart()
            return
    
    try:
        grouping = dpg.get_value("chart_grouping_combo")
        chart_path = generate_sku_summary_chart(STATE.forecast_data, grouping)
        
        if dpg.does_item_exist("summary_container"):
            dpg.configure_item("summary_container", show=True)
        
        if dpg.does_item_exist("summary_texture"):
            dpg.delete_item("summary_texture")
        if dpg.does_item_exist("summary_image"):
            dpg.delete_item("summary_image")
        
        if chart_path and os.path.exists(chart_path):
            width, height, channels, data = dpg.load_image(str(chart_path))
            if data:
                with dpg.texture_registry():
                    dpg.add_static_texture(width=width, height=height, 
                                          default_value=data, tag="summary_texture")
                dpg.add_image("summary_texture", parent="summary_image_group", tag="summary_image")
        
        if dpg.does_item_exist("summary_toggle_btn"):
            dpg.set_item_label("summary_toggle_btn", "Hide Summary")
        
    except Exception as e:
        print(f"summary chart error: {e}")
        update_status(f"Summary error: {e}", error=True)


def hide_summary_chart():
    if dpg.does_item_exist("summary_container"):
        dpg.configure_item("summary_container", show=False)
    if dpg.does_item_exist("summary_toggle_btn"):
        dpg.set_item_label("summary_toggle_btn", "Show Summary")


# ================ DASHBOARD CALLBACKS ================

def update_dashboard():
    """
    refresh dashboard statistics with error percentages
    """
    if STATE.forecast_data is None:
        return
    
    try:
        grouping = dpg.get_value("dashboard_grouping_combo") if dpg.does_item_exist("dashboard_grouping_combo") else "Daily"
        data = calculate_dashboard_data(grouping)
        
        if data is None:
            return
        
        total_forecast = data['total_forecast']
        total_upper = data['total_upper']
        total_lower = data['total_lower']
        
        if total_forecast > 0:
            upper_pct = ((total_upper - total_forecast) / total_forecast) * 100
            lower_pct = ((total_forecast - total_lower) / total_forecast) * 100
            avg_error_pct = (upper_pct + lower_pct) / 2
        else:
            upper_pct = 0
            lower_pct = 0
            avg_error_pct = 0
        
        if dpg.does_item_exist("stat_total_forecast"):
            total = data['total_forecast']
            if total >= 1000000:
                dpg.set_value("stat_total_forecast", f"{total/1000000:.2f}M")
            elif total >= 1000:
                dpg.set_value("stat_total_forecast", f"{total/1000:.2f}K")
            else:
                dpg.set_value("stat_total_forecast", f"{total:,.0f}")
        
        if dpg.does_item_exist("stat_avg_daily"):
            dpg.set_value("stat_avg_daily", f"{data['avg_daily']:,.1f}")
        
        if dpg.does_item_exist("stat_num_periods"):
            dpg.set_value("stat_num_periods", str(data['num_periods']))
        
        if dpg.does_item_exist("stat_num_skus"):
            dpg.set_value("stat_num_skus", str(data['num_skus']))
        
        if dpg.does_item_exist("stat_date_range"):
            start = data['start_date']
            end = data['end_date']
            if hasattr(start, 'strftime'):
                start = start.strftime('%Y-%m-%d')
            if hasattr(end, 'strftime'):
                end = end.strftime('%Y-%m-%d')
            dpg.set_value("stat_date_range", f"{start} to {end}")
        
        if dpg.does_item_exist("stat_confidence"):
            lower = data['total_lower']
            upper = data['total_upper']
            if lower >= 1000:
                lower_str = f"{lower/1000:.1f}K"
            else:
                lower_str = f"{lower:,.0f}"
            if upper >= 1000:
                upper_str = f"{upper/1000:.1f}K"
            else:
                upper_str = f"{upper:,.0f}"
            dpg.set_value("stat_confidence", f"{lower_str} - {upper_str}")
        
        if dpg.does_item_exist("stat_error_pct"):
            dpg.set_value("stat_error_pct", f"+/-{avg_error_pct:.1f}%")
        
        if dpg.does_item_exist("stat_upper_pct"):
            dpg.set_value("stat_upper_pct", f"+{upper_pct:.1f}%")
        
        if dpg.does_item_exist("stat_lower_pct"):
            dpg.set_value("stat_lower_pct", f"-{lower_pct:.1f}%")
        
        update_dashboard_table(data)
        
    except Exception as e:
        print(f"dashboard update error: {e}")
        import traceback
        traceback.print_exc()


def update_dashboard_table(data):
    """
    update dashboard forecast table with error percentages
    """
    if dpg.does_item_exist("dashboard_table"):
        dpg.delete_item("dashboard_table")
    
    if not dpg.does_item_exist("dashboard_table_group"):
        return
    
    # clear placeholder
    for child in dpg.get_item_children("dashboard_table_group", 1):
        if dpg.get_item_type(child) == "mvAppItemType::mvText":
            dpg.delete_item(child)
    
    forecast_grouped = data['forecast_grouped']
    upper_grouped = data['upper_grouped']
    lower_grouped = data['lower_grouped']
    
    with dpg.table(header_row=True, parent="dashboard_table_group", 
                   tag="dashboard_table", resizable=True,
                   borders_innerH=True, borders_outerH=True,
                   borders_innerV=True, borders_outerV=True,
                   scrollY=True, height=300):
        
        dpg.add_table_column(label="Period")
        for sku in forecast_grouped.columns:
            dpg.add_table_column(label=str(sku))
        dpg.add_table_column(label="Total")
        dpg.add_table_column(label="Error %")
        
        for idx in forecast_grouped.index:
            with dpg.table_row():
                if hasattr(idx, 'strftime'):
                    dpg.add_text(idx.strftime('%Y-%m-%d'))
                else:
                    dpg.add_text(str(idx))
                
                row_total = 0
                row_upper = 0
                row_lower = 0
                
                for sku in forecast_grouped.columns:
                    val = forecast_grouped.loc[idx, sku]
                    row_total += val
                    
                    if sku in upper_grouped.columns:
                        row_upper += upper_grouped.loc[idx, sku]
                    if sku in lower_grouped.columns:
                        row_lower += lower_grouped.loc[idx, sku]
                    
                    if val >= 1000:
                        dpg.add_text(f"{val/1000:.1f}K")
                    else:
                        dpg.add_text(f"{val:,.0f}")
                
                if row_total >= 1000:
                    dpg.add_text(f"{row_total/1000:.1f}K")
                else:
                    dpg.add_text(f"{row_total:,.0f}")
                
                if row_total > 0:
                    error_range = row_upper - row_lower
                    error_pct = (error_range / row_total) * 50
                    dpg.add_text(f"+/-{error_pct:.1f}%")
                else:
                    dpg.add_text("--")


def update_dashboard_callback():
    update_dashboard()
    update_status("Dashboard updated", success=True)


def grouping_changed_callback(sender, app_data):
    update_dashboard()