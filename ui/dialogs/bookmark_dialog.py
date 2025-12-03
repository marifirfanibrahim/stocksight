"""
bookmark management dialog
view, edit, and organize bookmarks
"""


# ================ IMPORTS ================

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem,
    QLineEdit, QComboBox, QTextEdit, QGroupBox,
    QSplitter, QMenu, QMessageBox, QInputDialog,
    QTabWidget, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction

from datetime import datetime

from core.bookmarks import BOOKMARKS, BookmarkType
from core.state import Bookmark


# ================ BOOKMARK DIALOG ================

class BookmarkDialog(QDialog):
    """
    bookmark management dialog
    """
    
    bookmark_selected = pyqtSignal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Bookmarks")
        self.setMinimumSize(600, 500)
        self.setModal(False)
        
        self._current_bookmark = None
        
        self._create_ui()
        self._connect_signals()
        self._refresh_lists()
    
    def _create_ui(self):
        """
        create dialog ui
        """
        layout = QHBoxLayout(self)
        layout.setSpacing(15)
        
        # ---------- LEFT PANEL - BOOKMARK LISTS ----------
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # search
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search bookmarks...")
        self.txt_search.setClearButtonEnabled(True)
        left_layout.addWidget(self.txt_search)
        
        # tabs for bookmark types
        self.tabs = QTabWidget()
        
        # all bookmarks
        self.list_all = QListWidget()
        self.list_all.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.addTab(self.list_all, "All")
        
        # sku bookmarks
        self.list_skus = QListWidget()
        self.list_skus.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.addTab(self.list_skus, "SKUs")
        
        # anomaly bookmarks
        self.list_anomalies = QListWidget()
        self.list_anomalies.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.addTab(self.list_anomalies, "Anomalies")
        
        # forecast bookmarks
        self.list_forecasts = QListWidget()
        self.list_forecasts.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.addTab(self.list_forecasts, "Forecasts")
        
        # feature bookmarks
        self.list_features = QListWidget()
        self.list_features.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.addTab(self.list_features, "Features")
        
        left_layout.addWidget(self.tabs)
        
        # ---------- RIGHT PANEL - DETAILS ----------
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # details group
        details_group = QGroupBox("Bookmark Details")
        details_layout = QVBoxLayout(details_group)
        
        # name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.txt_name = QLineEdit()
        name_layout.addWidget(self.txt_name)
        details_layout.addLayout(name_layout)
        
        # type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        self.lbl_type = QLabel("--")
        self.lbl_type.setStyleSheet("color: gray;")
        type_layout.addWidget(self.lbl_type)
        type_layout.addStretch()
        details_layout.addLayout(type_layout)
        
        # created
        created_layout = QHBoxLayout()
        created_layout.addWidget(QLabel("Created:"))
        self.lbl_created = QLabel("--")
        self.lbl_created.setStyleSheet("color: gray;")
        created_layout.addWidget(self.lbl_created)
        created_layout.addStretch()
        details_layout.addLayout(created_layout)
        
        # items
        details_layout.addWidget(QLabel("Items:"))
        self.list_items = QListWidget()
        self.list_items.setMaximumHeight(150)
        details_layout.addWidget(self.list_items)
        
        # notes
        details_layout.addWidget(QLabel("Notes:"))
        self.txt_notes = QTextEdit()
        self.txt_notes.setMaximumHeight(100)
        details_layout.addWidget(self.txt_notes)
        
        right_layout.addWidget(details_group)
        
        # action buttons
        action_layout = QHBoxLayout()
        
        self.btn_save = QPushButton("Save Changes")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._save_bookmark)
        action_layout.addWidget(self.btn_save)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setProperty("secondary", True)
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._delete_bookmark)
        action_layout.addWidget(self.btn_delete)
        
        self.btn_go_to = QPushButton("Go To")
        self.btn_go_to.setEnabled(False)
        self.btn_go_to.clicked.connect(self._go_to_bookmark)
        action_layout.addWidget(self.btn_go_to)
        
        right_layout.addLayout(action_layout)
        
        right_layout.addStretch()
        
        # ---------- SPLITTER ----------
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 300])
        
        layout.addWidget(splitter)
    
    def _connect_signals(self):
        """
        connect signals
        """
        self.txt_search.textChanged.connect(self._on_search)
        
        # list selection
        self.list_all.currentItemChanged.connect(self._on_item_selected)
        self.list_skus.currentItemChanged.connect(self._on_item_selected)
        self.list_anomalies.currentItemChanged.connect(self._on_item_selected)
        self.list_forecasts.currentItemChanged.connect(self._on_item_selected)
        self.list_features.currentItemChanged.connect(self._on_item_selected)
        
        # context menus
        self.list_all.customContextMenuRequested.connect(self._show_context_menu)
        self.list_skus.customContextMenuRequested.connect(self._show_context_menu)
        self.list_anomalies.customContextMenuRequested.connect(self._show_context_menu)
        self.list_forecasts.customContextMenuRequested.connect(self._show_context_menu)
        self.list_features.customContextMenuRequested.connect(self._show_context_menu)
        
        # text changes
        self.txt_name.textChanged.connect(lambda: self.btn_save.setEnabled(True))
        self.txt_notes.textChanged.connect(lambda: self.btn_save.setEnabled(True))
        
        # bookmark updates
        BOOKMARKS.add_callback(self._on_bookmark_change)
    
    def _refresh_lists(self):
        """
        refresh all bookmark lists
        """
        self.list_all.clear()
        self.list_skus.clear()
        self.list_anomalies.clear()
        self.list_forecasts.clear()
        self.list_features.clear()
        
        bookmarks = BOOKMARKS.get_all()
        
        for bookmark in bookmarks:
            item = QListWidgetItem(bookmark.name)
            item.setData(Qt.ItemDataRole.UserRole, bookmark.id)
            
            self.list_all.addItem(item)
            
            # add to type-specific list
            if bookmark.bookmark_type == BookmarkType.SKU:
                item2 = QListWidgetItem(bookmark.name)
                item2.setData(Qt.ItemDataRole.UserRole, bookmark.id)
                self.list_skus.addItem(item2)
            elif bookmark.bookmark_type == BookmarkType.ANOMALY_SET:
                item2 = QListWidgetItem(bookmark.name)
                item2.setData(Qt.ItemDataRole.UserRole, bookmark.id)
                self.list_anomalies.addItem(item2)
            elif bookmark.bookmark_type == BookmarkType.FORECAST:
                item2 = QListWidgetItem(bookmark.name)
                item2.setData(Qt.ItemDataRole.UserRole, bookmark.id)
                self.list_forecasts.addItem(item2)
            elif bookmark.bookmark_type == BookmarkType.FEATURE_SET:
                item2 = QListWidgetItem(bookmark.name)
                item2.setData(Qt.ItemDataRole.UserRole, bookmark.id)
                self.list_features.addItem(item2)
    
    def _on_search(self, text: str):
        """
        filter bookmarks
        """
        text_lower = text.lower()
        
        for list_widget in [self.list_all, self.list_skus, self.list_anomalies,
                           self.list_forecasts, self.list_features]:
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                match = text_lower in item.text().lower()
                item.setHidden(not match)
    
    def _on_item_selected(self, current, previous):
        """
        handle bookmark selection
        """
        if current is None:
            self._clear_details()
            return
        
        bookmark_id = current.data(Qt.ItemDataRole.UserRole)
        bookmark = BOOKMARKS.get(bookmark_id)
        
        if bookmark:
            self._display_bookmark(bookmark)
    
    def _display_bookmark(self, bookmark: Bookmark):
        """
        display bookmark details
        """
        self._current_bookmark = bookmark
        
        self.txt_name.setText(bookmark.name)
        self.lbl_type.setText(bookmark.bookmark_type.replace('_', ' ').title())
        self.lbl_created.setText(bookmark.created_at.strftime('%Y-%m-%d %H:%M'))
        
        self.list_items.clear()
        for item in bookmark.items:
            self.list_items.addItem(item)
        
        self.txt_notes.setText(bookmark.notes)
        
        self.btn_save.setEnabled(False)
        self.btn_delete.setEnabled(True)
        self.btn_go_to.setEnabled(True)
    
    def _clear_details(self):
        """
        clear detail panel
        """
        self._current_bookmark = None
        
        self.txt_name.clear()
        self.lbl_type.setText("--")
        self.lbl_created.setText("--")
        self.list_items.clear()
        self.txt_notes.clear()
        
        self.btn_save.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self.btn_go_to.setEnabled(False)
    
    def _save_bookmark(self):
        """
        save bookmark changes
        """
        if self._current_bookmark is None:
            return
        
        BOOKMARKS.update(
            self._current_bookmark.id,
            name=self.txt_name.text(),
            notes=self.txt_notes.toPlainText()
        )
        
        self.btn_save.setEnabled(False)
        self._refresh_lists()
    
    def _delete_bookmark(self):
        """
        delete current bookmark
        """
        if self._current_bookmark is None:
            return
        
        reply = QMessageBox.question(
            self,
            "Delete Bookmark",
            f"Delete '{self._current_bookmark.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            BOOKMARKS.delete(self._current_bookmark.id)
            self._clear_details()
            self._refresh_lists()
    
    def _go_to_bookmark(self):
        """
        navigate to bookmarked item
        """
        if self._current_bookmark is None:
            return
        
        self.bookmark_selected.emit(
            self._current_bookmark.bookmark_type,
            self._current_bookmark.id
        )
    
    def _show_context_menu(self, position):
        """
        show context menu
        """
        list_widget = self.sender()
        item = list_widget.itemAt(position)
        
        if item is None:
            return
        
        menu = QMenu(self)
        
        # go to
        go_action = QAction("Go To", self)
        go_action.triggered.connect(self._go_to_bookmark)
        menu.addAction(go_action)
        
        menu.addSeparator()
        
        # rename
        rename_action = QAction("Rename", self)
        rename_action.triggered.connect(self._rename_bookmark)
        menu.addAction(rename_action)
        
        # delete
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self._delete_bookmark)
        menu.addAction(delete_action)
        
        menu.exec(list_widget.mapToGlobal(position))
    
    def _rename_bookmark(self):
        """
        rename current bookmark
        """
        if self._current_bookmark is None:
            return
        
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Bookmark",
            "New name:",
            text=self._current_bookmark.name
        )
        
        if ok and new_name:
            BOOKMARKS.update(self._current_bookmark.id, name=new_name)
            self._refresh_lists()
    
    def _on_bookmark_change(self, action: str, bookmark_id: str):
        """
        handle bookmark system change
        """
        self._refresh_lists()