"""
core package initialization
central path setup for robust imports
"""


# ================ IMPORTS ================

import os
import sys


# ================ PATH SETUP ================

_core_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_core_dir)

if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


# ================ EXPORTS ================

from core.state import STATE, PipelineStage, AlertSeverity