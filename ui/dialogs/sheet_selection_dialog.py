"""
sheet selection dialog module
allows user to select worksheet from excel files
displays sheet preview and row counts
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QFrame, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from typing import Dict, List, Optional, Any
import pandas as pd

import config


# ============================================================================
#                       SHEET SELECTION DIALOG
# ============================================================================

class SheetSelectionDialog(QDialog):
    # dialog for selecting excel worksheet
    
    # signals
    sheet_selected = pyqtSignal(str)
    
    def __init__(self, file_path: str, sheet_info: Dict[str, int], parent=None):
        # initialize dialog
        super().__init__(parent)
        
        self._file_path = file_path
        self._sheet_info = sheet_info  # {sheet_name: row_count}
        self._selected_sheet = None
        self._preview_data = {}
        
        self._setup_ui()
        self._populate_sheets()
    
    # ---------- UI SETUP ----------
    
    def _setup_ui(self) -> None:
        # setup user interface
        self.setWindowTitle("Select Worksheet")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # header
        header = QLabel("This Excel file contains multiple worksheets")
        header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout.addWidget(header)
        
        # file info
        file_name = self._file_path.split("/")[-1].split("\\")[-1]
        info_label = QLabel(f"📁 {file_name} • {len(self._sheet_info)} worksheet(s)")
        info_label.setStyleSheet("color: #666;")
        info_label.setToolTip("Excel file being imported")
        layout.addWidget(info_label)
        
        # splitter for sheet list and preview
        splitter = QSplitter(Qt.Horizontal)
        
        # left side - sheet list
        left_widget = QGroupBox("Available Worksheets")
        left_widget.setToolTip("Click a worksheet to see preview")
        left_layout = QVBoxLayout(left_widget)
        
        self._sheet_list = QListWidget()
        self._sheet_list.setAlternatingRowColors(True)
        self._sheet_list.itemClicked.connect(self._on_sheet_clicked)
        self._sheet_list.itemDoubleClicked.connect(self._on_sheet_double_clicked)
        self._sheet_list.setToolTip("Double-click to select and continue")
        left_layout.addWidget(self._sheet_list)
        
        # sheet count label
        self._count_label = QLabel("")
        self._count_label.setStyleSheet("color: #666; font-size: 10px;")
        left_layout.addWidget(self._count_label)
        
        splitter.addWidget(left_widget)
        
        # right side - preview
        right_widget = QGroupBox("Data Preview")
        right_widget.setToolTip("First 10 rows of selected worksheet")
        right_layout = QVBoxLayout(right_widget)
        
        self._preview_table = QTableWidget()
        self._preview_table.setAlternatingRowColors(True)
        self._preview_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._preview_table.horizontalHeader().setStretchLastSection(True)
        self._preview_table.setToolTip("Preview of worksheet data")
        right_layout.addWidget(self._preview_table)
        
        # preview info
        self._preview_info = QLabel("Select a worksheet to preview")
        self._preview_info.setStyleSheet("color: #666;")
        right_layout.addWidget(self._preview_info)
        
        splitter.addWidget(right_widget)
        
        # set splitter sizes
        splitter.setSizes([250, 450])
        
        layout.addWidget(splitter)
        
        # recommendation
        self._recommendation = QLabel("")
        self._recommendation.setWordWrap(True)
        self._recommendation.setStyleSheet("color: #2E86AB; font-style: italic;")
        layout.addWidget(self._recommendation)
        
        # buttons
        button_layout = QHBoxLayout()
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setToolTip("Cancel import")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self._select_btn = QPushButton("Select Worksheet")
        self._select_btn.setEnabled(False)
        self._select_btn.setToolTip("Use selected worksheet for import")
        self._select_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {config.UI_COLORS['primary']};
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #3A9CC0;
            }}
            QPushButton:disabled {{
                background-color: #ccc;
            }}
        """)
        self._select_btn.clicked.connect(self._on_select)
        button_layout.addWidget(self._select_btn)
        
        layout.addLayout(button_layout)
    
    # ---------- POPULATION ----------
    
    def _populate_sheets(self) -> None:
        # populate sheet list
        self._sheet_list.clear()
        
        largest_sheet = None
        largest_count = 0
        
        for sheet_name, row_count in self._sheet_info.items():
            # create list item
            item = QListWidgetItem()
            
            # format display text
            if row_count > 0:
                display_text = f"📊 {sheet_name} ({row_count:,} rows)"
            else:
                display_text = f"📄 {sheet_name} (empty)"
            
            item.setText(display_text)
            item.setData(Qt.UserRole, sheet_name)
            item.setToolTip(f"Worksheet: {sheet_name}\nRows: {row_count:,}")
            
            # track largest sheet
            if row_count > largest_count:
                largest_count = row_count
                largest_sheet = sheet_name
            
            self._sheet_list.addItem(item)
        
        # update count
        self._count_label.setText(f"{len(self._sheet_info)} worksheet(s) found")
        
        # set recommendation
        if largest_sheet and len(self._sheet_info) > 1:
            self._recommendation.setText(
                f"💡 Recommendation: '{largest_sheet}' has the most data ({largest_count:,} rows)"
            )
        
        # auto-select first sheet or largest
        if self._sheet_list.count() > 0:
            # find and select largest sheet
            for i in range(self._sheet_list.count()):
                item = self._sheet_list.item(i)
                if item.data(Qt.UserRole) == largest_sheet:
                    self._sheet_list.setCurrentItem(item)
                    self._on_sheet_clicked(item)
                    break
    
    # ---------- PREVIEW ----------
    
    def _on_sheet_clicked(self, item: QListWidgetItem) -> None:
        # handle sheet selection
        sheet_name = item.data(Qt.UserRole)
        self._selected_sheet = sheet_name
        self._select_btn.setEnabled(True)
        
        # load preview
        self._load_preview(sheet_name)
    
    def _on_sheet_double_clicked(self, item: QListWidgetItem) -> None:
        # handle double click - select and close
        self._on_sheet_clicked(item)
        self._on_select()
    
    def _load_preview(self, sheet_name: str) -> None:
        # load preview data for sheet
        try:
            # check cache
            if sheet_name in self._preview_data:
                df = self._preview_data[sheet_name]
            else:
                # load first 10 rows
                df = pd.read_excel(
                    self._file_path, 
                    sheet_name=sheet_name, 
                    nrows=10,
                    engine="openpyxl"
                )
                self._preview_data[sheet_name] = df
            
            # populate table
            self._preview_table.clear()
            self._preview_table.setRowCount(len(df))
            self._preview_table.setColumnCount(len(df.columns))
            self._preview_table.setHorizontalHeaderLabels([str(c) for c in df.columns])
            
            for i, row in df.iterrows():
                for j, value in enumerate(row):
                    cell_text = str(value) if pd.notna(value) else ""
                    item = QTableWidgetItem(cell_text)
                    item.setToolTip(cell_text)
                    self._preview_table.setItem(i, j, item)
            
            # resize columns
            self._preview_table.resizeColumnsToContents()
            
            # update info
            total_rows = self._sheet_info.get(sheet_name, 0)
            self._preview_info.setText(
                f"Showing first {len(df)} of {total_rows:,} rows • {len(df.columns)} columns"
            )
            
        except Exception as e:
            self._preview_info.setText(f"Error loading preview: {str(e)}")
            self._preview_table.clear()
    
    # ---------- ACTIONS ----------
    
    def _on_select(self) -> None:
        # handle select button
        if self._selected_sheet:
            self.sheet_selected.emit(self._selected_sheet)
            self.accept()
    
    def get_selected_sheet(self) -> Optional[str]:
        # get selected sheet name
        return self._selected_sheet