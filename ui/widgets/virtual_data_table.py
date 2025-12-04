"""
virtual data table widget
handles large datasets with virtual scrolling
optimized for 10k plus rows
"""

from PyQt5.QtWidgets import (
    QTableView, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QHeaderView,
    QMenu, QAction, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal, QSortFilterProxyModel
from PyQt5.QtGui import QFont
from typing import Optional, List
import pandas as pd

from ui.models.sku_table_model import SKUTableModel


# ============================================================================
#                         VIRTUAL DATA TABLE
# ============================================================================

class VirtualDataTable(QWidget):
    # table widget optimized for large datasets
    
    # signals
    row_selected = pyqtSignal(dict)
    row_double_clicked = pyqtSignal(dict)
    selection_changed = pyqtSignal(list)
    
    def __init__(self, parent=None):
        # initialize table widget
        super().__init__(parent)
        
        self._model = SKUTableModel(self)
        self._setup_ui()
        self._connect_signals()
    
    # ---------- UI SETUP ----------
    
    def _setup_ui(self) -> None:
        # setup user interface
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # toolbar
        toolbar = QHBoxLayout()
        
        # search box
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search...")
        self._search_box.setClearButtonEnabled(True)
        self._search_box.setMaximumWidth(250)
        toolbar.addWidget(self._search_box)
        
        # row count label
        self._count_label = QLabel("0 rows")
        toolbar.addWidget(self._count_label)
        
        toolbar.addStretch()
        
        # column selector button
        self._column_btn = QPushButton("Columns")
        self._column_btn.setMaximumWidth(100)
        toolbar.addWidget(self._column_btn)
        
        layout.addLayout(toolbar)
        
        # table view
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._table.setSortingEnabled(True)
        self._table.setWordWrap(False)
        
        # disable editing but allow selection and copying
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # optimize for large datasets
        self._table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._table.verticalHeader().setDefaultSectionSize(25)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        
        layout.addWidget(self._table)
    
    def _connect_signals(self) -> None:
        # connect widget signals
        self._search_box.textChanged.connect(self._on_search)
        self._column_btn.clicked.connect(self._show_column_menu)
        self._table.clicked.connect(self._on_row_clicked)
        self._table.doubleClicked.connect(self._on_row_double_clicked)
        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)
    
    # ---------- DATA MANAGEMENT ----------
    
    def set_data(self, data: pd.DataFrame, display_columns: Optional[List[str]] = None) -> None:
        # set table data
        self._model.set_data(data, display_columns)
        self._update_count_label()
        self._resize_columns()
    
    def get_data(self) -> pd.DataFrame:
        # get table data
        return self._model.get_data()
    
    def clear(self) -> None:
        # clear table data
        self._model.set_data(pd.DataFrame())
        self._update_count_label()
    
    # ---------- SELECTION ----------
    
    def get_selected_rows(self) -> List[dict]:
        # get selected row data
        selected = []
        for index in self._table.selectionModel().selectedRows():
            row_data = self._model.get_row_data(index.row())
            if row_data:
                selected.append(row_data)
        return selected
    
    def select_row(self, row: int) -> None:
        # select specific row
        if 0 <= row < self._model.rowCount():
            index = self._model.index(row, 0)
            self._table.selectRow(row)
            self._table.scrollTo(index)
    
    def clear_selection(self) -> None:
        # clear selection
        self._table.clearSelection()
    
    # ---------- COLUMNS ----------
    
    def set_display_columns(self, columns: List[str]) -> None:
        # set which columns to display
        self._model.set_display_columns(columns)
        self._resize_columns()
    
    def _show_column_menu(self) -> None:
        # show column selection menu
        menu = QMenu(self)
        
        all_columns = self._model.get_all_columns()
        display_columns = self._model.get_display_columns()
        
        for col in all_columns:
            action = QAction(col.replace("_", " ").title(), menu)
            action.setCheckable(True)
            action.setChecked(col in display_columns)
            action.setData(col)
            action.triggered.connect(self._toggle_column)
            menu.addAction(action)
        
        menu.exec_(self._column_btn.mapToGlobal(self._column_btn.rect().bottomLeft()))
    
    def _toggle_column(self) -> None:
        # toggle column visibility
        action = self.sender()
        col = action.data()
        
        display_columns = self._model.get_display_columns()
        
        if col in display_columns:
            if len(display_columns) > 1:
                display_columns.remove(col)
        else:
            display_columns.append(col)
        
        self._model.set_display_columns(display_columns)
        self._resize_columns()
    
    def _resize_columns(self) -> None:
        # resize columns to content
        self._table.resizeColumnsToContents()
        
        # limit max width
        header = self._table.horizontalHeader()
        for i in range(header.count()):
            if header.sectionSize(i) > 200:
                header.resizeSection(i, 200)
    
    # ---------- EVENT HANDLERS ----------
    
    def _on_search(self, text: str) -> None:
        # handle search text change
        self._model.set_filter(text)
        self._update_count_label()
    
    def _on_row_clicked(self, index) -> None:
        # handle row click
        row_data = self._model.get_row_data(index.row())
        if row_data:
            self.row_selected.emit(row_data)
    
    def _on_row_double_clicked(self, index) -> None:
        # handle row double click
        row_data = self._model.get_row_data(index.row())
        if row_data:
            self.row_double_clicked.emit(row_data)
    
    def _on_selection_changed(self) -> None:
        # handle selection change
        selected = self.get_selected_rows()
        self.selection_changed.emit(selected)
    
    def _update_count_label(self) -> None:
        # update row count label
        count = self._model.rowCount()
        total = len(self._model.get_data())
        
        if count == total:
            self._count_label.setText(f"{count:,} rows")
        else:
            self._count_label.setText(f"{count:,} of {total:,} rows")