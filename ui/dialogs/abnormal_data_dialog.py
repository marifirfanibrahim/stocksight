"""
abnormal data dialog module
displays abnormal data for review
allows export to external applications
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QGroupBox, QMessageBox,
    QFileDialog, QAbstractItemView, QTabWidget, QWidget,
    QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal
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
    
    # signals
    fix_requested = pyqtSignal(str, dict)  # fix type, options
    
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
        
        desc = QLabel("Below are the data quality issues detected. Select which issues to fix and export data for review.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)
        
        # tabs for different issue types
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)
        
        # fix options section
        fix_group = QGroupBox("Apply Fixes")
        fix_layout = QVBoxLayout(fix_group)
        
        fix_desc = QLabel("Select which issues to fix:")
        fix_layout.addWidget(fix_desc)
        
        # fix checkboxes
        self._fix_checks = {}
        fix_options = [
            ("missing", "Fill missing values (forward fill)"),
            ("duplicates", "Aggregate duplicate entries (sum quantities)"),
            ("negative", "Fix negative values (set to zero)"),
            ("outliers", "Remove statistical outliers")
        ]
        
        for key, label in fix_options:
            check = QCheckBox(label)
            check.setEnabled(False)  # enabled when issue exists
            self._fix_checks[key] = check
            fix_layout.addWidget(check)
        
        # apply selected fixes button
        fix_btn_layout = QHBoxLayout()
        self._apply_fixes_btn = QPushButton("Apply Selected Fixes")
        self._apply_fixes_btn.clicked.connect(self._apply_selected_fixes)
        fix_btn_layout.addWidget(self._apply_fixes_btn)
        fix_btn_layout.addStretch()
        fix_layout.addLayout(fix_btn_layout)
        
        layout.addWidget(fix_group)
        
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
        # analyze and categorize abnormal data - only abnormal rows
        df = self._data
        qty_col = self._column_mapping.get("quantity")
        date_col = self._column_mapping.get("date")
        sku_col = self._column_mapping.get("sku")
        
        # missing values - only rows with missing in mapped columns
        mapped_cols = [c for c in self._column_mapping.values() if c and c in df.columns]
        if mapped_cols:
            missing_mask = df[mapped_cols].isnull().any(axis=1)
            if missing_mask.any():
                self._abnormal_data["missing"] = {
                    "title": "Missing Values",
                    "data": df[missing_mask][mapped_cols + [c for c in df.columns if c not in mapped_cols][:2]].copy(),
                    "description": f"{missing_mask.sum():,} rows with missing values in key columns"
                }
                self._fix_checks["missing"].setEnabled(True)
        
        # duplicates - only duplicate rows
        if sku_col and date_col:
            dup_mask = df.duplicated(subset=[sku_col, date_col], keep=False)
            if dup_mask.any():
                # only show relevant columns for duplicates
                display_cols = [sku_col, date_col]
                if qty_col:
                    display_cols.append(qty_col)
                
                self._abnormal_data["duplicates"] = {
                    "title": "Duplicate Entries",
                    "data": df[dup_mask][display_cols].sort_values([sku_col, date_col]).copy(),
                    "description": f"{dup_mask.sum():,} duplicate rows (same item and date)"
                }
                self._fix_checks["duplicates"].setEnabled(True)
        
        # negative values - only negative rows
        if qty_col and qty_col in df.columns:
            neg_mask = df[qty_col] < 0
            if neg_mask.any():
                # show only relevant columns
                display_cols = [sku_col, date_col, qty_col] if sku_col and date_col else [qty_col]
                display_cols = [c for c in display_cols if c and c in df.columns]
                
                self._abnormal_data["negative"] = {
                    "title": "Negative Values",
                    "data": df[neg_mask][display_cols].copy(),
                    "description": f"{neg_mask.sum():,} rows with negative quantities"
                }
                self._fix_checks["negative"].setEnabled(True)
        
        # outliers using IQR - only outlier rows
        if qty_col and qty_col in df.columns:
            q1 = df[qty_col].quantile(0.25)
            q3 = df[qty_col].quantile(0.75)
            iqr = q3 - q1
            
            outlier_mask = (df[qty_col] < q1 - 1.5 * iqr) | (df[qty_col] > q3 + 1.5 * iqr)
            if outlier_mask.any():
                # show only relevant columns
                display_cols = [sku_col, date_col, qty_col] if sku_col and date_col else [qty_col]
                display_cols = [c for c in display_cols if c and c in df.columns]
                
                self._abnormal_data["outliers"] = {
                    "title": "Statistical Outliers",
                    "data": df[outlier_mask][display_cols].copy(),
                    "description": f"{outlier_mask.sum():,} rows with outlier values (outside 1.5x IQR)"
                }
                self._fix_checks["outliers"].setEnabled(True)
    
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
            self._apply_fixes_btn.setEnabled(False)
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
        
        for row_idx, (i, row) in enumerate(display_df.iterrows()):
            for j, value in enumerate(row):
                cell_text = str(value) if pd.notna(value) else ""
                item = QTableWidgetItem(cell_text)
                
                # highlight abnormal cells
                if pd.isna(value):
                    item.setBackground(QBrush(QColor("#FFCDD2")))
                elif isinstance(value, (int, float)) and value < 0:
                    item.setBackground(QBrush(QColor("#FFCDD2")))
                
                table.setItem(row_idx, j, item)
        
        table.resizeColumnsToContents()
        
        layout.addWidget(table)
        
        # row count info
        if len(df) > 1000:
            info_label = QLabel(f"Showing first 1,000 of {len(df):,} rows. Export to view all.")
            info_label.setStyleSheet("color: #666; font-style: italic;")
            layout.addWidget(info_label)
        
        return widget
    
    # ---------- FIX METHODS ----------
    
    def _apply_selected_fixes(self) -> None:
        # apply selected fixes with confirmation
        selected_fixes = []
        fix_descriptions = {
            "missing": "Fill missing values using forward fill",
            "duplicates": "Aggregate duplicate entries by summing quantities",
            "negative": "Set negative values to zero",
            "outliers": "Remove rows with statistical outliers"
        }
        
        for key, check in self._fix_checks.items():
            if check.isEnabled() and check.isChecked():
                selected_fixes.append((key, fix_descriptions.get(key, key)))
        
        if not selected_fixes:
            QMessageBox.information(
                self,
                "No Fixes Selected",
                "Please select at least one fix to apply."
            )
            return
        
        # build confirmation message
        fix_list = "\n".join([f"• {desc}" for _, desc in selected_fixes])
        
        reply = QMessageBox.question(
            self,
            "Confirm Fixes",
            f"The following fixes will be applied:\n\n{fix_list}\n\n"
            "This will modify your data. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # emit signal for each selected fix
            for fix_key, _ in selected_fixes:
                self.fix_requested.emit(fix_key, {})
            
            QMessageBox.information(
                self,
                "Fixes Applied",
                f"Applied {len(selected_fixes)} fix(es) to your data.\n"
                "Close this dialog to see updated quality metrics."
            )
            self.accept()
    
    def get_selected_fixes(self) -> List[str]:
        # get list of selected fix types
        return [key for key, check in self._fix_checks.items() 
                if check.isEnabled() and check.isChecked()]
    
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