"""
sku table model module
qt model for displaying sku data in tables
supports virtual scrolling for large datasets
"""

from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant
from PyQt5.QtGui import QColor, QBrush
from typing import List, Dict, Any, Optional
import pandas as pd

import config


# ============================================================================
#                           SKU TABLE MODEL
# ============================================================================

class SKUTableModel(QAbstractTableModel):
    # table model for sku data display
    
    def __init__(self, parent=None):
        # initialize model
        super().__init__(parent)
        
        self._data = pd.DataFrame()
        self._columns = []
        self._display_columns = []
        self._sort_column = 0
        self._sort_order = Qt.AscendingOrder
        self._filter_text = ""
        self._filtered_indices = []
    
    # ---------- DATA MANAGEMENT ----------
    
    def set_data(self, data: pd.DataFrame, display_columns: Optional[List[str]] = None) -> None:
        # set dataframe data
        self.beginResetModel()
        
        self._data = data.copy() if data is not None else pd.DataFrame()
        self._columns = list(self._data.columns)
        
        if display_columns:
            self._display_columns = [c for c in display_columns if c in self._columns]
        else:
            self._display_columns = self._columns[:10]  # limit default columns
        
        self._apply_filter()
        self.endResetModel()
    
    def get_data(self) -> pd.DataFrame:
        # get underlying dataframe
        return self._data
    
    def get_row_data(self, row: int) -> Dict[str, Any]:
        # get data for specific row
        if 0 <= row < len(self._filtered_indices):
            actual_idx = self._filtered_indices[row]
            return self._data.iloc[actual_idx].to_dict()
        return {}
    
    # ---------- QT MODEL INTERFACE ----------
    
    def rowCount(self, parent=QModelIndex()) -> int:
        # return number of rows
        if parent.isValid():
            return 0
        return len(self._filtered_indices)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        # return number of columns
        if parent.isValid():
            return 0
        return len(self._display_columns)
    
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> QVariant:
        # return data for cell
        if not index.isValid():
            return QVariant()
        
        row = index.row()
        col = index.column()
        
        if row < 0 or row >= len(self._filtered_indices):
            return QVariant()
        
        actual_row = self._filtered_indices[row]
        col_name = self._display_columns[col]
        value = self._data.iloc[actual_row][col_name]
        
        if role == Qt.DisplayRole:
            return self._format_value(value, col_name)
        
        elif role == Qt.TextAlignmentRole:
            if isinstance(value, (int, float)):
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter
        
        elif role == Qt.BackgroundRole:
            return self._get_background_color(actual_row, col_name, value)
        
        elif role == Qt.UserRole:
            return value
        
        return QVariant()
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> QVariant:
        # return header data
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal and section < len(self._display_columns):
                col_name = self._display_columns[section]
                return self._format_header(col_name)
            elif orientation == Qt.Vertical:
                return str(section + 1)
        
        return QVariant()
    
    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None:
        # sort by column
        if column < 0 or column >= len(self._display_columns):
            return
        
        self.beginResetModel()
        
        self._sort_column = column
        self._sort_order = order
        
        col_name = self._display_columns[column]
        ascending = (order == Qt.AscendingOrder)
        
        # sort indices
        sorted_indices = self._data[col_name].iloc[self._filtered_indices].argsort()
        if not ascending:
            sorted_indices = sorted_indices[::-1]
        
        self._filtered_indices = [self._filtered_indices[i] for i in sorted_indices]
        
        self.endResetModel()
    
    # ---------- FILTERING ----------
    
    def set_filter(self, text: str) -> None:
        # set filter text
        self.beginResetModel()
        self._filter_text = text.lower()
        self._apply_filter()
        self.endResetModel()
    
    def _apply_filter(self) -> None:
        # apply current filter
        if not self._filter_text:
            self._filtered_indices = list(range(len(self._data)))
        else:
            self._filtered_indices = []
            for i in range(len(self._data)):
                row = self._data.iloc[i]
                for col in self._display_columns:
                    if self._filter_text in str(row[col]).lower():
                        self._filtered_indices.append(i)
                        break
    
    def clear_filter(self) -> None:
        # clear filter
        self.set_filter("")
    
    # ---------- FORMATTING ----------
    
    def _format_value(self, value: Any, column: str) -> str:
        # format value for display
        if pd.isna(value):
            return ""
        
        if isinstance(value, float):
            if "pct" in column.lower() or "percent" in column.lower():
                return f"{value:.1f}%"
            elif "mape" in column.lower() or "mae" in column.lower():
                return f"{value:.2f}"
            elif abs(value) >= 1000:
                return f"{value:,.0f}"
            else:
                return f"{value:.2f}"
        
        if isinstance(value, int):
            return f"{value:,}"
        
        return str(value)
    
    def _format_header(self, column: str) -> str:
        # format column header
        # convert snake_case to Title Case
        return column.replace("_", " ").title()
    
    def _get_background_color(self, row: int, column: str, value: Any) -> QVariant:
        # get background color for cell
        # highlight based on column type
        if "tier" in column.lower() or "class" in column.lower():
            if value == "A":
                return QBrush(QColor(200, 230, 200))  # light green
            elif value == "B":
                return QBrush(QColor(255, 255, 200))  # light yellow
            elif value == "C":
                return QBrush(QColor(255, 220, 200))  # light orange
        
        if "mape" in column.lower():
            if isinstance(value, (int, float)):
                if value < 10:
                    return QBrush(QColor(200, 230, 200))
                elif value > 30:
                    return QBrush(QColor(255, 200, 200))
        
        return QVariant()
    
    # ---------- COLUMN MANAGEMENT ----------
    
    def set_display_columns(self, columns: List[str]) -> None:
        # set which columns to display
        self.beginResetModel()
        self._display_columns = [c for c in columns if c in self._columns]
        self.endResetModel()
    
    def get_display_columns(self) -> List[str]:
        # get current display columns
        return self._display_columns.copy()
    
    def get_all_columns(self) -> List[str]:
        # get all available columns
        return self._columns.copy()