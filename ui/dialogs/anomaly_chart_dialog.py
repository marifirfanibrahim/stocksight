"""
anomaly chart dialog module
displays sku chart in separate window
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication
from typing import Optional, List, Dict
import pandas as pd

from ui.widgets.time_series_chart import TimeSeriesChart
import config


# ============================================================================
#                       ANOMALY CHART DIALOG
# ============================================================================

class AnomalyChartDialog(QDialog):
    # dialog showing sku chart with anomalies
    
    def __init__(self, 
                 sku: str,
                 sku_data: pd.DataFrame,
                 date_col: str,
                 qty_col: str,
                 anomalies: Optional[List[Dict]] = None,
                 parent=None):
        # initialize dialog
        super().__init__(parent)
        
        self._sku = sku
        self._sku_data = sku_data
        self._date_col = date_col
        self._qty_col = qty_col
        self._anomalies = anomalies or []
        
        self._setup_ui()
        self._load_chart()
    
    def _setup_ui(self) -> None:
        # setup user interface
        self.setWindowTitle(f"Time Series Chart - {self._sku}")
        self.setMinimumWidth(900)
        self.setMinimumHeight(550)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # header
        header_layout = QHBoxLayout()
        
        header = QLabel(f"Item: {self._sku}")
        try:
            app = QApplication.instance()
            base_font = app.font() if app is not None else QFont()
            hdr_font = QFont(base_font.family(), max(10, base_font.pointSize() + 2), QFont.Bold)
            header.setFont(hdr_font)
        except Exception:
            header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # data points info
        data_info = QLabel(f"{len(self._sku_data):,} data points")
        data_info.setStyleSheet("color: #666;")
        header_layout.addWidget(data_info)
        
        layout.addLayout(header_layout)
        
        # chart
        self._chart = TimeSeriesChart()
        layout.addWidget(self._chart)
        
        # anomaly info
        if self._anomalies:
            anomaly_label = QLabel(f"🔴 {len(self._anomalies)} anomalies highlighted")
            anomaly_label.setStyleSheet("color: #DC3545; font-weight: bold;")
            layout.addWidget(anomaly_label)
        
        # buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _load_chart(self) -> None:
        # load data into chart
        if self._sku_data.empty:
            return
        
        dates = self._sku_data[self._date_col].tolist()
        values = self._sku_data[self._qty_col].tolist()
        
        self._chart.set_data(dates, values, label=self._sku)
        
        # add anomalies
        if self._anomalies:
            self._chart.set_anomalies(self._anomalies)