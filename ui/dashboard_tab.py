"""
dashboard tab interface
show forecast numbers with error margins
grouped data views
"""


# ================ IMPORTS ================

import dearpygui.dearpygui as dpg
from config import GUIConfig, DataConfig


# ================ DASHBOARD TAB ================

def create_dashboard_tab():
    """
    create dashboard tab content
    """
    with dpg.tab(label="Dashboard"):
        dpg.add_spacer(height=10)
        
        # ---------- HEADER ----------
        dpg.add_text("FORECAST DASHBOARD", color=GUIConfig.HEADER_COLOR)
        dpg.add_separator()
        
        dpg.add_spacer(height=10)
        
        # ---------- CONTROLS ROW ----------
        from ui.callbacks import update_dashboard_callback, grouping_changed_callback
        
        with dpg.group(horizontal=True):
            dpg.add_text("Group By:")
            dpg.add_combo(DataConfig.GROUP_OPTIONS, 
                         default_value="Daily", 
                         tag="grouping_combo",
                         callback=grouping_changed_callback,
                         width=150)
            
            dpg.add_spacer(width=20)
            
            dpg.add_button(label="Refresh Dashboard", 
                          callback=update_dashboard_callback,
                          width=150)
        
        dpg.add_spacer(height=10)
        dpg.add_separator()
        dpg.add_spacer(height=10)
        
        # ---------- SUMMARY STATS ----------
        dpg.add_text("SUMMARY STATISTICS", color=GUIConfig.HEADER_COLOR)
        dpg.add_separator()
        
        with dpg.group(horizontal=True):
            with dpg.child_window(width=280, height=120, border=True):
                dpg.add_text("Total Forecast", color=(200, 200, 200))
                dpg.add_text("--", tag="total_forecast_text", color=GUIConfig.SUCCESS_COLOR)
                dpg.add_spacer(height=5)
                dpg.add_text("Average Daily", color=(200, 200, 200))
                dpg.add_text("--", tag="avg_daily_text", color=(200, 200, 200))
            
            dpg.add_spacer(width=10)
            
            with dpg.child_window(width=280, height=120, border=True):
                dpg.add_text("Confidence Range", color=(200, 200, 200))
                dpg.add_text("--", tag="confidence_range_text", color=GUIConfig.WARNING_COLOR)
                dpg.add_spacer(height=5)
                dpg.add_text("Average Error Margin", color=(200, 200, 200))
                dpg.add_text("--", tag="avg_error_text", color=(200, 200, 200))
            
            dpg.add_spacer(width=10)
            
            with dpg.child_window(width=280, height=120, border=True):
                dpg.add_text("Forecast Period", color=(200, 200, 200))
                dpg.add_text("--", tag="forecast_period_text", color=(200, 200, 200))
                dpg.add_spacer(height=5)
                dpg.add_text("Number of SKUs", color=(200, 200, 200))
                dpg.add_text("--", tag="num_skus_text", color=(200, 200, 200))
        
        dpg.add_spacer(height=20)
        
        # ---------- FORECAST TABLE ----------
        dpg.add_text("FORECAST DETAILS (± Error Margin)", color=GUIConfig.HEADER_COLOR)
        dpg.add_separator()
        
        dpg.add_text("Run forecast to see details", tag="dashboard_status_text", 
                    color=(150, 150, 150))
        
        dpg.add_spacer(height=10)
        
        with dpg.group(tag="dashboard_table_group"):
            pass
        
        dpg.add_spacer(height=20)
        
        # ---------- SKU BREAKDOWN ----------
        dpg.add_text("SKU BREAKDOWN", color=GUIConfig.HEADER_COLOR)
        dpg.add_separator()
        
        with dpg.group(tag="sku_breakdown_group"):
            dpg.add_text("Run forecast to see SKU breakdown", color=(150, 150, 150))