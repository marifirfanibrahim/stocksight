"""
abnormal data dialog module
displays abnormal data for review
allows fixes and export
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog,
    QAbstractItemView, QTabWidget, QWidget,
    QGroupBox, QLineEdit, QCheckBox, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QBrush
from PyQt5.QtWidgets import QApplication
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

import config
from core.data_processor import DataProcessor


# ============================================================================
#                       ABNORMAL DATA DIALOG
# ============================================================================

class AbnormalDataDialog(QDialog):
    # dialog for viewing abnormal data and applying fixes
    
    def __init__(self, 
                 data: pd.DataFrame, 
                 column_mapping: Dict[str, str],
                 quality_info: Dict[str, Any],
                 parent=None,
                 processor: Optional[DataProcessor] = None):
        # initialize dialog
        super().__init__(parent)
        
        self._data = data
        self._column_mapping = column_mapping
        self._quality_info = quality_info
        self._processor = processor
        
        self._abnormal_data: Dict[str, Dict[str, Any]] = {}
        self._tables: Dict[str, QTableWidget] = {}
        self._type_order: List[str] = []
        self._fix_controls: Dict[str, Dict[str, object]] = {}
        
        self._setup_ui()
        self._analyze_abnormal_data()
        self._populate_tabs()
        self._setup_fix_controls()
    
    # ---------- UI SETUP ----------
    
    def _setup_ui(self) -> None:
        # setup main dialog ui
        self.setWindowTitle("Abnormal Data Review")
        # Respect available screen size so dialog fits on small displays
        try:
            screen = self.screen().availableGeometry()
            min_w = min(900, max(560, int(screen.width() * 0.6)))
            min_h = min(600, max(400, int(screen.height() * 0.5)))
            self.setMinimumSize(min_w, min_h)
            # Prevent dialog exceeding the screen (leave margins)
            max_w = max(800, int(screen.width() - 80))
            max_h = max(600, int(screen.height() - 100))
            self.setMaximumSize(max_w, max_h)
        except Exception:
            self.setMinimumWidth(700)
            self.setMinimumHeight(480)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # header
        header = QLabel("Review Abnormal Data")
        try:
            app = QApplication.instance()
            base_font = app.font() if app is not None else QFont()
            header_font = QFont(base_font.family(), max(10, base_font.pointSize() + 2), QFont.Bold)
            header.setFont(header_font)
        except Exception:
            header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(header)
        
        # description
        desc = QLabel(
            "These rows look unusual based on missing values, duplicates, negatives, or outliers.\n"
            "You can search, apply fixes, or export full abnormal datasets."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)
        
        # search row
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Filter rows in current tab preview...")
        self._search_edit.textChanged.connect(self._apply_search_filter)
        search_layout.addWidget(self._search_edit)
        
        search_layout.addStretch()
        layout.addLayout(search_layout)
        
        # abnormal tabs
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)
        
        # fix controls
        self._fix_group = QGroupBox("Fix Abnormal Data")
        fix_layout = QVBoxLayout(self._fix_group)
        fix_layout.setSpacing(8)
        
        fix_desc = QLabel("Select which issues to fix and how:")
        fix_desc.setWordWrap(True)
        fix_desc.setStyleSheet("color: #666;")
        fix_layout.addWidget(fix_desc)
        
        self._fix_rows_container = QWidget()
        self._fix_rows_layout = QVBoxLayout(self._fix_rows_container)
        self._fix_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._fix_rows_layout.setSpacing(6)
        fix_layout.addWidget(self._fix_rows_container)
        
        layout.addWidget(self._fix_group)
        
        # bottom buttons
        bottom_layout = QHBoxLayout()
        
        self._export_csv_btn = QPushButton("📄 Export CSV")
        self._export_csv_btn.clicked.connect(lambda: self._export_data("csv"))
        bottom_layout.addWidget(self._export_csv_btn)
        
        self._export_excel_btn = QPushButton("📊 Export Excel")
        self._export_excel_btn.clicked.connect(lambda: self._export_data("excel"))
        bottom_layout.addWidget(self._export_excel_btn)
        
        bottom_layout.addSpacing(20)
        
        self._apply_btn = QPushButton("Apply Fixes")
        self._apply_btn.clicked.connect(self._apply_fixes)
        bottom_layout.addWidget(self._apply_btn)
        
        bottom_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(close_btn)
        
        layout.addLayout(bottom_layout)
    
    # ---------- ANALYSIS ----------
    
    def _analyze_abnormal_data(self) -> None:
        # analyze abnormal rows by category
        df = self._data
        qty_col = self._column_mapping.get("quantity")
        date_col = self._column_mapping.get("date")
        sku_col = self._column_mapping.get("sku")
        
        # missing values in mapped columns
        mapped_cols = [c for c in self._column_mapping.values() if c and c in df.columns]
        if mapped_cols:
            miss_mask = df[mapped_cols].isnull().any(axis=1)
            if miss_mask.any():
                self._abnormal_data["missing"] = {
                    "title": "Missing Values",
                    "data": df[miss_mask].copy(),
                    "description": f"{int(miss_mask.sum()):,} rows with missing values in key columns"
                }
        
        # duplicates by sku + date
        if sku_col and date_col:
            dup_mask = df.duplicated(subset=[sku_col, date_col], keep=False)
            if dup_mask.any():
                self._abnormal_data["duplicates"] = {
                    "title": "Duplicate Entries",
                    "data": df[dup_mask].copy(),
                    "description": f"{int(dup_mask.sum()):,} rows with duplicate item and date"
                }
        
        # negative values
        if qty_col and qty_col in df.columns:
            neg_mask = df[qty_col] < 0
            if neg_mask.any():
                self._abnormal_data["negative"] = {
                    "title": "Negative Values",
                    "data": df[neg_mask].copy(),
                    "description": f"{int(neg_mask.sum()):,} rows with negative quantities"
                }
        
        # outliers by z-score
        if qty_col and qty_col in df.columns:
            vals = df[qty_col].astype(float)
            mean = vals.mean()
            std = vals.std()
            if std and not np.isnan(std):
                z = (vals - mean) / std
                out_mask = (z > 3.0) | (z < -3.0)
                if out_mask.any():
                    self._abnormal_data["outliers"] = {
                        "title": "Outliers",
                        "data": df[out_mask].copy(),
                        "description": f"{int(out_mask.sum()):,} rows with values outside 3 standard deviations"
                    }
    
    # ---------- TABS ----------
    
    def _populate_tabs(self) -> None:
        # build tabs for each abnormal type
        if not self._abnormal_data:
            empty = QWidget()
            lay = QVBoxLayout(empty)
            msg = QLabel("✓ No abnormal data detected!")
            try:
                app = QApplication.instance()
                base_font = app.font() if app is not None else QFont()
                msg_font = QFont(base_font.family(), max(10, base_font.pointSize() + 2))
                msg.setFont(msg_font)
            except Exception:
                msg.setFont(QFont("Segoe UI", 14))
            msg.setAlignment(Qt.AlignCenter)
            msg.setStyleSheet("color: #28A745;")
            lay.addWidget(msg)
            self._tabs.addTab(empty, "All Clear")
            self._fix_group.setEnabled(False)
            self._export_csv_btn.setEnabled(False)
            self._export_excel_btn.setEnabled(False)
            self._apply_btn.setEnabled(False)
            return
        
        for key, info in self._abnormal_data.items():
            title = info["title"]
            df = info["data"]
            
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            tab_layout.setContentsMargins(0, 0, 0, 0)
            
            # description label
            desc = QLabel(info["description"])
            desc.setStyleSheet("font-weight: bold; margin-bottom: 8px;")
            tab_layout.addWidget(desc)
            
            # table without exclude column
            table = QTableWidget()
            table.setAlternatingRowColors(True)
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            # adjust header resize mode to avoid forcing wide dialogs
            try:
                header = table.horizontalHeader()
                # on small screens prefer stretching to keep dialog width reasonable
                scr = self.screen().availableGeometry()
                if scr.width() < 1200:
                    header.setSectionResizeMode(QHeaderView.Stretch)
                else:
                    header.setSectionResizeMode(QHeaderView.ResizeToContents)
                header.setStretchLastSection(True)
            except Exception:
                pass
            table.verticalHeader().setVisible(False)
            table.setSortingEnabled(True)
            
            # preview first 1000 rows
            preview = df.head(1000)
            cols = list(preview.columns)
            
            # set columns without exclude checkbox
            table.setColumnCount(len(cols))
            headers = [str(c) for c in cols]
            table.setHorizontalHeaderLabels(headers)
            
            table.setRowCount(len(preview))
            
            for row_idx, (orig_idx, row) in enumerate(preview.iterrows()):
                for j, col in enumerate(cols):
                    val = row[col]
                    text = "" if pd.isna(val) else str(val)
                    item = QTableWidgetItem(text)
                    
                    # highlight problematic cells
                    if pd.isna(val):
                        item.setBackground(QBrush(QColor("#FFCDD2")))
                    elif isinstance(val, (int, float)) and val < 0:
                        item.setBackground(QBrush(QColor("#FFCDD2")))
                    
                    table.setItem(row_idx, j, item)
            
            # Resize columns but avoid creating a very wide table on small screens
            try:
                table.resizeColumnsToContents()
            except Exception:
                pass
            
            tab_layout.addWidget(table)
            
            # info label for large datasets
            if len(df) > len(preview):
                info_label = QLabel(
                    f"Showing first {len(preview):,} of {len(df):,} rows. "
                    f"Export to CSV or Excel to see full abnormal dataset."
                )
                info_label.setStyleSheet("color: #666; font-style: italic;")
                tab_layout.addWidget(info_label)
            
            self._tabs.addTab(tab, f"{title} ({len(df):,})")
            self._tables[key] = table
            self._type_order.append(key)
    
    # ---------- FIX CONTROLS ----------
    
    def _setup_fix_controls(self) -> None:
        # build fix type controls
        def add_fix_row(
            key: str,
            title: str,
            description: str,
            enabled: bool,
            methods: List[tuple],
            default_method: str
        ) -> None:
            row = QWidget()
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 6)
            row_layout.setSpacing(2)
            
            # checkbox for fix type
            chk = QCheckBox(title)
            chk.setFont(QFont("Segoe UI", 10, QFont.Bold))
            chk.setEnabled(enabled)
            chk.setChecked(enabled)
            row_layout.addWidget(chk)
            
            # description
            desc = QLabel(description)
            desc.setStyleSheet("color: #666; margin-left: 20px; font-size: 9pt;")
            desc.setWordWrap(True)
            row_layout.addWidget(desc)
            
            # method selector
            method_layout = QHBoxLayout()
            method_layout.addSpacing(20)
            method_layout.addWidget(QLabel("Method:"))
            
            combo = QComboBox()
            for code, text in methods:
                combo.addItem(text, code)
            for idx in range(combo.count()):
                if combo.itemData(idx) == default_method:
                    combo.setCurrentIndex(idx)
                    break
            combo.setEnabled(enabled)
            method_layout.addWidget(combo)
            method_layout.addStretch()
            
            row_layout.addLayout(method_layout)
            
            self._fix_rows_layout.addWidget(row)
            self._fix_controls[key] = {"check": chk, "combo": combo}
        
        # missing values fix options
        add_fix_row(
            "missing",
            "Missing values",
            "Handle missing values in key columns.",
            enabled=("missing" in self._abnormal_data),
            methods=[
                ("ffill", "Forward fill (previous value)"),
                ("bfill", "Backward fill (next value)"),
                ("zero", "Set missing to zero"),
                ("mean", "Fill numeric with average"),
                ("remove", "Remove rows with missing values")
            ],
            default_method="ffill"
        )
        
        # duplicates
        add_fix_row(
            "duplicates",
            "Duplicate entries",
            "Handle rows with same item and date.",
            enabled=("duplicates" in self._abnormal_data),
            methods=[
                ("sum", "Sum quantities"),
                ("mean", "Average quantities"),
                ("first", "Keep first entry")
            ],
            default_method="sum"
        )
        
        # negative
        add_fix_row(
            "negative",
            "Negative values",
            "Handle negative quantities.",
            enabled=("negative" in self._abnormal_data),
            methods=[
                ("zero", "Set to zero"),
                ("absolute", "Use absolute value")
            ],
            default_method="zero"
        )
        
        # outliers
        add_fix_row(
            "outliers",
            "Outliers",
            "Handle rows with extreme values.",
            enabled=("outliers" in self._abnormal_data),
            methods=[
                ("remove", "Remove outlier rows"),
                ("cap", "Cap values to threshold")
            ],
            default_method="remove"
        )
    
    # ---------- SEARCH ----------
    
    def _apply_search_filter(self) -> None:
        # filter preview rows in current tab
        text = self._search_edit.text().lower().strip()
        if not self._type_order:
            return
        
        idx = self._tabs.currentIndex()
        if idx < 0 or idx >= len(self._type_order):
            return
        
        t_key = self._type_order[idx]
        table = self._tables.get(t_key)
        if table is None:
            return
        
        for row in range(table.rowCount()):
            if not text:
                table.setRowHidden(row, False)
                continue
            
            match = False
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if not item:
                    continue
                val = item.text().lower()
                if text in val:
                    match = True
                    break
            table.setRowHidden(row, not match)
    
    # ---------- EXPORT ----------
    
    def _get_current_type(self) -> Optional[str]:
        # get key for current tab
        idx = self._tabs.currentIndex()
        if idx < 0 or idx >= len(self._type_order):
            return None
        return self._type_order[idx]
    
    def _export_data(self, fmt: str) -> None:
        # export full abnormal dataset for current type
        t_key = self._get_current_type()
        if t_key is None:
            return
        
        info = self._abnormal_data.get(t_key)
        if not info:
            QMessageBox.warning(self, "No Data", "No abnormal data to export")
            return
        
        df = info["data"]
        if df.empty:
            QMessageBox.warning(self, "No Data", "No abnormal data to export")
            return
        
        if fmt == "csv":
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Abnormal Data to CSV",
                f"abnormal_{t_key}.csv",
                "CSV Files (*.csv)"
            )
            if not path:
                return
            df.to_csv(path, index=False)
        else:
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Abnormal Data to Excel",
                f"abnormal_{t_key}.xlsx",
                "Excel Files (*.xlsx)"
            )
            if not path:
                return
            df.to_excel(path, index=False, engine="openpyxl")
        
        QMessageBox.information(self, "Export Complete", f"Exported to:\n{path}")
    
    # ---------- APPLY FIXES ----------
    
    def _apply_fixes(self) -> None:
        # apply selected fixes to processor data
        if self._processor is None or self._processor.processed_data is None:
            QMessageBox.warning(self, "No Data", "No processed data to fix")
            return
        
        # collect selected fixes
        fix_specs: List[tuple] = []
        for key, ctrl in self._fix_controls.items():
            chk: QCheckBox = ctrl["check"]
            combo: QComboBox = ctrl["combo"]
            if chk.isEnabled() and chk.isChecked():
                method = combo.currentData()
                fix_specs.append((key, method))
        
        if not fix_specs:
            QMessageBox.information(
                self,
                "No Fixes Selected",
                "Please select at least one fix to apply."
            )
            return
        
        # description mapping for confirmation
        desc_map = {
            "missing": {
                "ffill": "fill missing with previous values",
                "bfill": "fill missing with next values",
                "zero": "set missing to zero",
                "mean": "fill missing numeric values with averages",
                "remove": "remove rows with missing values"
            },
            "duplicates": {
                "sum": "sum duplicate quantities",
                "mean": "average duplicate quantities",
                "first": "keep first duplicate row"
            },
            "negative": {
                "zero": "set negative quantities to zero",
                "absolute": "use absolute value of negative quantities"
            },
            "outliers": {
                "remove": "remove rows with outlier quantities",
                "cap": "cap outlier quantities to threshold"
            }
        }
        
        lines = []
        for f_type, method in fix_specs:
            txt = desc_map.get(f_type, {}).get(method, f"{f_type} ({method})")
            lines.append(f"• {txt}")
        
        msg = "\n".join(lines)
        
        reply = QMessageBox.question(
            self,
            "Confirm Fixes",
            f"The following fixes will be applied:\n\n{msg}\n\n"
            "This will modify your loaded data. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # apply each fix
        applied_msgs: List[str] = []
        for f_type, method in fix_specs:
            if f_type == "missing":
                ok, m = self._processor.apply_fix(
                    "fill_missing", method=method
                )
            elif f_type == "duplicates":
                ok, m = self._processor.apply_fix(
                    "remove_duplicates", method=method
                )
            elif f_type == "negative":
                ok, m = self._processor.apply_fix(
                    "fix_negatives", method=method
                )
            elif f_type == "outliers":
                ok, m = self._processor.apply_fix(
                    "remove_outliers", method=method, threshold=3.0
                )
            else:
                ok, m = False, f"unknown fix type: {f_type}"
            
            if ok:
                applied_msgs.append(m)
        
        if not applied_msgs:
            QMessageBox.information(
                self,
                "No Fixes Applied",
                "No fixes were successfully applied."
            )
            return
        
        text = "Applied the following fixes:\n" + "\n".join(
            [f"• {m}" for m in applied_msgs]
        )
        QMessageBox.information(self, "Fixes Applied", text)
        
        self.accept()