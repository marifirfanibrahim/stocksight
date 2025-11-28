"""
controls tab interface
forecast and data controls
"""


# ================ IMPORTS ================

import dearpygui.dearpygui as dpg

from config import Paths, GUIConfig, AutoTSConfig, DataConfig


# ================ CONTROLS TAB ================

def create_controls_tab():
    """
    create controls tab content
    """
    with dpg.tab(label="Controls"):
        dpg.add_spacer(height=5)
        
        # ---------- DATA SECTION ----------
        dpg.add_text("DATA", color=GUIConfig.HEADER_COLOR)
        dpg.add_separator()
        
        from ui.callbacks import upload_callback, reset_data_callback, remove_data_callback
        
        upload_btn = dpg.add_button(label="Upload CSV", callback=upload_callback, width=-1)
        dpg.bind_item_theme(upload_btn, "upload_button_theme")
        
        dpg.add_spacer(height=5)
        
        remove_btn = dpg.add_button(label="Remove Data", callback=remove_data_callback, width=-1)
        dpg.bind_item_theme(remove_btn, "danger_button_theme")
        
        dpg.add_button(label="Reset Data", callback=reset_data_callback, width=-1)
        
        dpg.add_spacer(height=15)
        
        # ---------- OUTPUT LOCATION ----------
        dpg.add_text("OUTPUT", color=GUIConfig.HEADER_COLOR)
        dpg.add_separator()
        
        default_output = str(Paths.USER_OUTPUT)
        dpg.add_text(f"{default_output}", tag="output_dir_text", 
                    wrap=350, color=(200, 200, 200))
        
        from ui.callbacks import select_output_directory_callback
        dpg.add_button(label="Change Output Folder", 
                      callback=select_output_directory_callback, width=-1)
        
        dpg.add_spacer(height=15)
        
        # ---------- FORECAST SECTION ----------
        dpg.add_text("FORECAST", color=GUIConfig.HEADER_COLOR)
        dpg.add_separator()
        
        # forecast days - label on top
        dpg.add_text("Forecast Days:", color=(200, 200, 200))
        
        from ui.callbacks import forecast_days_callback
        dpg.add_input_int(default_value=AutoTSConfig.DEFAULT_FORECAST_DAYS, 
                          min_value=AutoTSConfig.MIN_FORECAST_DAYS, 
                          max_value=AutoTSConfig.MAX_FORECAST_DAYS,
                          callback=forecast_days_callback, 
                          tag="forecast_days", 
                          width=-1)
        dpg.add_text("Number of days to predict into the future", 
                    wrap=350, color=(150, 150, 150))
        
        dpg.add_spacer(height=10)
        
        # granularity - label on top
        dpg.add_text("Forecast Granularity:", color=(200, 200, 200))
        
        from ui.callbacks import forecast_granularity_callback
        dpg.add_combo(DataConfig.GROUP_OPTIONS, 
                     default_value="Daily", 
                     tag="forecast_granularity_combo",
                     callback=forecast_granularity_callback,
                     width=-1)
        dpg.add_text("Daily = best accuracy, Weekly/Monthly = less noise", 
                    wrap=350, color=(150, 150, 150))
        
        dpg.add_spacer(height=10)
        
        from ui.callbacks import forecast_callback
        forecast_btn = dpg.add_button(label="Run Forecast", callback=forecast_callback, width=-1, height=40)
        dpg.bind_item_theme(forecast_btn, "forecast_button_theme")
        
        dpg.add_text("Generate forecast for all SKUs", 
                    wrap=350, color=(150, 150, 150))
        
        dpg.add_spacer(height=15)
        
        # ---------- FEATURES SECTION ----------
        with dpg.collapsing_header(label="Advanced Features", default_open=False):
            dpg.add_checkbox(label="Use Additional Columns", 
                            default_value=False, tag="use_features_checkbox")
            
            dpg.add_spacer(height=5)
            
            dpg.add_text("Detected Features:", color=(200, 200, 200))
            with dpg.group(tag="features_group"):
                dpg.add_text("Load data to see features", color=(150, 150, 150))
            
            dpg.add_spacer(height=5)
            
            dpg.add_text("Seasonality Info:", color=(200, 200, 200))
            dpg.add_text("Load data to analyze seasonality", 
                        tag="seasonality_text", wrap=350, color=(150, 150, 150))
        
        dpg.add_spacer(height=20)
        
        # ---------- EXPORT SECTION ----------
        dpg.add_text("EXPORT", color=GUIConfig.HEADER_COLOR)
        dpg.add_separator()
        
        from ui.callbacks import export_callback
        export_btn = dpg.add_button(label="Export Results", callback=export_callback, width=-1)
        dpg.bind_item_theme(export_btn, "export_button_theme")
        
        dpg.add_text("Save forecast, confidence intervals, and charts", 
                    wrap=350, color=(150, 150, 150))