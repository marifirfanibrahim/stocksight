"""
forecast table model module
qt model for displaying forecast results
handles forecast specific formatting
"""

from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant
from PyQt5.QtGui import QColor, QBrush
from typing import Dict, List, Any, Optional
import pandas as pd

import config
from core.forecaster import ForecastResult


# ============================================================================
#                        FORECAST TABLE MODEL
# ============================================================================

class ForecastTableModel(QAbstractTableModel):
    # table model for forecast results
    
    COLUMNS = [
        "sku", "model", "total_forecast", "avg_daily", 
        "mape", "mae", "status"
    ]
    
    HEADERS = [
        "Item", "Model", "Total Forecast", "Avg Daily",
        "MAPE %", "MAE", "Status"
    ]
    
    def __init__(self, parent=None):
        # initialize model
        super().__init__(parent)
        
        self._forecasts = {}
        self._rows = []
        self._sort_column = 0
        self._sort_order = Qt.DescendingOrder
    
    # ---------- DATA MANAGEMENT ----------
    
    def set_forecasts(self, forecasts: Dict[str, ForecastResult]) -> None:
        # set forecast data
        self.beginResetModel()
        
        self._forecasts = forecasts
        self._rows = []
        
        for sku, result in forecasts.items():
            total = sum(result.forecast)
            avg = total / len(result.forecast) if result.forecast else 0
            mape = result.metrics.get("mape", 0)
            mae = result.metrics.get("mae", 0)
            
            # determine status
            if mape < 15:
                status = "Good"
            elif mape < 30:
                status = "Fair"
            else:
                status = "Review"
            
            self._rows.append({
                "sku": sku,
                "model": result.model,
                "total_forecast": total,
                "avg_daily": avg,
                "mape": mape,
                "mae": mae,
                "status": status,
                "result": result
            })
        
        self._apply_sort()
        self.endResetModel()
    
    def get_forecast(self, sku: str) -> Optional[ForecastResult]:
        # get forecast result for sku
        return self._forecasts.get(sku)
    
    def get_row_forecast(self, row: int) -> Optional[ForecastResult]:
        # get forecast for row index
        if 0 <= row < len(self._rows):
            return self._rows[row].get("result")
        return None
    
    # ---------- QT MODEL INTERFACE ----------
    
    def rowCount(self, parent=QModelIndex()) -> int:
        # return row count
        if parent.isValid():
            return 0
        return len(self._rows)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        # return column count
        if parent.isValid():
            return 0
        return len(self.COLUMNS)
    
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> QVariant:
        # return cell data
        if not index.isValid():
            return QVariant()
        
        row = index.row()
        col = index.column()
        
        if row < 0 or row >= len(self._rows):
            return QVariant()
        
        row_data = self._rows[row]
        col_name = self.COLUMNS[col]
        value = row_data.get(col_name, "")
        
        if role == Qt.DisplayRole:
            return self._format_value(value, col_name)
        
        elif role == Qt.TextAlignmentRole:
            if col_name in ["total_forecast", "avg_daily", "mape", "mae"]:
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter
        
        elif role == Qt.BackgroundRole:
            return self._get_background(row_data, col_name)
        
        elif role == Qt.UserRole:
            return row_data
        
        return QVariant()
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> QVariant:
        # return header data
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal and section < len(self.HEADERS):
                return self.HEADERS[section]
            elif orientation == Qt.Vertical:
                return str(section + 1)
        
        return QVariant()
    
    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None:
        # sort by column
        if column < 0 or column >= len(self.COLUMNS):
            return
        
        self.beginResetModel()
        self._sort_column = column
        self._sort_order = order
        self._apply_sort()
        self.endResetModel()
    
    def _apply_sort(self) -> None:
        # apply current sort
        col_name = self.COLUMNS[self._sort_column]
        reverse = (self._sort_order == Qt.DescendingOrder)
        
        self._rows.sort(
            key=lambda x: x.get(col_name, 0) if isinstance(x.get(col_name), (int, float)) else str(x.get(col_name, "")),
            reverse=reverse
        )
    
    # ---------- FORMATTING ----------
    
    def _format_value(self, value: Any, column: str) -> str:
        # format value for display
        if value is None:
            return ""
        
        if column == "total_forecast":
            return f"{value:,.0f}"
        elif column == "avg_daily":
            return f"{value:,.1f}"
        elif column == "mape":
            return f"{value:.1f}%"
        elif column == "mae":
            return f"{value:.2f}"
        
        return str(value)
    
    def _get_background(self, row_data: Dict, column: str) -> QVariant:
        # get background color
        if column == "status":
            status = row_data.get("status", "")
            if status == "Good":
                return QBrush(QColor(200, 230, 200))
            elif status == "Fair":
                return QBrush(QColor(255, 255, 200))
            elif status == "Review":
                return QBrush(QColor(255, 200, 200))
        
        elif column == "mape":
            mape = row_data.get("mape", 0)
            if mape < 15:
                return QBrush(QColor(200, 230, 200))
            elif mape > 30:
                return QBrush(QColor(255, 200, 200))
        
        return QVariant()
    
    # ---------- FILTERING ----------
    
    def get_problem_rows(self) -> List[int]:
        # get rows with high mape
        return [i for i, r in enumerate(self._rows) if r.get("mape", 0) > 30]
    
    def get_rows_by_status(self, status: str) -> List[int]:
        # get rows by status
        return [i for i, r in enumerate(self._rows) if r.get("status") == status]
    
    def get_summary(self) -> Dict[str, Any]:
        # get forecast summary
        if not self._rows:
            return {}
        
        total_forecast = sum(r["total_forecast"] for r in self._rows)
        avg_mape = sum(r["mape"] for r in self._rows) / len(self._rows)
        
        status_counts = {}
        model_counts = {}
        
        for r in self._rows:
            status = r.get("status", "Unknown")
            model = r.get("model", "Unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            model_counts[model] = model_counts.get(model, 0) + 1
        
        return {
            "total_items": len(self._rows),
            "total_forecast": total_forecast,
            "avg_mape": avg_mape,
            "status_distribution": status_counts,
            "model_distribution": model_counts
        }