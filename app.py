"""
stocksight inventory forecasting application
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


# ================ MAIN ================

def main():
    """
    application entry point
    """
    try:
        write_log("Starting Stocksight...")
        
        # Setup directories
        write_log("Importing config...")
        from config import Paths
        
        os.makedirs(Paths.DATA_DIR, exist_ok=True)
        os.makedirs(Paths.OUTPUT_DIR, exist_ok=True)
        os.makedirs(Paths.USER_OUTPUT, exist_ok=True)
        
        write_log("Importing tkinter...")
        import tkinter as tk
        
        write_log("Importing main window...")
        from ui.main_window import StocksightApp
        
        write_log("Creating application...")
        root = tk.Tk()
        app = StocksightApp(root)
        
        write_log("Starting main loop...")
        root.mainloop()
        
        write_log("Application closed normally")
        
    except Exception as e:
        error_msg = f"ERROR: {e}\n\n{traceback.format_exc()}"
        write_log(error_msg)
        print(f"FATAL ERROR: {e}")
        
        # Show error dialog
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Stocksight Error", 
                                f"Application crashed:\n\n{str(e)[:500]}\n\nSee crash_log.txt")
            root.destroy()
        except:
            pass
        
        sys.exit(1)


if __name__ == "__main__":
    main()