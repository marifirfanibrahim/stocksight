"""
abnormal data dialog module
displays abnormal data for review
allows export to external applications
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QGroupBox, QMessageBox,
    QFileDialog, QAbstractItemView, QTabWidget, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QBrush
from typing import Dict, List, Any, Optional
import pandas as pd
import subprocess
import os
import tempfile

import config


# ============================================================================
#                       ABNORMAL DATA DIALOG
# ============================================================================

class AbnormalDataDialog(QDialog):
    # dialog for viewing abnormal data
    
    def __init__(self, 
                 data: pd.DataFrame, 
                 column_mapping: Dict[str, str],
                 quality_info: Dict[str, Any],
                 parent=None):
        # initialize dialog
        super().__init__(parent)
        
        self._data = data
        self._column_mapping = column_mapping
        self._quality_info = quality_info
        self._abnormal_data = {}
        
        self._setup_ui()
        self._analyze_abnormal_data()
        self._populate_tabs()
    
    # ---------- UI SETUP ----------
    
    def _setup_ui(self) -> None:
        # setup user interface
        self.setWindowTitle("Abnormal Data Review")
        self.setMinimumWidth(900)
        self.setMinimumHeight(600)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # header
        header = QLabel("Review Abnormal Data")
        header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(header)
        
        desc = QLabel("Below are the data quality issues detected. You can export any of these to review in Excel or other applications.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)
        
        # tabs for different issue types
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)
        
        # export buttons
        export_layout = QHBoxLayout()
        
        export_layout.addWidget(QLabel("Export selected data:"))
        
        self._export_csv_btn = QPushButton("📄 Export to CSV")
        self._export_csv_btn.clicked.connect(lambda: self._export_data("csv"))
        export_layout.addWidget(self._export_csv_btn)
        
        self._export_excel_btn = QPushButton("📊 Export to Excel")
        self._export_excel_btn.clicked.connect(lambda: self._export_data("excel"))
        export_layout.addWidget(self._export_excel_btn)
        
        self._open_excel_btn = QPushButton("🔗 Open in Excel")
        self._open_excel_btn.clicked.connect(self._open_in_excel)
        export_layout.addWidget(self._open_excel_btn)
        
        export_layout.addStretch()
        layout.addLayout(export_layout)
        
        # close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    # ---------- DATA ANALYSIS ----------
    
    def _analyze_abnormal_data(self) -> None:
        # analyze and categorize abnormal data
        df = self._data
        qty_col = self._column_mapping.get("quantity")
        date_col = self._column_mapping.get("date")
        sku_col = self._column_mapping.get("sku")
        
        # missing values
        missing_mask = df.isnull().any(axis=1)
        if missing_mask.any():
            self._abnormal_data["missing"] = {
                "title": "Missing Values",
                "data": df[missing_mask].copy(),
                "description": f"{missing_mask.sum():,} rows with missing values"
            }
        
        # duplicates
        if sku_col and date_col:
            dup_mask = df.duplicated(subset=[sku_col, date_col], keep=False)
            if dup_mask.any():
                self._abnormal_data["duplicates"] = {
                    "title": "Duplicate Entries",
                    "data": df[dup_mask].sort_values([sku_col, date_col]).copy(),
                    "description": f"{dup_mask.sum():,} duplicate rows"
                }
        
        # negative values
        if qty_col and qty_col in df.columns:
            neg_mask = df[qty_col] < 0
            if neg_mask.any():
                self._abnormal_data["negative"] = {
                    "title": "Negative Values",
                    "data": df[neg_mask].copy(),
                    "description": f"{neg_mask.sum():,} rows with negative quantities"
                }
        
        # zero values (potential issues)
        if qty_col and qty_col in df.columns:
            zero_mask = df[qty_col] == 0
            zero_count = zero_mask.sum()
            zero_pct = (zero_count / len(df)) * 100
            
            # only flag if significant percentage
            if zero_pct > 10:
                self._abnormal_data["zeros"] = {
                    "title": "Zero Values",
                    "data": df[zero_mask].copy(),
                    "description": f"{zero_count:,} rows ({zero_pct:.1f}%) with zero quantities"
                }
        
        # outliers using IQR
        if qty_col and qty_col in df.columns:
            q1 = df[qty_col].quantile(0.25)
            q3 = df[qty_col].quantile(0.75)
            iqr = q3 - q1
            
            outlier_mask = (df[qty_col] < q1 - 1.5 * iqr) | (df[qty_col] > q3 + 1.5 * iqr)
            if outlier_mask.any():
                self._abnormal_data["outliers"] = {
                    "title": "Statistical Outliers",
                    "data": df[outlier_mask].copy(),
                    "description": f"{outlier_mask.sum():,} rows with outlier values (IQR method)"
                }
    
    def _populate_tabs(self) -> None:
        # populate tabs with abnormal data
        if not self._abnormal_data:
            # no abnormal data found
            no_data = QWidget()
            no_layout = QVBoxLayout(no_data)
            no_label = QLabel("✓ No abnormal data detected!")
            no_label.setFont(QFont("Segoe UI", 14))
            no_label.setAlignment(Qt.AlignCenter)
            no_label.setStyleSheet("color: #28A745;")
            no_layout.addWidget(no_label)
            self._tabs.addTab(no_data, "All Clear")
            return
        
        for key, info in self._abnormal_data.items():
            tab = self._create_data_tab(info)
            self._tabs.addTab(tab, f"{info['title']} ({len(info['data']):,})")
    
    def _create_data_tab(self, info: Dict) -> QWidget:
        # create tab for data category
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # description
        desc = QLabel(info["description"])
        desc.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # table
        table = QTableWidget()
        df = info["data"]
        
        # limit display rows
        display_df = df.head(1000)
        
        table.setRowCount(len(display_df))
        table.setColumnCount(len(display_df.columns))
        table.setHorizontalHeaderLabels([str(c) for c in display_df.columns])
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        
        for i, row in display_df.iterrows():
            for j, value in enumerate(row):
                cell_text = str(value) if pd.notna(value) else ""
                item = QTableWidgetItem(cell_text)
                
                # highlight abnormal cells
                if pd.isna(value):
                    item.setBackground(QBrush(QColor("#FFCDD2")))
                elif isinstance(value, (int, float)) and value < 0:
                    item.setBackground(QBrush(QColor("#FFCDD2")))
                
                table.setItem(i if isinstance(i, int) else display_df.index.get_loc(i), j, item)
        
        table.resizeColumnsToContents()
        
        layout.addWidget(table)
        
        # row count info
        if len(df) > 1000:
            info_label = QLabel(f"Showing first 1,000 of {len(df):,} rows. Export to view all.")
            info_label.setStyleSheet("color: #666; font-style: italic;")
            layout.addWidget(info_label)
        
        return widget
    
    # ---------- EXPORT METHODS ----------
    
    def _get_current_data(self) -> Optional[pd.DataFrame]:
        # get data from current tab
        current_idx = self._tabs.currentIndex()
        
        if current_idx < 0:
            return None
        
        keys = list(self._abnormal_data.keys())
        if current_idx < len(keys):
            return self._abnormal_data[keys[current_idx]]["data"]
        
        return None
    
    def _export_data(self, format_type: str) -> None:
        # export current tab data
        df = self._get_current_data()
        
        if df is None or df.empty:
            QMessageBox.warning(self, "No Data", "No data to export")
            return
        
        if format_type == "csv":
            path, _ = QFileDialog.getSaveFileName(
                self, "Export to CSV", "abnormal_data.csv", "CSV Files (*.csv)"
            )
            if path:
                df.to_csv(path, index=False)
                QMessageBox.information(self, "Export Complete", f"Exported to:\n{path}")
        
        elif format_type == "excel":
            path, _ = QFileDialog.getSaveFileName(
                self, "Export to Excel", "abnormal_data.xlsx", "Excel Files (*.xlsx)"
            )
            if path:
                df.to_excel(path, index=False, engine="openpyxl")
                QMessageBox.information(self, "Export Complete", f"Exported to:\n{path}")
    
    def _open_in_excel(self) -> None:
        # export to temp file and open in excel
        df = self._get_current_data()
        
        if df is None or df.empty:
            QMessageBox.warning(self, "No Data", "No data to open")
            return
        
        try:
            # create temp file
            fd, path = tempfile.mkstemp(suffix=".xlsx")
            os.close(fd)
            
            df.to_excel(path, index=False, engine="openpyxl")
            
            # open with default application
            if os.name == "nt":  # windows
                os.startfile(path)
            elif os.name == "posix":  # mac/linux
                subprocess.run(["open" if os.uname().sysname == "Darwin" else "xdg-open", path])
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to open in Excel:\n{str(e)}")