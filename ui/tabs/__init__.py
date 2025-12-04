"""
ui tabs package
contains tab implementations for main window
"""

from .data_tab import DataTab
from .explore_tab import ExploreTab
from .features_tab import FeaturesTab
from .forecast_tab import ForecastTab

__all__ = [
    "DataTab",
    "ExploreTab",
    "FeaturesTab",
    "ForecastTab"
]