"""
sku search and selection widget
filterable list with bookmarking
"""


# ================ IMPORTS ================

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QMenu, QCompleter
)
from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel
from PyQt6.QtGui import QAction

from typing import List, Optional

from core.state import STATE
from core.bookmarks import BOOKMARKS, BookmarkType


# ================ SKU SEARCH WIDGET ================

class SKUSearchWidget(QWidget):
    """
    sku search and selection widget
    """
    
    sku_selected = pyqtSignal(str)
    sku_double_clicked = pyqtSignal(str)
    selection_changed = pyqtSignal(list)
    
    def __init__(self, parent=None, multi_select: bool = False):
        super().__init__(parent)
        
        self._multi_select = multi_select
        self._all_skus = []
        
        self._create_ui()
        self._connect_signals()
    
    def _create_ui(self):
        """
        create widget ui
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # ---------- SEARCH BAR ----------
        search_layout = QHBoxLayout()
        search_layout.setSpacing(5)
        
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search SKUs...")
        self.txt_search.setClearButtonEnabled(True)
        search_layout.addWidget(self.txt_search)
        
        self.btn_clear = QPushButton("×")
        self.btn_clear.setFixedSize(24, 24)
        self.btn_clear.setToolTip("Clear search")
        search_layout.addWidget(self.btn_clear)
        
        layout.addLayout(search_layout)
        
        # ---------- SKU LIST ----------
        self.list_skus = QListWidget()
        
        if self._multi_select:
            self.list_skus.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        else:
            self.list_skus.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        
        self.list_skus.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        layout.addWidget(self.list_skus)
        
        # ---------- INFO LABEL ----------
        self.lbl_info = QLabel("0 SKUs")
        self.lbl_info.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.lbl_info)
        
        # ---------- ACTION BUTTONS ----------
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        
        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.setProperty("secondary", True)
        self.btn_select_all.setVisible(self._multi_select)
        btn_layout.addWidget(self.btn_select_all)
        
        self.btn_bookmark = QPushButton("Bookmark")
        self.btn_bookmark.setProperty("secondary", True)
        btn_layout.addWidget(self.btn_bookmark)
        
        layout.addLayout(btn_layout)
    
    def _connect_signals(self):
        """
        connect signals
        """
        self.txt_search.textChanged.connect(self._on_search_changed)
        self.btn_clear.clicked.connect(self._on_clear_search)
        
        self.list_skus.currentItemChanged.connect(self._on_item_changed)
        self.list_skus.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_skus.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_skus.customContextMenuRequested.connect(self._show_context_menu)
        
        self.btn_select_all.clicked.connect(self._on_select_all)
        self.btn_bookmark.clicked.connect(self._on_bookmark)
    
    # ================ PUBLIC METHODS ================
    
    def set_skus(self, skus: List[str]):
        """
        set available skus
        """
        self._all_skus = skus
        self._populate_list()
        
        # setup completer
        completer = QCompleter(skus)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.txt_search.setCompleter(completer)
    
    def refresh_from_state(self):
        """
        refresh skus from state
        """
        if STATE.sku_list:
            self.set_skus(STATE.sku_list)
    
    def get_selected_sku(self) -> Optional[str]:
        """
        get currently selected sku
        """
        item = self.list_skus.currentItem()
        return item.text() if item else None
    
    def get_selected_skus(self) -> List[str]:
        """
        get all selected skus
        """
        return [item.text() for item in self.list_skus.selectedItems()]
    
    def set_selected_sku(self, sku: str):
        """
        set selected sku
        """
        for i in range(self.list_skus.count()):
            item = self.list_skus.item(i)
            if item.text() == sku:
                self.list_skus.setCurrentItem(item)
                break
    
    def clear_selection(self):
        """
        clear selection
        """
        self.list_skus.clearSelection()
    
    def set_filter(self, text: str):
        """
        set search filter
        """
        self.txt_search.setText(text)
    
    # ================ SLOTS ================
    
    def _on_search_changed(self, text: str):
        """
        filter list based on search
        """
        self._populate_list(text)
    
    def _on_clear_search(self):
        """
        clear search
        """
        self.txt_search.clear()
    
    def _on_item_changed(self, current, previous):
        """
        handle item selection change
        """
        if current:
            self.sku_selected.emit(current.text())
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """
        handle double click
        """
        self.sku_double_clicked.emit(item.text())
    
    def _on_selection_changed(self):
        """
        handle selection change
        """
        selected = self.get_selected_skus()
        self.selection_changed.emit(selected)
    
    def _on_select_all(self):
        """
        select all visible items
        """
        self.list_skus.selectAll()
    
    def _on_bookmark(self):
        """
        bookmark selected skus
        """
        selected = self.get_selected_skus()
        
        if not selected:
            return
        
        if len(selected) == 1:
            BOOKMARKS.bookmark_sku(selected[0])
        else:
            BOOKMARKS.bookmark_skus(
                name=f"SKU Set ({len(selected)} items)",
                skus=selected
            )
    
    def _show_context_menu(self, position):
        """
        show context menu
        """
        item = self.list_skus.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        
        # view action
        view_action = QAction("View Details", self)
        view_action.triggered.connect(lambda: self.sku_double_clicked.emit(item.text()))
        menu.addAction(view_action)
        
        menu.addSeparator()
        
        # bookmark action
        bookmark_action = QAction("Bookmark", self)
        bookmark_action.triggered.connect(lambda: BOOKMARKS.bookmark_sku(item.text()))
        menu.addAction(bookmark_action)
        
        # check if bookmarked
        is_bookmarked = BOOKMARKS.is_bookmarked(item.text(), BookmarkType.SKU)
        if is_bookmarked:
            bookmark_action.setText("Already Bookmarked")
            bookmark_action.setEnabled(False)
        
        menu.exec(self.list_skus.mapToGlobal(position))
    
    # ================ HELPERS ================
    
    def _populate_list(self, filter_text: str = ""):
        """
        populate sku list
        """
        self.list_skus.clear()
        
        filter_lower = filter_text.lower()
        visible_count = 0
        
        for sku in self._all_skus:
            sku_str = str(sku)
            
            if filter_lower and filter_lower not in sku_str.lower():
                continue
            
            item = QListWidgetItem(sku_str)
            
            # mark bookmarked items
            if BOOKMARKS.is_bookmarked(sku_str, BookmarkType.SKU):
                item.setText(f"★ {sku_str}")
            
            self.list_skus.addItem(item)
            visible_count += 1
        
        # update info label
        total = len(self._all_skus)
        if filter_text:
            self.lbl_info.setText(f"{visible_count} of {total} SKUs")
        else:
            self.lbl_info.setText(f"{total} SKUs")