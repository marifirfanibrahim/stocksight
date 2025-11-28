"""
inventory forecasting application
main entry point
"""


# ================ IMPORTS ================

import dearpygui.dearpygui as dpg
from pathlib import Path
import os

from config import Paths
from core.state import STATE
from ui.main_window import create_gui
from ui.callbacks import update_scenario_sku_dropdown


# ================ DIRECTORY SETUP ================

def ensure_directories():
    """
    create required directories
    data and output folders
    """
    os.makedirs(Paths.DATA_DIR, exist_ok=True)
    os.makedirs(Paths.OUTPUT_DIR, exist_ok=True)
    os.makedirs(Paths.USER_OUTPUT, exist_ok=True)


# ================ MAIN ENTRY ================

def main():
    """
    application entry point
    initialize and run gui
    """
    print("starting syamsulai inventory forecast")
    
    # ---------- SETUP ----------
    ensure_directories()
    create_gui()
    
    print("gui initialized")
    print(f"default output: {Paths.USER_OUTPUT}")
    
    # ---------- RUN LOOP ----------
    dpg.show_viewport()
    
    while dpg.is_dearpygui_running():
        # ---------- SYNC DROPDOWNS ----------
        if STATE.sku_list and not dpg.get_value("scenario_sku"):
            update_scenario_sku_dropdown()
        
        dpg.render_dearpygui_frame()
    
    # ---------- CLEANUP ----------
    dpg.destroy_context()
    print("application closed")


if __name__ == "__main__":
    main()