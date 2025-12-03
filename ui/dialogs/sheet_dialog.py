"""
sheet selection dialog
select sheet from multi-sheet excel file
"""


# ================ IMPORTS ================

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt

from typing import List, Optional


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
    
    KEYWORDS = {
        'date': ['date', 'time', 'timestamp', 'day', 'period'],
        'sku': ['sku', 'product', 'item', 'code', 'article', 'name', 'id'],
        'quantity': ['quantity', 'qty', 'amount', 'count', 'units', 'sales', 'demand', 'sold']
    }
    
    def __init__(self, parent=None, df=None):
        super().__init__(parent)
        
        self.df = df
        self.result_df = None
        self.columns = df.columns.tolist() if df is not None else []
        self.additional_columns = []
        
        self.setWindowTitle("Column Mapping")
        self.setMinimumSize(500, 550)
        self.setModal(True)
        
        self._create_ui()
        self._suggest_mapping()
    
    def _create_ui(self):
        """
        create dialog ui
        """
        from PyQt6.QtWidgets import QComboBox, QCheckBox, QScrollArea, QFrame, QGroupBox, QWidget
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # header
        lbl_header = QLabel("Map your data columns to required fields:")
        layout.addWidget(lbl_header)
        
        # required columns
        req_group = QGroupBox("Required Columns")
        req_layout = QVBoxLayout(req_group)
        
        # date
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Date:"))
        self.combo_date = QComboBox()
        self.combo_date.addItems(self.columns)
        date_layout.addWidget(self.combo_date)
        req_layout.addLayout(date_layout)
        
        # sku
        sku_layout = QHBoxLayout()
        sku_layout.addWidget(QLabel("SKU/Product:"))
        self.combo_sku = QComboBox()
        self.combo_sku.addItems(self.columns)
        sku_layout.addWidget(self.combo_sku)
        req_layout.addLayout(sku_layout)
        
        # quantity
        qty_layout = QHBoxLayout()
        qty_layout.addWidget(QLabel("Quantity:"))
        self.combo_qty = QComboBox()
        self.combo_qty.addItems(self.columns)
        qty_layout.addWidget(self.combo_qty)
        req_layout.addLayout(qty_layout)
        
        layout.addWidget(req_group)
        
        # additional columns
        add_group = QGroupBox("Additional Columns (Optional)")
        add_layout = QVBoxLayout(add_group)
        
        add_layout.addWidget(QLabel("Select extra columns to include:"))
        
        # scroll area for checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(150)
        
        scroll_content = QWidget()
        self.checkbox_layout = QVBoxLayout(scroll_content)
        self.checkbox_layout.setSpacing(2)
        
        self.checkboxes = {}
        for col in self.columns:
            chk = QCheckBox(col)
            self.checkboxes[col] = chk
            self.checkbox_layout.addWidget(chk)
        
        self.checkbox_layout.addStretch()
        scroll.setWidget(scroll_content)
        add_layout.addWidget(scroll)
        
        # select/deselect buttons
        btn_row = QHBoxLayout()
        btn_select_all = QPushButton("Select All")
        btn_select_all.clicked.connect(self._select_all)
        btn_row.addWidget(btn_select_all)
        
        btn_deselect_all = QPushButton("Deselect All")
        btn_deselect_all.clicked.connect(self._deselect_all)
        btn_row.addWidget(btn_deselect_all)
        btn_row.addStretch()
        add_layout.addLayout(btn_row)
        
        layout.addWidget(add_group)
        
        # message label
        self.lbl_message = QLabel("")
        self.lbl_message.setStyleSheet("color: #f44336;")
        layout.addWidget(self.lbl_message)
        
        # buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("secondary", True)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        btn_confirm = QPushButton("Confirm")
        btn_confirm.clicked.connect(self._confirm)
        btn_layout.addWidget(btn_confirm)
        
        layout.addLayout(btn_layout)
    
    def _suggest_mapping(self):
        """
        auto-suggest column mappings
        """
        for col in self.columns:
            col_lower = col.lower().strip()
            
            for field, keywords in self.KEYWORDS.items():
                for keyword in keywords:
                    if keyword in col_lower:
                        if field == 'date':
                            self.combo_date.setCurrentText(col)
                        elif field == 'sku':
                            self.combo_sku.setCurrentText(col)
                        elif field == 'quantity':
                            self.combo_qty.setCurrentText(col)
                        break
    
    def _select_all(self):
        """
        select all additional columns
        """
        for chk in self.checkboxes.values():
            chk.setChecked(True)
    
    def _deselect_all(self):
        """
        deselect all additional columns
        """
        for chk in self.checkboxes.values():
            chk.setChecked(False)
    
    def _confirm(self):
        """
        confirm mapping and close
        """
        date_col = self.combo_date.currentText()
        sku_col = self.combo_sku.currentText()
        qty_col = self.combo_qty.currentText()
        
        # validate
        if not date_col or not sku_col or not qty_col:
            self.lbl_message.setText("Please select all required columns")
            return
        
        if len(set([date_col, sku_col, qty_col])) < 3:
            self.lbl_message.setText("Each column must be different")
            return
        
        # get additional columns
        required = {date_col, sku_col, qty_col}
        self.additional_columns = [
            col for col, chk in self.checkboxes.items()
            if chk.isChecked() and col not in required
        ]
        
        # create result dataframe
        rename_map = {
            date_col: 'Date',
            sku_col: 'SKU',
            qty_col: 'Quantity'
        }
        
        columns_to_keep = [date_col, sku_col, qty_col] + self.additional_columns
        self.result_df = self.df[columns_to_keep].rename(columns=rename_map)
        
        # store mapping in state
        from core.state import STATE
        STATE.column_mapping = {
            'Date': date_col,
            'SKU': sku_col,
            'Quantity': qty_col
        }
        STATE.additional_columns = self.additional_columns
        
        self.accept()