"""
stocksight inventory forecasting application
pyqt6 main entry point
"""


# ================ IMPORTS ================

import sys
import os
import traceback
from pathlib import Path
from datetime import datetime


# ================ PATH SETUP ================

if getattr(sys, 'frozen', False):
    # running as compiled
    APP_DIR = Path(sys.executable).parent
else:
    # running as script
    APP_DIR = Path(__file__).parent

sys.path.insert(0, str(APP_DIR))


# ================ CRASH LOGGING ================

def get_log_path() -> Path:
    """
    get path for crash log file
    """
    return APP_DIR / "crash_log.txt"


def write_log(message: str):
    """
    write message to crash log
    """
    log_path = get_log_path()
    try:
        with open(log_path, 'a') as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"TIME: {datetime.now()}\n")
            f.write(f"{'='*50}\n")
            f.write(message)
            f.write("\n")
    except Exception:
        pass


# ================ DEPENDENCY CHECK ================

def check_dependencies() -> tuple:
    """
    check required dependencies
    returns success status and message
    """
    missing = []
    
    # core dependencies
    required = [
        ('PyQt6', 'PyQt6'),
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
        ('matplotlib', 'matplotlib'),
    ]
    
    # optional but recommended
    optional = [
        ('autots', 'AutoTS'),
        ('ydata_profiling', 'YData Profiling'),
        ('autoviz', 'AutoViz'),
        ('tsfresh', 'TSFresh'),
        ('featuretools', 'Featuretools'),
    ]
    
    for module, name in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(name)
    
    if missing:
        return False, f"Missing required packages: {', '.join(missing)}"
    
    # check optional
    optional_missing = []
    for module, name in optional:
        try:
            __import__(module)
        except ImportError:
            optional_missing.append(name)
    
    if optional_missing:
        print(f"Optional packages not installed: {', '.join(optional_missing)}")
    
    return True, "All required dependencies found"


# ================ MAIN ================

def main():
    """
    application entry point
    """
    try:
        write_log("Starting Stocksight...")
        
        # check dependencies
        write_log("Checking dependencies...")
        success, message = check_dependencies()
        
        if not success:
            write_log(f"Dependency check failed: {message}")
            print(f"ERROR: {message}")
            print("Install with: pip install PyQt6 pandas numpy matplotlib autots")
            sys.exit(1)
        
        write_log("Dependencies OK")
        
        # initialize directories
        write_log("Initializing directories...")
        from config import init_directories
        init_directories()
        
        # import pyqt
        write_log("Importing PyQt6...")
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QFont
        
        # import main window
        write_log("Importing main window...")
        from ui.main_window import MainWindow
        
        # create application
        write_log("Creating application...")
        app = QApplication(sys.argv)
        
        # set application properties
        app.setApplicationName("Stocksight")
        app.setApplicationVersion("2.0.0")
        app.setOrganizationName("Stocksight")
        
        # set default font
        font = QFont("Segoe UI", 10)
        app.setFont(font)
        
        # create main window
        write_log("Creating main window...")
        window = MainWindow()
        window.show()
        
        write_log("Starting event loop...")
        exit_code = app.exec()
        
        write_log(f"Application closed with code: {exit_code}")
        sys.exit(exit_code)
        
    except Exception as e:
        error_msg = f"ERROR: {e}\n\n{traceback.format_exc()}"
        write_log(error_msg)
        print(f"FATAL ERROR: {e}")
        
        # show error dialog
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)
            
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Stocksight Error")
            msg.setText("Application crashed")
            msg.setInformativeText(str(e)[:500])
            msg.setDetailedText(traceback.format_exc())
            msg.exec()
            
        except Exception:
            pass
        
        sys.exit(1)


if __name__ == "__main__":
    main()