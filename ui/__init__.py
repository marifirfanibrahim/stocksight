"""
ui package initialization
pyqt6 user interface components
"""


# ================ IMPORTS ================

import os
import sys


# ================ PATH SETUP ================

_ui_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_ui_dir)

if _project_root not in sys.path:
    sys.path.insert(0, _project_root)