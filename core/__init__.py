"""
core package initialization
central path setup for robust imports
"""

import os
import sys

# ================ PATH SETUP ================

# get project root directory
_core_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_core_dir)

# add to system path if missing
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)