"""
inventory forecasting application
main entry point
"""


# ================ IMPORTS ================

import os
from config import Paths
from ui.main_window import create_gui


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
    print("starting stocksight inventory forecast")
    
    # ---------- SETUP ----------
    ensure_directories()
    
    # ---------- CREATE AND RUN GUI ----------
    create_gui()
    
    print("application closed")


if __name__ == "__main__":
    main()