"""
main window setup
create gui structure
"""


# ================ IMPORTS ================

import dearpygui.dearpygui as dpg

from config import Paths, GUIConfig, DataConfig
from ui.themes import create_all_themes
from ui.controls_tab import create_controls_tab
from ui.scenarios_tab import create_scenarios_tab
from ui.dashboard_tab import create_dashboard_tab


# ================ GUI SETUP ================

def create_gui():
    """
    build dear pygui interface
    setup all windows and widgets
    """
    # ---------- CONTEXT ----------
    dpg.create_context()
    
    # ---------- CREATE ALL THEMES FIRST ----------
    create_all_themes()
    
    # ---------- FILE DIALOG ----------
    from ui.callbacks import load_csv_callback, cancel_callback, output_dir_callback
    
    with dpg.file_dialog(directory_selector=False, show=False,
                         callback=load_csv_callback, cancel_callback=cancel_callback,
                         tag="file_dialog", width=700, height=400):
        dpg.add_file_extension(".csv", color=(0, 255, 0, 255))
    
    # ---------- OUTPUT DIRECTORY DIALOG ----------
    with dpg.file_dialog(directory_selector=True, show=False,
                         callback=output_dir_callback, cancel_callback=cancel_callback,
                         tag="output_dir_dialog", width=700, height=400):
        pass
    
    # ---------- MAIN WINDOW ----------
    with dpg.window(label="Inventory Forecast", tag="main_window"):
        
        # ---------- MENU BAR ----------
        from ui.callbacks import (
            upload_callback, 
            select_output_directory_callback, 
            reset_output_directory_callback,
            export_callback
        )
        
        with dpg.menu_bar():
            with dpg.menu(label="File"):
                dpg.add_menu_item(label="Upload CSV", callback=upload_callback)
                dpg.add_menu_item(label="Select Output Folder", callback=select_output_directory_callback)
                dpg.add_menu_item(label="Reset Output Folder", callback=reset_output_directory_callback)
                dpg.add_separator()
                dpg.add_menu_item(label="Export Results", callback=export_callback)
                dpg.add_separator()
                dpg.add_menu_item(label="Exit", callback=lambda: dpg.stop_dearpygui())
        
        # ---------- CONTROL PANEL ----------
        with dpg.group(horizontal=True):
            
            # ---------- LEFT PANEL ----------
            with dpg.child_window(width=GUIConfig.LEFT_PANEL_WIDTH, height=-30):
                
                # ---------- TAB BAR FOR CONTROLS ----------
                with dpg.tab_bar():
                    create_controls_tab()
                    create_scenarios_tab()
            
            # ---------- RIGHT PANEL ----------
            with dpg.child_window(width=-1, height=-30):
                
                # ---------- TABS (REORDERED) ----------
                with dpg.tab_bar():
                    
                    # ---------- 1. DATA PREVIEW TAB (FIRST) ----------
                    with dpg.tab(label="Data Preview"):
                        dpg.add_spacer(height=10)
                        with dpg.group(tag="preview_group"):
                            dpg.add_text("Load a CSV file to preview data")
                    
                    # ---------- 2. FORECAST CHART TAB ----------
                    with dpg.tab(label="Forecast Chart"):
                        dpg.add_spacer(height=10)
                        
                        # ---------- CHART CONTROLS ----------
                        from ui.callbacks import (
                            refresh_chart_callback, 
                            generate_sku_summary_callback,
                            chart_grouping_changed_callback
                        )
                        
                        with dpg.group(horizontal=True):
                            dpg.add_text("Group By:")
                            dpg.add_combo(DataConfig.GROUP_OPTIONS, 
                                         default_value="Daily", 
                                         tag="chart_grouping_combo",
                                         callback=chart_grouping_changed_callback,
                                         width=150)
                            
                            dpg.add_spacer(width=20)
                            
                            refresh_btn = dpg.add_button(label="Refresh Chart", 
                                          callback=refresh_chart_callback,
                                          width=120)
                            dpg.bind_item_theme(refresh_btn, "refresh_chart_theme")
                            
                            dpg.add_spacer(width=10)
                            
                            summary_btn = dpg.add_button(label="SKU Summary", 
                                          callback=generate_sku_summary_callback,
                                          width=120)
                            dpg.bind_item_theme(summary_btn, "summary_chart_theme")
                        
                        dpg.add_spacer(height=5)
                        dpg.add_separator()
                        dpg.add_spacer(height=10)
                        
                        # ---------- CHART DISPLAY ----------
                        with dpg.group(tag="chart_group"):
                            dpg.add_text("Run forecast to view chart with 95% confidence intervals")
                    
                    # ---------- 3. DASHBOARD TAB (LAST) ----------
                    create_dashboard_tab()
        
        # ---------- STATUS BAR ----------
        dpg.add_text("Ready", tag="status_text", color=GUIConfig.STATUS_COLOR)
    
    # ---------- CONFIGURE VIEWPORT ----------
    dpg.create_viewport(title=GUIConfig.WINDOW_TITLE, 
                       width=GUIConfig.WINDOW_WIDTH, 
                       height=GUIConfig.WINDOW_HEIGHT)
    dpg.setup_dearpygui()
    dpg.set_primary_window("main_window", True)