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
        self._frequency = "D"
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
        self._figure.patch.set_facecolor("white")
        self._canvas = FigureCanvas(self._figure)
        self._ax = None
        
        layout.addWidget(self._canvas)
        
        # navigation toolbar
        self._nav_toolbar = NavigationToolbar(self._canvas, self)
        layout.addWidget(self._nav_toolbar)
    
    # ---------- FREQUENCY SUPPORT ----------
    
    def set_frequency(self, frequency: str) -> None:
        # set chart frequency for axis formatting
        self._frequency = frequency
        self._redraw()
    
    def _get_date_formatter(self) -> mdates.DateFormatter:
        # get appropriate date formatter based on frequency
        if self._frequency == "D":
            return mdates.DateFormatter("%Y-%m-%d")
        elif self._frequency == "W":
            return mdates.DateFormatter("%Y-W%W")
        elif self._frequency == "M":
            return mdates.DateFormatter("%Y-%m")
        else:
            return mdates.DateFormatter("%Y-%m-%d")
    
    def _get_date_locator(self) -> mdates.DateLocator:
        # get appropriate date locator based on frequency
        if self._frequency == "D":
            return mdates.AutoDateLocator()
        elif self._frequency == "W":
            return mdates.WeekdayLocator(interval=2)
        elif self._frequency == "M":
            return mdates.MonthLocator()
        else:
            return mdates.AutoDateLocator()
    
    def _get_axis_label(self) -> str:
        # get axis label based on frequency
        labels = {
            "D": "Date",
            "W": "Week",
            "M": "Month"
        }
        return labels.get(self._frequency, "Date")
    
    # ---------- DATA MANAGEMENT ----------
    
    def set_data(self, dates: List, values: List, label: str = "Actual") -> None:
        # set time series data
        if not dates or not values:
            self._data = None
            self._redraw()
            return
        
        # convert and validate dates
        try:
            parsed_dates = pd.to_datetime(dates)
        except Exception:
            self._data = None
            self._redraw()
            return
        
        # validate values
        clean_values = []
        for v in values:
            try:
                fv = float(v)
                if np.isfinite(fv):
                    clean_values.append(fv)
                else:
                    clean_values.append(0)
            except (ValueError, TypeError):
                clean_values.append(0)
        
        self._data = {
            "dates": parsed_dates,
            "values": clean_values,
            "label": label
        }
        self._redraw()
    
    def set_forecast(self, dates: List, values: List, 
                     lower: Optional[List] = None, 
                     upper: Optional[List] = None) -> None:
        # set forecast data
        if not dates or not values:
            self._forecast = None
            return
        
        # convert and validate
        try:
            parsed_dates = pd.to_datetime(dates)
        except Exception:
            self._forecast = None
            return
        
        # clean values
        clean_values = []
        for v in values:
            try:
                fv = float(v)
                clean_values.append(fv if np.isfinite(fv) else 0)
            except (ValueError, TypeError):
                clean_values.append(0)
        
        # clean bounds
        clean_lower = None
        clean_upper = None
        
        if lower:
            clean_lower = []
            for v in lower:
                try:
                    fv = float(v)
                    clean_lower.append(fv if np.isfinite(fv) else 0)
                except (ValueError, TypeError):
                    clean_lower.append(0)
        
        if upper:
            clean_upper = []
            for v in upper:
                try:
                    fv = float(v)
                    clean_upper.append(fv if np.isfinite(fv) else 0)
                except (ValueError, TypeError):
                    clean_upper.append(0)
        
        self._forecast = {
            "dates": parsed_dates,
            "values": clean_values,
            "lower": clean_lower,
            "upper": clean_upper
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
        self._figure.clear()
        self._ax = None
        self._canvas.draw()
    
    # ---------- DRAWING ----------
    
    def _redraw(self) -> None:
        # redraw chart with current data
        self._figure.clear()
        self._ax = self._figure.add_subplot(111)
        
        # apply styling
        self._ax.set_facecolor("white")
        self._ax.grid(True, linestyle="--", alpha=0.3, color="#cccccc")
        
        # check for data
        has_data = self._data is not None and len(self._data.get("values", [])) > 0
        has_forecast = self._forecast is not None and len(self._forecast.get("values", [])) > 0
        
        if not has_data and not has_forecast:
            self._ax.text(0.5, 0.5, "No data to display", 
                         ha="center", va="center", transform=self._ax.transAxes,
                         fontsize=12, color="gray")
            self._canvas.draw()
            return
        
        # draw historical data
        if has_data:
            dates = self._data["dates"]
            values = self._data["values"]
            label = self._data.get("label", "Actual")
            
            chart_type = self._chart_type.currentText()
            
            # use explicit colors that are visible
            hist_color = "#2E86AB"  # primary blue
            
            if chart_type == "Line":
                self._ax.plot(dates, values, label=label, color=hist_color, 
                             linewidth=2, marker="o", markersize=3, markevery=max(1, len(dates)//20))
            elif chart_type == "Bar":
                self._ax.bar(dates, values, label=label, color=hist_color, alpha=0.7)
            elif chart_type == "Area":
                self._ax.fill_between(dates, values, label=label, color=hist_color, alpha=0.3)
                self._ax.plot(dates, values, color=hist_color, linewidth=2)
        
        # draw forecast
        if has_forecast and self._show_forecast.isChecked():
            f_dates = self._forecast["dates"]
            f_values = self._forecast["values"]
            
            # use distinct forecast color
            forecast_color = "#E91E63"  # pink/magenta
            
            self._ax.plot(f_dates, f_values, label="Forecast", 
                         color=forecast_color, linewidth=2, linestyle="--",
                         marker="s", markersize=4, markevery=max(1, len(f_dates)//10))
            
            # confidence interval
            if self._forecast.get("lower") and self._forecast.get("upper"):
                self._ax.fill_between(f_dates, self._forecast["lower"], self._forecast["upper"],
                                     color=forecast_color, alpha=0.15)
        
        # draw anomalies
        if self._anomalies and self._show_anomalies.isChecked():
            for anomaly in self._anomalies:
                try:
                    a_date = pd.to_datetime(anomaly.get("date"))
                    a_value = float(anomaly.get("value", 0))
                    a_type = anomaly.get("type", "spike")
                    
                    color = "#DC3545" if a_type == "spike" else "#FFC107"
                    self._ax.scatter([a_date], [a_value], color=color, s=120, zorder=5, 
                                    marker="o", edgecolors="white", linewidths=2)
                except Exception:
                    continue
        
        # format axes
        self._ax.xaxis.set_major_formatter(self._get_date_formatter())
        self._ax.xaxis.set_major_locator(self._get_date_locator())
        
        # rotate labels for readability
        self._figure.autofmt_xdate(rotation=45)
        
        self._ax.set_xlabel(self._get_axis_label())
        self._ax.set_ylabel("Value")
        self._ax.legend(loc="upper left", framealpha=0.9)
        
        # add some padding to y-axis
        if has_data or has_forecast:
            all_values = []
            if has_data:
                all_values.extend(self._data["values"])
            if has_forecast:
                all_values.extend(self._forecast["values"])
            
            if all_values:
                y_min = min(all_values)
                y_max = max(all_values)
                y_range = y_max - y_min if y_max != y_min else max(abs(y_max), 1)
                self._ax.set_ylim(max(0, y_min - y_range * 0.1), y_max + y_range * 0.1)
        
        self._figure.tight_layout()
        self._canvas.draw()
    
    def _set_zoom(self, days: Optional[int]) -> None:
        # set zoom level
        if self._ax is None:
            return
        
        # get all dates
        all_dates = []
        if self._data is not None:
            all_dates.extend(self._data["dates"].tolist())
        if self._forecast is not None:
            all_dates.extend(self._forecast["dates"].tolist())
        
        if not all_dates:
            return
        
        all_dates = pd.to_datetime(all_dates)
        
        if days is None:
            self._ax.set_xlim(all_dates.min(), all_dates.max())
        else:
            end_date = all_dates.max()
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