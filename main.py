"""
stocksight application entry point
initializes pyqt application
launches main window
"""

import sys
import os
from pathlib import Path

# add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QCoreApplication, QObject, QEvent
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QComboBox

import config
from utils.logging_config import setup_logging
from ui.main_window import MainWindow


# ============================================================================
#                              INITIALIZATION
# ============================================================================

def setup_application():
    # configure application attributes before creating qapplication
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # create application instance
    app = QApplication(sys.argv)
    
    # set application metadata
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)
    app.setOrganizationName(config.APP_AUTHOR)
    
    # Do not override the system font — let the OS/application default be used
    
    # load stylesheet if exists
    style_path = config.STYLES_DIR / "main.qss"
    if style_path.exists():
        with open(style_path, "r") as f:
            app.setStyleSheet(f.read())
    
    return app


def main():
    # setup logging
    logger = setup_logging()
    logger.info(f"starting {config.APP_NAME} v{config.APP_VERSION}")
    
    # create application
    app = setup_application()

    # Prevent mouse wheel from accidentally changing QComboBox selection when scrolling
    class _ComboWheelFilter(QObject):
        def eventFilter(self, obj, event):
            try:
                if event.type() == QEvent.Type.Wheel:
                    # ignore wheel events targeted at combobox widgets
                    if isinstance(obj, QComboBox):
                        return True
                return super().eventFilter(obj, event)
            except Exception:
                return False

    app.installEventFilter(_ComboWheelFilter(app))
    
    # create and show main window
    window = MainWindow()
    window.show()
    
    # run application
    exit_code = app.exec_()
    
    logger.info(f"application exited with code {exit_code}")
    sys.exit(exit_code)


# ============================================================================
#                                  ENTRY
# ============================================================================

if __name__ == "__main__":
    main()