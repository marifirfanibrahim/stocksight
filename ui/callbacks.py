"""
callback functions for ui events
handle user interactions
"""


# ================ IMPORTS ================

import dearpygui.dearpygui as dpg
import threading
from datetime import datetime
from pathlib import Path

from config import Paths, GUIConfig, DataConfig, ExportConfig, ScenarioConfig
from core.state import STATE
from core.data_operations import (
    get_output_directory,
    load_csv_file,
    clear_all_data,
    validate_forecast_requirements,
    export_results,
    calculate_dashboard_data
)
from core.forecasting import run_forecast_thread
from utils.preprocessing import (
    clean_dataframe,
    apply_demand_spike,
    apply_supply_delay,
    format_dates_output
)


# ================ UI UPDATE FUNCTIONS ================

def update_status(message, error=False, success=False, warning=False):
    """
    update status bar text
    with color coding
    """
    if error:
        color = GUIConfig.ERROR_COLOR
    elif success:
        color = GUIConfig.SUCCESS_COLOR
    elif warning:
        color = GUIConfig.WARNING_COLOR
    else:
        color = GUIConfig.STATUS_COLOR
    
    dpg.set_value("status_text", message)
    dpg.configure_item("status_text", color=color)


def update_sku_dropdown():
    """
    populate scenario sku dropdown
    """
    if STATE.sku_list:
        if dpg.does_item_exist("scenario_sku"):
            dpg.configure_item("scenario_sku", items=STATE.sku_list)
            dpg.set_value("scenario_sku", STATE.sku_list[0])


def update_scenario_sku_dropdown():
    """
    sync scenario sku dropdown
    """
    if STATE.sku_list:
        dpg.configure_item("scenario_sku", items=STATE.sku_list)
        dpg.set_value("scenario_sku", STATE.sku_list[0])


def update_data_preview():
    """
    show data preview table
    """
    # ---------- CLEAR EXISTING ----------
    if dpg.does_item_exist("preview_table"):
        dpg.delete_item("preview_table")
    
    if STATE.clean_data is None:
        return
    
    # ---------- CREATE TABLE ----------
    preview = STATE.clean_data.head(DataConfig.PREVIEW_ROWS).copy()
    
    # ---------- FORMAT DATES ----------
    if STATE.detected_date_format:
        preview['Date'] = format_dates_output(preview['Date'], STATE.detected_date_format)
    
    with dpg.table(header_row=True, parent="preview_group", tag="preview_table",
                   borders_innerH=True, borders_outerH=True,
                   borders_innerV=True, borders_outerV=True):
        
        # ---------- ADD COLUMNS ----------
        for col in preview.columns:
            dpg.add_table_column(label=str(col))
        
        # ---------- ADD ROWS ----------
        for _, row in preview.iterrows():
            with dpg.table_row():
                for val in row:
                    dpg.add_text(str(val))


def update_forecast_display(chart_path=None):
    """
    load and display forecast chart
    """
    # ---------- CHECK FILE EXISTS ----------
    if chart_path is None:
        chart_path = get_output_directory() / "forecast.png"
    
    chart_path = Path(chart_path)
    
    if not chart_path.exists():
        return
    
    # ---------- LOAD TEXTURE ----------
    if dpg.does_item_exist("forecast_texture"):
        dpg.delete_item("forecast_texture")
    
    width, height, channels, data = dpg.load_image(str(chart_path))
    
    with dpg.texture_registry():
        dpg.add_static_texture(width, height, data, tag="forecast_texture")
    
    # ---------- UPDATE IMAGE ----------
    if dpg.does_item_exist("forecast_image"):
        dpg.configure_item("forecast_image", texture_tag="forecast_texture")
    else:
        dpg.add_image("forecast_texture", parent="chart_group", tag="forecast_image")


def update_feature_list_ui():
    """
    update feature selection checkboxes
    """
    # ---------- CLEAR EXISTING ----------
    if dpg.does_item_exist("feature_list"):
        dpg.delete_item("feature_list")
    
    if not STATE.feature_columns:
        return
    
    # ---------- CREATE CHECKBOXES ----------
    with dpg.group(parent="features_group", tag="feature_list"):
        for col in STATE.feature_columns:
            dpg.add_checkbox(label=col, default_value=True, 
                           callback=feature_toggle_callback, user_data=col)


def update_seasonality_display():
    """
    show seasonality detection results
    """
    if not STATE.seasonality_info:
        dpg.set_value("seasonality_text", "Load data to analyze seasonality")
        return
    
    info_text = []
    
    if STATE.seasonality_info.get('has_monthly_seasonality'):
        cv = STATE.seasonality_info.get('monthly_cv', 0)
        info_text.append(f"Monthly pattern detected (CV: {cv:.2f})")
    else:
        info_text.append("No strong monthly pattern")
    
    if STATE.seasonality_info.get('has_weekly_seasonality'):
        cv = STATE.seasonality_info.get('weekly_cv', 0)
        info_text.append(f"Weekly pattern detected (CV: {cv:.2f})")
    else:
        info_text.append("No strong weekly pattern")
    
    dpg.set_value("seasonality_text", "\n".join(info_text))


def update_scenario_history_display():
    """
    update scenario history text
    """
    if not hasattr(STATE, 'scenario_history'):
        STATE.scenario_history = []
    
    if not STATE.scenario_history:
        dpg.set_value("scenario_history_text", "No scenarios applied yet")
    else:
        history_text = []
        for i, scenario in enumerate(STATE.scenario_history, 1):
            history_text.append(f"{i}. {scenario}")
        dpg.set_value("scenario_history_text", "\n".join(history_text))


def clear_ui_data():
    """
    clear all data from ui
    """
    # ---------- CLEAR PREVIEW ----------
    if dpg.does_item_exist("preview_table"):
        dpg.delete_item("preview_table")
    
    # ---------- CLEAR FEATURES ----------
    if dpg.does_item_exist("feature_list"):
        dpg.delete_item("feature_list")
    
    # ---------- CLEAR FORECAST ----------
    if dpg.does_item_exist("forecast_image"):
        dpg.delete_item("forecast_image")
    
    # ---------- CLEAR DASHBOARD ----------
    if dpg.does_item_exist("dashboard_table"):
        dpg.delete_item("dashboard_table")
    
    if dpg.does_item_exist("sku_breakdown_table"):
        dpg.delete_item("sku_breakdown_table")
    
    # ---------- RESET TEXT ----------
    dpg.set_value("seasonality_text", "Load data to analyze seasonality")
    dpg.set_value("scenario_history_text", "No scenarios applied yet")
    dpg.set_value("dashboard_status_text", "Run forecast to see details")
    dpg.set_value("total_forecast_text", "--")
    dpg.set_value("avg_daily_text", "--")
    dpg.set_value("confidence_range_text", "--")
    dpg.set_value("avg_error_text", "--")
    dpg.set_value("forecast_period_text", "--")
    dpg.set_value("num_skus_text", "--")
    
    # ---------- CLEAR DROPDOWNS ----------
    if dpg.does_item_exist("scenario_sku"):
        dpg.configure_item("scenario_sku", items=[])


# ================ DASHBOARD FUNCTIONS ================

def update_dashboard():
    """
    update dashboard with forecast data
    """
    if STATE.forecast_data is None:
        dpg.set_value("dashboard_status_text", "Run forecast to see details")
        return
    
    grouping = dpg.get_value("grouping_combo")
    data = calculate_dashboard_data(grouping)
    
    if data is None:
        return
    
    # ---------- UPDATE SUMMARY STATS ----------
    dpg.set_value("total_forecast_text", f"{data['total_forecast']:,.0f}")
    dpg.set_value("avg_daily_text", f"{data['avg_daily']:,.1f}")
    dpg.set_value("confidence_range_text", f"{data['total_lower']:,.0f} - {data['total_upper']:,.0f}")
    dpg.set_value("avg_error_text", f"±{data['avg_error']:,.1f}")
    
    # ---------- FORMAT DATES ----------
    if STATE.detected_date_format:
        try:
            start_str = data['start_date'].strftime(STATE.detected_date_format)
            end_str = data['end_date'].strftime(STATE.detected_date_format)
        except:
            start_str = str(data['start_date'])
            end_str = str(data['end_date'])
    else:
        start_str = str(data['start_date'])
        end_str = str(data['end_date'])
    
    dpg.set_value("forecast_period_text", f"{start_str} to {end_str}")
    dpg.set_value("num_skus_text", str(data['num_skus']))
    
    dpg.set_value("dashboard_status_text", f"Showing {grouping.lower()} grouped data")
    
    # ---------- UPDATE FORECAST TABLE ----------
    update_dashboard_table(data)
    
    # ---------- UPDATE SKU BREAKDOWN ----------
    update_sku_breakdown(data)


def update_dashboard_table(data):
    """
    update forecast details table
    """
    # ---------- CLEAR EXISTING ----------
    if dpg.does_item_exist("dashboard_table"):
        dpg.delete_item("dashboard_table")
    
    forecast = data['forecast_grouped']
    upper = data['upper_grouped']
    lower = data['lower_grouped']
    errors = data['error_margins']
    
    with dpg.table(header_row=True, parent="dashboard_table_group", tag="dashboard_table",
                   borders_innerH=True, borders_outerH=True,
                   borders_innerV=True, borders_outerV=True):
        
        # ---------- ADD COLUMNS ----------
        dpg.add_table_column(label="Date")
        
        for sku in forecast.columns:
            dpg.add_table_column(label=f"{sku}")
            dpg.add_table_column(label=f"± Error")
        
        # ---------- ADD ROWS ----------
        for idx in forecast.index:
            with dpg.table_row():
                # ---------- DATE ----------
                if STATE.detected_date_format:
                    try:
                        date_str = idx.strftime(STATE.detected_date_format)
                    except:
                        date_str = str(idx)
                else:
                    date_str = str(idx)
                
                dpg.add_text(date_str)
                
                # ---------- VALUES ----------
                for sku in forecast.columns:
                    forecast_val = forecast.loc[idx, sku]
                    error_val = errors.loc[idx, sku]
                    
                    dpg.add_text(f"{forecast_val:,.0f}")
                    dpg.add_text(f"±{error_val:,.0f}", color=(150, 150, 150))


def update_sku_breakdown(data):
    """
    update sku breakdown table
    """
    # ---------- CLEAR EXISTING ----------
    if dpg.does_item_exist("sku_breakdown_table"):
        dpg.delete_item("sku_breakdown_table")
    
    # ---------- CLEAR GROUP ----------
    for child in dpg.get_item_children("sku_breakdown_group", 1):
        dpg.delete_item(child)
    
    forecast = data['forecast_grouped']
    upper = data['upper_grouped']
    lower = data['lower_grouped']
    
    with dpg.table(header_row=True, parent="sku_breakdown_group", tag="sku_breakdown_table",
                   borders_innerH=True, borders_outerH=True,
                   borders_innerV=True, borders_outerV=True):
        
        # ---------- ADD COLUMNS ----------
        dpg.add_table_column(label="SKU")
        dpg.add_table_column(label="Total Forecast")
        dpg.add_table_column(label="Lower Bound")
        dpg.add_table_column(label="Upper Bound")
        dpg.add_table_column(label="Error Margin")
        
        # ---------- ADD ROWS ----------
        for sku in forecast.columns:
            with dpg.table_row():
                total_forecast = forecast[sku].sum()
                total_lower = lower[sku].sum()
                total_upper = upper[sku].sum()
                error_margin = total_upper - total_lower
                
                dpg.add_text(sku)
                dpg.add_text(f"{total_forecast:,.0f}")
                dpg.add_text(f"{total_lower:,.0f}")
                dpg.add_text(f"{total_upper:,.0f}")
                dpg.add_text(f"±{error_margin/2:,.0f}")


def update_dashboard_callback():
    """
    dashboard refresh button callback
    """
    update_dashboard()


def grouping_changed_callback(sender, app_data):
    """
    grouping combo changed callback
    """
    STATE.date_grouping = app_data
    update_dashboard()


# ================ GRANULARITY CALLBACK ================

def forecast_granularity_callback(sender, app_data):
    """
    handle forecast granularity change
    """
    STATE.forecast_granularity = app_data
    print(f"forecast granularity set to: {app_data}")

    
# ================ FILE CALLBACKS ================

def load_csv_callback(sender, app_data):
    """
    handle csv file selection
    load and validate data
    """
    file_path = app_data['file_path_name']
    success, message = load_csv_file(file_path)
    
    if success:
        update_sku_dropdown()
        update_data_preview()
        update_seasonality_display()
        
        if STATE.feature_columns:
            update_feature_list_ui()
        
        update_status(message, success=True)
    else:
        update_status(message, error=True)


def cancel_callback(sender, app_data):
    """
    handle file dialog cancel
    """
    pass


def upload_callback():
    """
    open file dialog for csv
    """
    dpg.show_item("file_dialog")


# ================ DATA CALLBACKS ================

def reset_data_callback():
    """
    reset to original data
    clear modifications
    """
    if STATE.raw_data is not None:
        STATE.clean_data = clean_dataframe(STATE.raw_data, store_format=False)
        STATE.scenario_history = []
        update_data_preview()
        update_scenario_history_display()
        update_status("Data reset to original", success=True)
        print("data reset")
    else:
        update_status("No data to reset", warning=True)


def remove_data_callback():
    """
    remove all loaded data
    clear everything
    """
    clear_all_data()
    clear_ui_data()
    update_status("All data removed", success=True)
    print("all data removed")


# ================ OUTPUT CALLBACKS ================

def select_output_directory_callback():
    """
    open directory selection dialog
    """
    dpg.show_item("output_dir_dialog")


def output_dir_callback(sender, app_data):
    """
    handle output directory selection
    """
    selected_dir = app_data['file_path_name']
    STATE.custom_output_dir = selected_dir
    
    dpg.set_value("output_dir_text", f"Output: {selected_dir}")
    update_status(f"Output directory: {selected_dir}")
    print(f"output directory set: {selected_dir}")


def reset_output_directory_callback():
    """
    reset to default user documents
    """
    STATE.custom_output_dir = None
    default_dir = str(Paths.USER_OUTPUT)
    dpg.set_value("output_dir_text", f"Output: {default_dir}")
    update_status(f"Reset to default: {default_dir}")
    print(f"reset output to: {default_dir}")


# ================ FORECAST CALLBACKS ================

def forecast_days_callback(sender, app_data):
    """
    handle forecast days change
    """
    STATE.forecast_days = int(app_data)


def forecast_callback():
    """
    trigger forecast execution
    """
    if STATE.clean_data is None:
        update_status("Error: No data loaded", error=True)
        return
    
    if STATE.is_forecasting:
        update_status("Forecast already running", warning=True)
        return
    
    # ---------- VALIDATE DATA ----------
    valid, msg = validate_forecast_requirements()
    if not valid:
        update_status(f"Error: {msg}", error=True)
        return
    
    if "Warning" in msg:
        update_status(msg, warning=True)
        print(msg)
    
    STATE.is_forecasting = True
    STATE.use_features = dpg.get_value("use_features_checkbox")
    STATE.forecast_granularity = dpg.get_value("forecast_granularity_combo")
    
    granularity_msg = f" at {STATE.forecast_granularity.lower()} level" if STATE.forecast_granularity != 'Daily' else ""
    update_status(f"Forecasting{granularity_msg}... please wait")
    
    # ---------- CALLBACK FOR UI UPDATE ----------
    def update_forecast_ui(success, message, chart_path):
        dpg.split_frame()
        if success:
            # Get chart grouping for display
            chart_grouping = dpg.get_value("chart_grouping_combo") if dpg.does_item_exist("chart_grouping_combo") else "Daily"
            
            # Regenerate chart with grouping
            try:
                from utils.preprocessing import prepare_for_autots
                from core.charting import generate_forecast_chart
                
                df_pivot = prepare_for_autots(STATE.clean_data, use_features=False)
                df_pivot = df_pivot.set_index('Date')
                
                chart_path = generate_forecast_chart(
                    df_pivot, 
                    STATE.forecast_data, 
                    STATE.upper_forecast, 
                    STATE.lower_forecast,
                    chart_grouping
                )
            except:
                pass
            
            update_forecast_display(chart_path)
            update_dashboard()
            update_status(message, success=True)
        else:
            update_status(message, error=True)
    
    # ---------- RUN IN THREAD ----------
    thread = threading.Thread(target=run_forecast_thread, args=(update_forecast_ui,))
    thread.start()


def export_callback():
    """
    export current results
    """
    timestamp = datetime.now().strftime(ExportConfig.TIMESTAMP_FORMAT)
    success, message = export_results(timestamp)
    
    if success:
        update_status(message, success=True)
    else:
        update_status(message, error=True)


# ================ SCENARIO CALLBACKS ================

def apply_scenario_callback():
    """
    apply scenario modifications
    recalculate forecast
    """
    if STATE.clean_data is None:
        update_status("Error: No data loaded", error=True)
        return
    
    # ---------- GET PARAMETERS ----------
    scenario_type = dpg.get_value("scenario_type")
    sku = dpg.get_value("scenario_sku")
    
    if not sku:
        update_status("Error: Select SKU for scenario", error=True)
        return
    
    # ---------- TRACK HISTORY ----------
    if not hasattr(STATE, 'scenario_history'):
        STATE.scenario_history = []
    
    # ---------- APPLY SCENARIO ----------
    if scenario_type == "Demand Spike":
        multiplier = dpg.get_value("spike_multiplier")
        start = dpg.get_value("scenario_start")
        end = dpg.get_value("scenario_end")
        
        STATE.clean_data = apply_demand_spike(
            STATE.clean_data, sku, multiplier, start, end
        )
        
        # ---------- ADD TO HISTORY ----------
        history_entry = f"Spike: {sku} x{multiplier:.1f} ({start} to {end})"
        STATE.scenario_history.append(history_entry)
        
        update_status(f"Applied {multiplier}x demand spike to {sku}", success=True)
        print(f"demand spike: {sku} x{multiplier} from {start} to {end}")
        
    elif scenario_type == "Supply Delay":
        delay = int(dpg.get_value("delay_days"))
        start = dpg.get_value("scenario_start")
        
        STATE.clean_data = apply_supply_delay(
            STATE.clean_data, sku, delay, start
        )
        
        # ---------- ADD TO HISTORY ----------
        history_entry = f"Delay: {sku} +{delay} days (from {start})"
        STATE.scenario_history.append(history_entry)
        
        update_status(f"Applied {delay} day delay to {sku}", success=True)
        print(f"supply delay: {sku} +{delay} days from {start}")
    
    # ---------- UPDATE DISPLAYS ----------
    update_data_preview()
    update_scenario_history_display()


def reset_all_scenarios_callback():
    """
    reset all scenario settings to default
    """
    # ---------- RESET VALUES ----------
    dpg.set_value("spike_multiplier", ScenarioConfig.DEFAULT_SPIKE_MULTIPLIER)
    dpg.set_value("delay_days", ScenarioConfig.DEFAULT_DELAY_DAYS)
    dpg.set_value("scenario_start", "2024-01-15")
    dpg.set_value("scenario_end", "2024-01-25")
    dpg.set_value("scenario_type", "Demand Spike")
    
    # ---------- RESET DATA ----------
    if STATE.raw_data is not None:
        STATE.clean_data = clean_dataframe(STATE.raw_data, store_format=False)
        update_data_preview()
        STATE.scenario_history = []
        update_scenario_history_display()
        update_status("All scenarios reset", success=True)
        print("all scenarios reset")
    else:
        update_status("No data to reset", warning=True)


# ================ FEATURE CALLBACKS ================

def feature_toggle_callback(sender, app_data, user_data):
    """
    handle feature selection toggle
    """
    column = user_data
    enabled = app_data
    
    if enabled and column not in STATE.selected_features:
        STATE.selected_features.append(column)
    elif not enabled and column in STATE.selected_features:
        STATE.selected_features.remove(column)
    
    print(f"feature {column}: {'enabled' if enabled else 'disabled'}")


# ================ CHART CALLBACKS ================

def refresh_chart_callback():
    """
    refresh chart with current grouping
    """
    if STATE.forecast_data is None:
        update_status("No forecast to display", warning=True)
        return
    
    grouping = dpg.get_value("chart_grouping_combo")
    
    update_status(f"Generating {grouping.lower()} chart...")
    
    try:
        # ---------- GET HISTORICAL DATA ----------
        from utils.preprocessing import prepare_for_autots
        df_pivot = prepare_for_autots(STATE.clean_data, use_features=False)
        df_pivot = df_pivot.set_index('Date')
        
        # ---------- GENERATE CHART ----------
        from core.charting import generate_forecast_chart
        chart_path = generate_forecast_chart(
            df_pivot, 
            STATE.forecast_data, 
            STATE.upper_forecast, 
            STATE.lower_forecast,
            grouping
        )
        
        # ---------- UPDATE DISPLAY ----------
        update_forecast_display(chart_path)
        update_status(f"Chart updated ({grouping})", success=True)
        
    except Exception as e:
        update_status(f"Chart error: {str(e)}", error=True)
        print(f"chart error: {e}")


def generate_sku_summary_callback():
    """
    generate sku summary bar chart
    """
    if STATE.forecast_data is None:
        update_status("No forecast to display", warning=True)
        return
    
    grouping = dpg.get_value("chart_grouping_combo")
    
    try:
        from core.charting import generate_sku_summary_chart
        chart_path = generate_sku_summary_chart(STATE.forecast_data, grouping)
        
        # ---------- LOAD AND DISPLAY ----------
        if dpg.does_item_exist("summary_texture"):
            dpg.delete_item("summary_texture")
        
        width, height, channels, data = dpg.load_image(str(chart_path))
        
        with dpg.texture_registry():
            dpg.add_static_texture(width, height, data, tag="summary_texture")
        
        if dpg.does_item_exist("summary_image"):
            dpg.configure_item("summary_image", texture_tag="summary_texture")
        else:
            dpg.add_image("summary_texture", parent="chart_group", tag="summary_image")
        
        update_status(f"SKU summary generated ({grouping})", success=True)
        
    except Exception as e:
        update_status(f"Summary error: {str(e)}", error=True)


def chart_grouping_changed_callback(sender, app_data):
    """
    handle chart grouping change
    """
    print(f"chart grouping changed to: {app_data}")
    # Auto-refresh chart when grouping changes
    if STATE.forecast_data is not None:
        refresh_chart_callback()