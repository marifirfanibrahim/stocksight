"""
inventory forecasting application
main entry point with crash logging
"""


# ================ IMPORTS ================

import sys
import os
import traceback
from pathlib import Path
from datetime import datetime


# ================ CRASH LOGGING ================

def get_log_path():
    """
    get path for crash log file
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent / "crash_log.txt"
    else:
        return Path(__file__).parent / "crash_log.txt"


def write_log(message):
    """
    write message to crash log
    """
    log_path = get_log_path()
    with open(log_path, 'a') as f:
        f.write(f"\n{'='*50}\n")
        f.write(f"TIME: {datetime.now()}\n")
        f.write(f"{'='*50}\n")
        f.write(message)
        f.write("\n")


# ================ MAIN ENTRY ================

def main():
    """
    application entry point
    initialize and run gui
    """
    try:
        write_log("Starting application...")
        
        write_log("Importing config...")
        from config import Paths
        
        write_log("Importing dearpygui...")
        import dearpygui.dearpygui as dpg
        
        write_log("Importing ui...")
        from ui.main_window import create_gui
        
        write_log("Creating directories...")
        os.makedirs(Paths.DATA_DIR, exist_ok=True)
        os.makedirs(Paths.OUTPUT_DIR, exist_ok=True)
        os.makedirs(Paths.USER_OUTPUT, exist_ok=True)
        
        write_log("Starting GUI...")
        print("starting stocksight inventory forecast")
        
        create_gui()
        
        print("application closed")
        write_log("Application closed normally")
        
    except Exception as e:
        error_msg = f"ERROR: {e}\n\n{traceback.format_exc()}"
        write_log(error_msg)
        print(f"FATAL ERROR: {e}")
        
        # show message box on windows
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Application crashed:\n\n{str(e)[:500]}\n\nSee crash_log.txt for details",
                "Stocksight Error",
                0x10
            )
        except:
            pass
        
        sys.exit(1)


if __name__ == "__main__":
    main()