"""
time series chart widget
displays time series data with interactivity
uses matplotlib for rendering
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel
from PyQt5.QtCore import pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np

import config


# ============================================================================
#                         TIME SERIES CHART
# ============================================================================

class TimeSeriesChart(QWidget):
    # interactive time series chart widget
    
    # signals
    point_clicked = pyqtSignal(dict)
    range_selected = pyqtSignal(str, str)
    
    def __init__(self, parent=None):
        # initialize chart widget
        super().__init__(parent)
        
        self._data = None
        self._forecast = None
        self._anomalies = []
        self._setup_ui()
    
    # ---------- UI SETUP ----------
    
    def _setup_ui(self) -> None:
        # setup user interface
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # toolbar
        toolbar_layout = QHBoxLayout()
        
        # chart type selector
        self._chart_type = QComboBox()
        self._chart_type.addItems(["Line", "Bar", "Area"])
        self._chart_type.currentIndexChanged.connect(self._redraw)
        toolbar_layout.addWidget(QLabel("Type:"))
        toolbar_layout.addWidget(self._chart_type)
        
        # show options
        self._show_forecast = QPushButton("Forecast")
        self._show_forecast.setCheckable(True)
        self._show_forecast.clicked.connect(self._redraw)
        toolbar_layout.addWidget(self._show_forecast)
        
        self._show_anomalies = QPushButton("Anomalies")
        self._show_anomalies.setCheckable(True)
        self._show_anomalies.clicked.connect(self._redraw)
        toolbar_layout.addWidget(self._show_anomalies)
        
        toolbar_layout.addStretch()
        
        # zoom buttons
        self._zoom_1m = QPushButton("1M")
        self._zoom_1m.clicked.connect(lambda: self._set_zoom(30))
        toolbar_layout.addWidget(self._zoom_1m)
        
        self._zoom_3m = QPushButton("3M")
        self._zoom_3m.clicked.connect(lambda: self._set_zoom(90))
        toolbar_layout.addWidget(self._zoom_3m)
        
        self._zoom_all = QPushButton("All")
        self._zoom_all.clicked.connect(lambda: self._set_zoom(None))
        toolbar_layout.addWidget(self._zoom_all)
        
        layout.addLayout(toolbar_layout)
        
        # matplotlib figure
        self._figure = Figure(figsize=(10, 4), dpi=100)
        self._canvas = FigureCanvas(self._figure)
        self._ax = self._figure.add_subplot(111)
        
        layout.addWidget(self._canvas)
        
        # navigation toolbar
        self._nav_toolbar = NavigationToolbar(self._canvas, self)
        layout.addWidget(self._nav_toolbar)
        
        # apply styling
        self._apply_style()
    
    def _apply_style(self) -> None:
        # apply chart styling
        self._figure.patch.set_facecolor("white")
        self._ax.set_facecolor("white")
        self._ax.grid(True, linestyle="--", alpha=0.3)
    
    # ---------- DATA MANAGEMENT ----------
    
    def set_data(self, dates: List, values: List, label: str = "Actual") -> None:
        # set time series data
        self._data = {
            "dates": pd.to_datetime(dates),
            "values": values,
            "label": label
        }
        self._redraw()
    
    def set_forecast(self, dates: List, values: List, 
                     lower: Optional[List] = None, 
                     upper: Optional[List] = None) -> None:
        # set forecast data
        self._forecast = {
            "dates": pd.to_datetime(dates),
            "values": values,
            "lower": lower,
            "upper": upper
        }
        self._show_forecast.setChecked(True)
        self._redraw()
    
    def set_anomalies(self, anomalies: List[Dict]) -> None:
        # set anomaly markers
        self._anomalies = anomalies
        self._show_anomalies.setChecked(True)
        self._redraw()
    
    def clear(self) -> None:
        # clear all data
        self._data = None
        self._forecast = None
        self._anomalies = []
        self._ax.clear()
        self._canvas.draw()
    
    # ---------- DRAWING ----------
    
    def _redraw(self) -> None:
        # redraw chart with current data
        self._ax.clear()
        self._apply_style()
        
        if self._data is None:
            self._canvas.draw()
            return
        
        dates = self._data["dates"]
        values = self._data["values"]
        label = self._data["label"]
        
        chart_type = self._chart_type.currentText()
        
        # draw main series
        if chart_type == "Line":
            self._ax.plot(dates, values, label=label, color=config.UI_COLORS["primary"], linewidth=1.5)
        elif chart_type == "Bar":
            self._ax.bar(dates, values, label=label, color=config.UI_COLORS["primary"], alpha=0.7)
        elif chart_type == "Area":
            self._ax.fill_between(dates, values, label=label, color=config.UI_COLORS["primary"], alpha=0.3)
            self._ax.plot(dates, values, color=config.UI_COLORS["primary"], linewidth=1)
        
        # draw forecast
        if self._forecast and self._show_forecast.isChecked():
            f_dates = self._forecast["dates"]
            f_values = self._forecast["values"]
            
            self._ax.plot(f_dates, f_values, label="Forecast", 
                         color=config.UI_COLORS["secondary"], linewidth=1.5, linestyle="--")
            
            # confidence interval
            if self._forecast["lower"] and self._forecast["upper"]:
                self._ax.fill_between(f_dates, self._forecast["lower"], self._forecast["upper"],
                                     color=config.UI_COLORS["secondary"], alpha=0.2)
        
        # draw anomalies
        if self._anomalies and self._show_anomalies.isChecked():
            for anomaly in self._anomalies:
                a_date = pd.to_datetime(anomaly.get("date"))
                a_value = anomaly.get("value", 0)
                a_type = anomaly.get("type", "spike")
                
                color = config.UI_COLORS["danger"] if a_type == "spike" else config.UI_COLORS["warning"]
                self._ax.scatter([a_date], [a_value], color=color, s=100, zorder=5, marker="o")
        
        # format axes
        self._ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        self._ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        self._figure.autofmt_xdate()
        
        self._ax.set_xlabel("Date")
        self._ax.set_ylabel("Value")
        self._ax.legend(loc="upper left")
        
        self._figure.tight_layout()
        self._canvas.draw()
    
    def _set_zoom(self, days: Optional[int]) -> None:
        # set zoom level
        if self._data is None:
            return
        
        dates = self._data["dates"]
        
        if days is None:
            self._ax.set_xlim(dates.min(), dates.max())
        else:
            end_date = dates.max()
            start_date = end_date - pd.Timedelta(days=days)
            self._ax.set_xlim(start_date, end_date)
        
        self._canvas.draw()
    
    # ---------- EXPORT ----------
    
    def save_figure(self, file_path: str, dpi: int = 150) -> bool:
        # save figure to file
        try:
            self._figure.savefig(file_path, dpi=dpi, bbox_inches="tight")
            return True
        except Exception:
            return False