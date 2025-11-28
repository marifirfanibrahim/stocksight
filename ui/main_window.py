"""
main window setup
create gui structure
"""


# ================ IMPORTS ================

import dearpygui.dearpygui as dpg

from config import Paths, GUIConfig, DataConfig, AutoTSConfig, ScenarioConfig
from .themes import create_all_themes
from .column_mapper import create_column_mapping_dialog
from . import callbacks


# ================ UI HELPER FUNCTIONS ================

def _create_controls_tab_content():
    """
    create content for controls tab
    """
    dpg.add_spacer(height=5)
    
    # ---------- DATA SECTION ----------
    dpg.add_text("DATA", color=GUIConfig.HEADER_COLOR)
    dpg.add_separator()
    
    upload_btn = dpg.add_button(label="Upload CSV/Excel", callback=callbacks.upload_callback, width=-1)
    dpg.bind_item_theme(upload_btn, "upload_button_theme")
    
    dpg.add_spacer(height=5)
    
    remap_btn = dpg.add_button(label="Remap Columns", callback=callbacks.remap_columns_callback, width=-1)
    dpg.bind_item_theme(remap_btn, "export_button_theme")
    
    dpg.add_spacer(height=5)
    
    remove_btn = dpg.add_button(label="Remove Data", callback=callbacks.remove_data_callback, width=-1)
    dpg.bind_item_theme(remove_btn, "danger_button_theme")
    
    dpg.add_spacer(height=10)
    
    # ---------- SEASONALITY INFO ----------
    dpg.add_text("SEASONALITY", color=GUIConfig.HEADER_COLOR)
    dpg.add_separator()
    dpg.add_text("No data analyzed", tag="seasonality_info_text", color=(150, 150, 150), wrap=280)
    
    dpg.add_spacer(height=15)
    
    # ---------- FORECAST SECTION ----------
    dpg.add_text("FORECAST", color=GUIConfig.HEADER_COLOR)
    dpg.add_separator()
    
    dpg.add_text("Days:")
    dpg.add_input_int(default_value=AutoTSConfig.DEFAULT_FORECAST_DAYS, 
                      min_value=AutoTSConfig.MIN_FORECAST_DAYS, 
                      max_value=365,
                      min_clamped=True,
                      max_clamped=True,
                      callback=callbacks.forecast_days_callback, 
                      tag="forecast_days", width=-1)
    
    dpg.add_text("Granularity:")
    dpg.add_combo(DataConfig.GROUP_OPTIONS, default_value="Daily", 
                  tag="forecast_granularity_combo", 
                  callback=callbacks.forecast_granularity_callback, width=-1)
    
    dpg.add_spacer(height=10)
    
    # forecast button
    forecast_btn = dpg.add_button(label="Run Forecast", tag="forecast_btn",
                                  callback=callbacks.forecast_callback, 
                                  width=-1, height=40)
    dpg.bind_item_theme(forecast_btn, "forecast_button_theme")
    
    dpg.add_spacer(height=15)
    
    # ---------- MODEL SECTION ----------
    dpg.add_text("MODEL", color=GUIConfig.HEADER_COLOR)
    dpg.add_separator()
    
    dpg.add_text("No model loaded", tag="loaded_model_text", color=(150, 150, 150))
    
    with dpg.group(horizontal=True):
        dpg.add_button(label="Load Model", callback=callbacks.load_model_callback, width=100)
        
        use_model_btn = dpg.add_button(label="Use Model", tag="use_model_btn",
                                       callback=callbacks.forecast_with_model_callback, 
                                       width=100, show=False)
        dpg.bind_item_theme(use_model_btn, "forecast_button_theme")
    
    dpg.add_spacer(height=15)
    
    # ---------- EXPORT SECTION ----------
    dpg.add_text("EXPORT", color=GUIConfig.HEADER_COLOR)
    dpg.add_separator()
    
    dpg.add_text("Directory:", color=(150, 150, 150))
    dpg.add_input_text(default_value=str(Paths.USER_OUTPUT), tag="export_dir_text", 
                       width=-1, readonly=True)
    
    with dpg.group(horizontal=True):
        dpg.add_button(label="Browse", callback=callbacks.select_export_dir_callback, width=70)
        dpg.add_button(label="Reset", callback=callbacks.reset_export_dir_callback, width=70)
    
    dpg.add_spacer(height=5)
    
    with dpg.group(horizontal=True):
        export_btn = dpg.add_button(label="Export", callback=callbacks.export_callback, width=70)
        dpg.bind_item_theme(export_btn, "export_button_theme")
        
        model_btn = dpg.add_button(label="Save Model", callback=callbacks.export_model_callback, width=85)
        dpg.bind_item_theme(model_btn, "export_button_theme")
        

def _create_scenarios_tab_content():
    """
    create content for scenarios tab
    """
    dpg.add_spacer(height=5)
    
    dpg.add_text("SCENARIO", color=GUIConfig.HEADER_COLOR)
    dpg.add_separator()
    
    dpg.add_text("Type:")
    scenario_combo = dpg.add_combo(["Demand Spike", "Supply Delay"], default_value="Demand Spike", 
                                   tag="scenario_type", width=-1, 
                                   callback=callbacks.scenario_type_changed_callback)
    
    with dpg.tooltip(scenario_combo):
        dpg.add_text("Demand Spike:", color=GUIConfig.HEADER_COLOR)
        dpg.add_text("Multiply demand by factor.\nUse >1 for increase, <1 for decrease.", wrap=220)
        dpg.add_spacer(height=5)
        dpg.add_text("Supply Delay:", color=GUIConfig.HEADER_COLOR)
        dpg.add_text("Shift quantities forward.\nSimulates delayed shipments.", wrap=220)
    
    dpg.add_spacer(height=10)
    
    dpg.add_text("Target SKU:")
    dpg.add_combo([], tag="scenario_sku", width=-1)
    
    dpg.add_spacer(height=10)
    
    dpg.add_text("PARAMETERS", color=GUIConfig.HEADER_COLOR)
    dpg.add_separator()
    
    with dpg.group(tag="spike_multiplier_group", show=True):
        dpg.add_text("Multiplier:")
        multiplier_slider = dpg.add_slider_float(default_value=ScenarioConfig.DEFAULT_SPIKE_MULTIPLIER,
                                                  min_value=ScenarioConfig.MIN_SPIKE_MULTIPLIER,
                                                  max_value=ScenarioConfig.MAX_SPIKE_MULTIPLIER,
                                                  tag="spike_multiplier", width=-1, format="%.1fx")
        with dpg.tooltip(multiplier_slider):
            dpg.add_text("1.0 = no change\n1.5 = 50% increase\n2.0 = double\n0.5 = 50% decrease")
    
    with dpg.group(tag="delay_days_group", show=False):
        dpg.add_text("Delay Days:")
        delay_slider = dpg.add_slider_int(default_value=ScenarioConfig.DEFAULT_DELAY_DAYS,
                                           min_value=ScenarioConfig.MIN_DELAY_DAYS,
                                           max_value=ScenarioConfig.MAX_DELAY_DAYS,
                                           tag="delay_days", width=-1)
        with dpg.tooltip(delay_slider):
            dpg.add_text("Days to shift forecast forward")
    
    dpg.add_spacer(height=10)
    
    dpg.add_text("DATE RANGE", color=GUIConfig.HEADER_COLOR)
    dpg.add_separator()
    
    with dpg.group(horizontal=True):
        dpg.add_button(label="Week", callback=callbacks.set_date_this_week, width=55)
        dpg.add_button(label="Month", callback=callbacks.set_date_this_month, width=55)
        dpg.add_button(label="Next", callback=callbacks.set_date_next_month, width=55)
    
    dpg.add_spacer(height=5)
    
    dpg.add_text("Start:", color=(150, 150, 150))
    dpg.add_date_picker(tag="scenario_start_date", default_value={
        'year': 124, 'month': 0, 'month_day': 1
    })
    
    dpg.add_text("End:", color=(150, 150, 150))
    dpg.add_date_picker(tag="scenario_end_date", default_value={
        'year': 124, 'month': 0, 'month_day': 31
    })
    
    dpg.add_spacer(height=10)
    
    with dpg.group(horizontal=True):
        apply_btn = dpg.add_button(label="Apply", 
                                   callback=callbacks.apply_scenario_callback, 
                                   width=80, height=30)
        dpg.bind_item_theme(apply_btn, "apply_scenario_theme")
        
        dpg.add_spacer(width=5)
        
        reset_btn = dpg.add_button(label="Reset All", 
                                   callback=callbacks.reset_all_scenarios_callback, 
                                   width=80, height=30)
        dpg.bind_item_theme(reset_btn, "reset_scenario_theme")


def _create_chart_tab_content():
    """
    create content for chart tab
    """
    with dpg.group(horizontal=True):
        dpg.add_text("Grouping:")
        dpg.add_combo(DataConfig.GROUP_OPTIONS, default_value="Daily",
                      tag="chart_grouping_combo", width=90,
                      callback=callbacks.chart_grouping_changed_callback)
        
        dpg.add_spacer(width=10)
        
        dpg.add_text("SKU:")
        dpg.add_combo(["All SKUs"], default_value="All SKUs",
                      tag="chart_sku_combo", width=120,
                      callback=callbacks.chart_sku_changed_callback)
        
        dpg.add_spacer(width=10)
        
        summary_btn = dpg.add_button(label="Show Summary", tag="summary_toggle_btn",
                                     callback=callbacks.toggle_summary_callback,
                                     width=100)
        dpg.bind_item_theme(summary_btn, "summary_chart_theme")
        
        dpg.add_spacer(width=10)
        
        zoom_btn = dpg.add_button(label="Zoom Chart", callback=callbacks.zoom_chart_callback)
        dpg.bind_item_theme(zoom_btn, "export_button_theme")

    dpg.add_separator()
    dpg.add_spacer(height=5)
    
    with dpg.child_window(border=False, horizontal_scrollbar=True):
        with dpg.group(tag="chart_image_group"):
            dpg.add_text("Run forecast to see chart.", color=(150, 150, 150))
        
        with dpg.group(tag="summary_container", show=False):
            dpg.add_spacer(height=10)
            dpg.add_separator()
            dpg.add_text("SKU SUMMARY", color=GUIConfig.HEADER_COLOR)
            with dpg.group(tag="summary_image_group"):
                pass


def _create_dashboard_tab_content():
    """
    create content for dashboard tab
    """
    dpg.add_spacer(height=5)
    
    # ---------- CONTROLS ----------
    with dpg.group(horizontal=True):
        dpg.add_text("Grouping:")
        dpg.add_combo(DataConfig.GROUP_OPTIONS, default_value="Daily",
                      tag="dashboard_grouping_combo", width=90,
                      callback=callbacks.grouping_changed_callback)
        
        dpg.add_spacer(width=10)
        
        dpg.add_text("SKU:")
        dpg.add_combo(["All SKUs"], default_value="All SKUs",
                      tag="dashboard_sku_combo", width=120,
                      callback=callbacks.dashboard_sku_changed_callback)
        
        dpg.add_spacer(width=10)
        
        refresh_btn = dpg.add_button(label="Refresh", 
                                     callback=callbacks.update_dashboard_callback,
                                     width=70)
        dpg.bind_item_theme(refresh_btn, "refresh_chart_theme")
        
        dpg.add_spacer(width=10)
        
        seasonality_btn = dpg.add_button(label="Seasonality", 
                                         callback=callbacks.show_seasonality_chart_callback,
                                         width=80)
        dpg.bind_item_theme(seasonality_btn, "summary_chart_theme")
        
        dpg.add_spacer(width=10)
        
        diagnostics_btn = dpg.add_button(label="SKU Report", 
                                         callback=callbacks.show_forecast_diagnostics_callback,
                                         width=80)
        dpg.bind_item_theme(diagnostics_btn, "export_button_theme")
    
    # ---------- STATISTICS ----------
    dpg.add_text("STATISTICS", color=GUIConfig.HEADER_COLOR)
    dpg.add_separator()
    dpg.add_spacer(height=5)
    
    with dpg.group(horizontal=True):
        with dpg.child_window(width=180, height=50, border=False):
            dpg.add_text("Total Forecast", color=(180, 180, 180))
            stat1 = dpg.add_text("--", tag="stat_total_forecast", wrap=170)
            dpg.bind_item_font(stat1, "stat_font")
            
        with dpg.child_window(width=180, height=50, border=False):
            dpg.add_text("Avg Daily", color=(180, 180, 180))
            stat2 = dpg.add_text("--", tag="stat_avg_daily", wrap=170)
            dpg.bind_item_font(stat2, "stat_font")
            
        with dpg.child_window(width=120, height=50, border=False):
            dpg.add_text("Periods", color=(180, 180, 180))
            stat3 = dpg.add_text("--", tag="stat_num_periods")
            dpg.bind_item_font(stat3, "stat_font")
        
        with dpg.child_window(width=120, height=50, border=False):
            dpg.add_text("SKUs", color=(180, 180, 180))
            stat4 = dpg.add_text("--", tag="stat_num_skus")
            dpg.bind_item_font(stat4, "stat_font")
    
    dpg.add_spacer(height=5)
    
    with dpg.group(horizontal=True):
        with dpg.child_window(width=220, height=50, border=False):
            dpg.add_text("Date Range", color=(180, 180, 180))
            dpg.add_text("--", tag="stat_date_range", wrap=210)
        
        with dpg.child_window(width=200, height=50, border=False):
            dpg.add_text("95% Confidence", color=(180, 180, 180))
            dpg.add_text("--", tag="stat_confidence", wrap=190)
        
        with dpg.child_window(width=180, height=50, border=False):
            dpg.add_text("Avg Error", color=(180, 180, 180))
            stat5 = dpg.add_text("--", tag="stat_error_pct", wrap=170)
            dpg.bind_item_font(stat5, "stat_font")
    
    dpg.add_spacer(height=10)
    
    # ---------- SEASONALITY CHART CONTAINER ----------
    with dpg.group(tag="seasonality_chart_container", show=False):
        dpg.add_text("SEASONALITY PATTERN", color=GUIConfig.HEADER_COLOR)
        dpg.add_separator()
        with dpg.group(tag="seasonality_chart_group"):
            pass
        dpg.add_button(label="Hide", callback=callbacks.hide_seasonality_chart, width=60)
        dpg.add_spacer(height=10)
    
    # ---------- FORECAST TABLE ----------
    dpg.add_text("FORECAST BY PERIOD", color=GUIConfig.HEADER_COLOR)
    dpg.add_separator()
    dpg.add_spacer(height=5)
    
    with dpg.group(tag="dashboard_table_group"):
        dpg.add_text("Run forecast to see data.", color=(150, 150, 150))


# ================ MAIN GUI FUNCTION ================

def create_gui():
    """
    build and run dear pygui interface
    """
    dpg.create_context()
    
    create_all_themes()
    create_column_mapping_dialog()
    
    # ---------- FILE DIALOG ----------
    with dpg.file_dialog(show=False, callback=callbacks.load_file_callback, 
                         cancel_callback=callbacks.cancel_load_callback, 
                         tag="file_dialog", width=700, height=400):
        dpg.add_file_extension(".csv", color=(100, 255, 100, 255), custom_text="[CSV]")
        dpg.add_file_extension(".xlsx", color=(100, 200, 255, 255), custom_text="[Excel]")
        dpg.add_file_extension(".xls", color=(100, 200, 255, 255), custom_text="[Excel]")
        dpg.add_file_extension(".*", color=(150, 150, 150, 255))
    
    # ---------- FOLDER DIALOG ----------
    with dpg.file_dialog(show=False, callback=callbacks.folder_selected_callback,
                         cancel_callback=callbacks.folder_cancel_callback,
                         tag="folder_dialog", width=700, height=400,
                         directory_selector=True):
        pass
    
    # ---------- MODEL FILE DIALOG ----------
    with dpg.file_dialog(show=False, callback=callbacks.load_model_file_callback,
                         cancel_callback=callbacks.cancel_load_callback,
                         tag="model_file_dialog", width=700, height=400):
        dpg.add_file_extension(".pkl", color=(100, 255, 100, 255), custom_text="[Model]")
        dpg.add_file_extension(".*", color=(150, 150, 150, 255))
    
    # ---------- MAIN WINDOW ----------
    with dpg.window(label="Inventory Forecast", tag="main_window"):
        
        # ---------- MENU BAR ----------
        with dpg.menu_bar():
            with dpg.menu(label="File"):
                dpg.add_menu_item(label="Upload CSV/Excel", callback=callbacks.upload_callback)
                dpg.add_menu_item(label="Load Model", callback=callbacks.load_model_callback)
                dpg.add_separator()
                dpg.add_menu_item(label="Set Export Directory", callback=callbacks.select_export_dir_callback)
                dpg.add_menu_item(label="Export Results", callback=callbacks.export_callback)
                dpg.add_menu_item(label="Export Model", callback=callbacks.export_model_callback)
                dpg.add_separator()
                dpg.add_menu_item(label="Exit", callback=lambda: dpg.stop_dearpygui())
            
            with dpg.menu(label="View"):
                dpg.add_menu_item(label="Zoom Chart", callback=callbacks.zoom_chart_callback)
                dpg.add_menu_item(label="Toggle Summary", callback=callbacks.toggle_summary_callback)
                dpg.add_menu_item(label="Seasonality Chart", callback=callbacks.show_seasonality_chart_callback)
                dpg.add_menu_item(label="Refresh Dashboard", callback=callbacks.update_dashboard_callback)
                dpg.add_separator()
                dpg.add_menu_item(label="SKU Diagnostics", callback=callbacks.show_forecast_diagnostics_callback)
        
        # ---------- MAIN LAYOUT ----------
        with dpg.group(horizontal=True):
            
            # ---------- LEFT PANEL ----------
            with dpg.child_window(width=GUIConfig.LEFT_PANEL_WIDTH, height=-30):
                with dpg.tab_bar():
                    with dpg.tab(label="Controls"):
                        _create_controls_tab_content()
                    with dpg.tab(label="Scenarios"):
                        _create_scenarios_tab_content()
            
            # ---------- RIGHT PANEL ----------
            with dpg.child_window(width=-1, height=-30):
                with dpg.tab_bar():
                    with dpg.tab(label="Data Preview"):
                        with dpg.child_window(border=False, horizontal_scrollbar=True):
                            dpg.add_group(tag="preview_group")
                            dpg.add_text("Load a CSV or Excel file to see data preview.", parent="preview_group")
                    
                    with dpg.tab(label="Forecast Chart"):
                        with dpg.group(tag="chart_group"):
                            _create_chart_tab_content()
                    
                    with dpg.tab(label="Dashboard"):
                        with dpg.child_window(border=False):
                            _create_dashboard_tab_content()
        
        # ---------- STATUS BAR ----------
        with dpg.child_window(height=25, no_scrollbar=True):
            with dpg.group(horizontal=True):
                dpg.add_text("Ready", tag="status_text")
                dpg.add_spacer(width=20)
                dpg.add_text("", tag="data_info_text")
                dpg.add_spacer(width=20)
                dpg.add_text("", tag="column_mapping_text", color=(100, 255, 100))
    
    # ---------- VIEWPORT SETUP ----------
    dpg.create_viewport(title=GUIConfig.WINDOW_TITLE, 
                        width=GUIConfig.WINDOW_WIDTH, 
                        height=GUIConfig.WINDOW_HEIGHT)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main_window", True)
    
    dpg.start_dearpygui()
    
    dpg.destroy_context()