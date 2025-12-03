"""
sheet selection and column mapping dialogs
handle multi-sheet excel and column configuration
"""


# ================ IMPORTS ================

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem,
    QComboBox, QCheckBox, QScrollArea, QFrame,
    QGroupBox, QWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from typing import List, Optional, Dict
import pandas as pd


# ================ SHEET SELECTION DIALOG ================

class SheetSelectionDialog(QDialog):
    """
    excel sheet selection dialog
    """
    
    def __init__(self, parent=None, sheets: List[str] = None):
        super().__init__(parent)
        
        self.sheets = sheets or []
        self.selected_sheet = None
        
        self.setWindowTitle("Select Sheet")
        self.setMinimumSize(350, 300)
        self.setModal(True)
        
        self._create_ui()
    
    def _create_ui(self):
        """
        create dialog ui
        """
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # header
        lbl_header = QLabel("This file has multiple sheets.\nSelect which sheet to load:")
        lbl_header.setWordWrap(True)
        layout.addWidget(lbl_header)
        
        # sheet list
        self.list_sheets = QListWidget()
        
        for sheet in self.sheets:
            item = QListWidgetItem(sheet)
            self.list_sheets.addItem(item)
        
        if self.sheets:
            self.list_sheets.setCurrentRow(0)
        
        self.list_sheets.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.list_sheets)
        
        # buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("secondary", True)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        btn_load = QPushButton("Load Sheet")
        btn_load.clicked.connect(self._on_load)
        btn_layout.addWidget(btn_load)
        
        layout.addLayout(btn_layout)
    
    def _on_load(self):
        """
        handle load button click
        """
        current = self.list_sheets.currentItem()
        
        if current:
            self.selected_sheet = current.text()
            self.accept()
    
    def _on_double_click(self, item: QListWidgetItem):
        """
        handle double click
        """
        self.selected_sheet = item.text()
        self.accept()
    
    def get_selected_sheet(self) -> Optional[str]:
        """
        get selected sheet name
        """
        return self.selected_sheet


# ================ COLUMN MAPPER DIALOG ================

class ColumnMapperDialog(QDialog):
    """
    column mapping dialog
    map file columns to required fields
    """
    
    # ---------- KEYWORD HINTS ----------
    KEYWORDS = {
        'date': [
            'date', 'time', 'timestamp', 'day', 'period', 'month', 'year',
            'datetime', 'trans_date', 'transaction_date', 'order_date',
            'sale_date', 'invoice_date', 'created', 'created_at', 'posted'
        ],
        'sku': [
            'sku', 'product', 'item', 'code', 'article', 'name', 'id',
            'part', 'material', 'product_id', 'item_id', 'item_code',
            'product_code', 'part_number', 'article_number', 'upc', 'ean',
            'barcode', 'plu', 'stock_code', 'inventory_id', 'goods'
        ],
        'quantity': [
            'quantity', 'qty', 'amount', 'count', 'units', 'sales', 'demand',
            'sold', 'volume', 'stock', 'inventory', 'on_hand', 'ordered',
            'shipped', 'received', 'consumed', 'usage', 'movement', 'total'
        ]
    }
    
    # ---------- SIGNALS ----------
    mapping_complete = pyqtSignal(dict)
    
    def __init__(self, parent=None, df: pd.DataFrame = None):
        super().__init__(parent)
        
        self.df = df
        self.result_mapping = None
        self.columns = df.columns.tolist() if df is not None else []
        self.additional_columns = []
        
        self.setWindowTitle("Configure Columns")
        self.setMinimumSize(700, 650)
        self.setModal(True)
        
        self._create_ui()
        self._populate_preview()
        self._suggest_mapping()
    
    def _create_ui(self):
        """
        create dialog ui
        """
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # ---------- HEADER ----------
        header_layout = QVBoxLayout()
        
        lbl_title = QLabel("Configure Column Mapping")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(lbl_title)
        
        lbl_desc = QLabel(
            "Map your data columns to the required fields. "
            "The system will auto-detect likely matches."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: gray;")
        header_layout.addWidget(lbl_desc)
        
        layout.addLayout(header_layout)
        
        # ---------- DATA PREVIEW ----------
        preview_group = QGroupBox("Data Preview (first 5 rows)")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_table = QTableWidget()
        self.preview_table.setMaximumHeight(150)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.setAlternatingRowColors(True)
        preview_layout.addWidget(self.preview_table)
        
        layout.addWidget(preview_group)
        
        # ---------- REQUIRED COLUMNS ----------
        req_group = QGroupBox("Required Columns")
        req_layout = QVBoxLayout(req_group)
        
        # date column
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Date Column:"))
        date_layout.addSpacing(20)
        self.combo_date = QComboBox()
        self.combo_date.setMinimumWidth(200)
        self.combo_date.addItem("-- Select --", None)
        self.combo_date.addItems(self.columns)
        self.combo_date.currentIndexChanged.connect(self._on_mapping_changed)
        date_layout.addWidget(self.combo_date)
        self.lbl_date_sample = QLabel("")
        self.lbl_date_sample.setStyleSheet("color: gray; font-style: italic;")
        date_layout.addWidget(self.lbl_date_sample)
        date_layout.addStretch()
        req_layout.addLayout(date_layout)
        
        # sku column
        sku_layout = QHBoxLayout()
        sku_layout.addWidget(QLabel("SKU/Product Column:"))
        sku_layout.addSpacing(20)
        self.combo_sku = QComboBox()
        self.combo_sku.setMinimumWidth(200)
        self.combo_sku.addItem("-- Select --", None)
        self.combo_sku.addItems(self.columns)
        self.combo_sku.currentIndexChanged.connect(self._on_mapping_changed)
        sku_layout.addWidget(self.combo_sku)
        self.lbl_sku_sample = QLabel("")
        self.lbl_sku_sample.setStyleSheet("color: gray; font-style: italic;")
        sku_layout.addWidget(self.lbl_sku_sample)
        sku_layout.addStretch()
        req_layout.addLayout(sku_layout)
        
        # quantity column
        qty_layout = QHBoxLayout()
        qty_layout.addWidget(QLabel("Quantity Column:"))
        qty_layout.addSpacing(20)
        self.combo_qty = QComboBox()
        self.combo_qty.setMinimumWidth(200)
        self.combo_qty.addItem("-- Select --", None)
        self.combo_qty.addItems(self.columns)
        self.combo_qty.currentIndexChanged.connect(self._on_mapping_changed)
        qty_layout.addWidget(self.combo_qty)
        self.lbl_qty_sample = QLabel("")
        self.lbl_qty_sample.setStyleSheet("color: gray; font-style: italic;")
        qty_layout.addWidget(self.lbl_qty_sample)
        qty_layout.addStretch()
        req_layout.addLayout(qty_layout)
        
        layout.addWidget(req_group)
        
        # ---------- ADDITIONAL COLUMNS ----------
        add_group = QGroupBox("Additional Columns (Optional Features)")
        add_layout = QVBoxLayout(add_group)
        
        add_desc = QLabel("Select additional columns to use as features for forecasting:")
        add_desc.setStyleSheet("color: gray;")
        add_layout.addWidget(add_desc)
        
        # scroll area for checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(120)
        
        scroll_content = QWidget()
        self.checkbox_layout = QHBoxLayout(scroll_content)
        self.checkbox_layout.setSpacing(15)
        
        self.checkboxes = {}
        for col in self.columns:
            chk = QCheckBox(col)
            chk.stateChanged.connect(self._on_additional_changed)
            self.checkboxes[col] = chk
            self.checkbox_layout.addWidget(chk)
        
        self.checkbox_layout.addStretch()
        scroll.setWidget(scroll_content)
        add_layout.addWidget(scroll)
        
        # select/deselect buttons
        btn_row = QHBoxLayout()
        
        btn_select_all = QPushButton("Select All")
        btn_select_all.setProperty("secondary", True)
        btn_select_all.clicked.connect(self._select_all)
        btn_row.addWidget(btn_select_all)
        
        btn_deselect_all = QPushButton("Deselect All")
        btn_deselect_all.setProperty("secondary", True)
        btn_deselect_all.clicked.connect(self._deselect_all)
        btn_row.addWidget(btn_deselect_all)
        
        btn_row.addStretch()
        
        self.lbl_additional_count = QLabel("0 additional columns selected")
        self.lbl_additional_count.setStyleSheet("color: gray;")
        btn_row.addWidget(self.lbl_additional_count)
        
        add_layout.addLayout(btn_row)
        
        layout.addWidget(add_group)
        
        # ---------- VALIDATION STATUS ----------
        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)
        
        # ---------- BUTTONS ----------
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("secondary", True)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        self.btn_confirm = QPushButton("Apply Mapping")
        self.btn_confirm.clicked.connect(self._confirm)
        self.btn_confirm.setEnabled(False)
        btn_layout.addWidget(self.btn_confirm)
        
        layout.addLayout(btn_layout)
    
    def _populate_preview(self):
        """
        populate data preview table
        """
        if self.df is None or len(self.df) == 0:
            return
        
        preview_df = self.df.head(5)
        
        self.preview_table.setRowCount(len(preview_df))
        self.preview_table.setColumnCount(len(preview_df.columns))
        self.preview_table.setHorizontalHeaderLabels([str(c) for c in preview_df.columns])
        
        for row_idx, row in preview_df.iterrows():
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(str(value) if pd.notna(value) else "")
                self.preview_table.setItem(row_idx, col_idx, item)
        
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    
    def _suggest_mapping(self):
        """
        auto-suggest column mappings based on keywords
        """
        date_found = False
        sku_found = False
        qty_found = False
        
        for col in self.columns:
            col_lower = col.lower().strip().replace('_', '').replace('-', '').replace(' ', '')
            
            # check date
            if not date_found:
                for keyword in self.KEYWORDS['date']:
                    if keyword.replace('_', '') in col_lower:
                        self.combo_date.setCurrentText(col)
                        date_found = True
                        break
            
            # check sku
            if not sku_found:
                for keyword in self.KEYWORDS['sku']:
                    if keyword.replace('_', '') in col_lower:
                        self.combo_sku.setCurrentText(col)
                        sku_found = True
                        break
            
            # check quantity
            if not qty_found:
                for keyword in self.KEYWORDS['quantity']:
                    if keyword.replace('_', '') in col_lower:
                        self.combo_qty.setCurrentText(col)
                        qty_found = True
                        break
        
        self._on_mapping_changed()
    
    def _on_mapping_changed(self):
        """
        handle mapping selection change
        """
        date_col = self.combo_date.currentText()
        sku_col = self.combo_sku.currentText()
        qty_col = self.combo_qty.currentText()
        
        # update sample labels
        if date_col and date_col != "-- Select --" and self.df is not None:
            sample = self.df[date_col].dropna().head(3).tolist()
            self.lbl_date_sample.setText(f"e.g., {sample}")
        else:
            self.lbl_date_sample.setText("")
        
        if sku_col and sku_col != "-- Select --" and self.df is not None:
            sample = self.df[sku_col].dropna().head(3).tolist()
            self.lbl_sku_sample.setText(f"e.g., {sample}")
        else:
            self.lbl_sku_sample.setText("")
        
        if qty_col and qty_col != "-- Select --" and self.df is not None:
            sample = self.df[qty_col].dropna().head(3).tolist()
            self.lbl_qty_sample.setText(f"e.g., {sample}")
        else:
            self.lbl_qty_sample.setText("")
        
        # update checkbox states
        required = {date_col, sku_col, qty_col}
        for col, chk in self.checkboxes.items():
            if col in required:
                chk.setChecked(False)
                chk.setEnabled(False)
                chk.setStyleSheet("color: gray;")
            else:
                chk.setEnabled(True)
                chk.setStyleSheet("")
        
        # validate
        self._validate_mapping()
    
    def _on_additional_changed(self):
        """
        handle additional column checkbox change
        """
        count = sum(1 for chk in self.checkboxes.values() if chk.isChecked() and chk.isEnabled())
        self.lbl_additional_count.setText(f"{count} additional columns selected")
    
    def _validate_mapping(self) -> bool:
        """
        validate current mapping
        """
        date_col = self.combo_date.currentText()
        sku_col = self.combo_sku.currentText()
        qty_col = self.combo_qty.currentText()
        
        errors = []
        
        # check selections made
        if date_col == "-- Select --":
            errors.append("Date column not selected")
        if sku_col == "-- Select --":
            errors.append("SKU column not selected")
        if qty_col == "-- Select --":
            errors.append("Quantity column not selected")
        
        # check uniqueness
        selected = [c for c in [date_col, sku_col, qty_col] if c != "-- Select --"]
        if len(selected) != len(set(selected)):
            errors.append("Each column must be different")
        
        # validate data types if possible
        if self.df is not None and not errors:
            # check quantity is numeric
            if qty_col in self.df.columns:
                qty_numeric = pd.to_numeric(self.df[qty_col], errors='coerce')
                valid_pct = qty_numeric.notna().sum() / len(self.df) * 100
                if valid_pct < 50:
                    errors.append(f"Quantity column has only {valid_pct:.0f}% numeric values")
        
        # update status
        if errors:
            self.lbl_status.setText("⚠ " + "; ".join(errors))
            self.lbl_status.setStyleSheet("color: #f44336;")
            self.btn_confirm.setEnabled(False)
            return False
        else:
            self.lbl_status.setText("✓ Mapping valid")
            self.lbl_status.setStyleSheet("color: #4caf50;")
            self.btn_confirm.setEnabled(True)
            return True
    
    def _select_all(self):
        """
        select all additional columns
        """
        for chk in self.checkboxes.values():
            if chk.isEnabled():
                chk.setChecked(True)
        self._on_additional_changed()
    
    def _deselect_all(self):
        """
        deselect all additional columns
        """
        for chk in self.checkboxes.values():
            chk.setChecked(False)
        self._on_additional_changed()
    
    def _confirm(self):
        """
        confirm mapping and close
        """
        if not self._validate_mapping():
            return
        
        date_col = self.combo_date.currentText()
        sku_col = self.combo_sku.currentText()
        qty_col = self.combo_qty.currentText()
        
        # get additional columns
        required = {date_col, sku_col, qty_col}
        self.additional_columns = [
            col for col, chk in self.checkboxes.items()
            if chk.isChecked() and chk.isEnabled() and col not in required
        ]
        
        # build result mapping
        self.result_mapping = {
            'date_column': date_col,
            'sku_column': sku_col,
            'quantity_column': qty_col,
            'additional_columns': self.additional_columns,
            'rename_map': {
                date_col: 'Date',
                sku_col: 'SKU',
                qty_col: 'Quantity'
            }
        }
        
        self.mapping_complete.emit(self.result_mapping)
        self.accept()
    
    def get_mapping(self) -> Optional[Dict]:
        """
        get result mapping
        """
        return self.result_mapping
    
    def get_mapped_dataframe(self) -> Optional[pd.DataFrame]:
        """
        get dataframe with columns renamed
        """
        if self.result_mapping is None or self.df is None:
            return None
        
        mapping = self.result_mapping
        
        # select columns
        columns_to_keep = [
            mapping['date_column'],
            mapping['sku_column'],
            mapping['quantity_column']
        ] + mapping['additional_columns']
        
        result_df = self.df[columns_to_keep].copy()
        result_df = result_df.rename(columns=mapping['rename_map'])
        
        return result_df