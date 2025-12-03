"""
feature table widget
display and manage feature selection
"""


# ================ IMPORTS ================

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QCheckBox, QMenu,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QAction

from typing import Dict, List, Optional


# ================ FEATURE TABLE WIDGET ================

class FeatureTableWidget(QWidget):
    """
    feature display and selection table
    """
    
    selection_changed = pyqtSignal(list)
    feature_toggled = pyqtSignal(str, bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._features = []
        self._importance = {}
        self._selected = set()
        self._groups = {}
        
        self._create_ui()
        self._connect_signals()
    
    def _create_ui(self):
        """
        create widget ui
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # ---------- SEARCH ----------
        search_layout = QHBoxLayout()
        
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Filter features...")
        self.txt_search.setClearButtonEnabled(True)
        search_layout.addWidget(self.txt_search)
        
        layout.addLayout(search_layout)
        
        # ---------- TABLE ----------
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['', 'Feature', 'Importance', 'Group'])
        
        # column sizing
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 100)
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        # enable sorting
        self.table.setSortingEnabled(True)
        
        layout.addWidget(self.table)
        
        # ---------- INFO ----------
        info_layout = QHBoxLayout()
        
        self.lbl_info = QLabel("0 features")
        self.lbl_info.setStyleSheet("color: gray; font-size: 10px;")
        info_layout.addWidget(self.lbl_info)
        
        info_layout.addStretch()
        
        self.lbl_selected = QLabel("0 selected")
        self.lbl_selected.setStyleSheet("color: #0078d4; font-size: 10px;")
        info_layout.addWidget(self.lbl_selected)
        
        layout.addLayout(info_layout)
        
        # ---------- BUTTONS ----------
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        
        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.setProperty("secondary", True)
        btn_layout.addWidget(self.btn_select_all)
        
        self.btn_deselect_all = QPushButton("Deselect All")
        self.btn_deselect_all.setProperty("secondary", True)
        btn_layout.addWidget(self.btn_deselect_all)
        
        self.btn_select_top = QPushButton("Top 20")
        self.btn_select_top.setProperty("secondary", True)
        btn_layout.addWidget(self.btn_select_top)
        
        layout.addLayout(btn_layout)
    
    def _connect_signals(self):
        """
        connect signals
        """
        self.txt_search.textChanged.connect(self._on_search_changed)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        self.btn_select_all.clicked.connect(self._select_all)
        self.btn_deselect_all.clicked.connect(self._deselect_all)
        self.btn_select_top.clicked.connect(self._select_top)
    
    # ================ PUBLIC METHODS ================
    
    def set_features(
        self,
        features: List[str],
        importance: Dict[str, float] = None,
        groups: Dict[str, str] = None,
        selected: List[str] = None
    ):
        """
        set features to display
        """
        self._features = features
        self._importance = importance or {}
        self._groups = groups or {}
        self._selected = set(selected) if selected else set()
        
        self._populate_table()
    
    def get_selected(self) -> List[str]:
        """
        get selected features
        """
        return list(self._selected)
    
    def set_selected(self, features: List[str]):
        """
        set selected features
        """
        self._selected = set(features)
        self._update_checkboxes()
        self._update_info()
    
    def select_feature(self, feature: str, selected: bool = True):
        """
        select or deselect a feature
        """
        if selected:
            self._selected.add(feature)
        else:
            self._selected.discard(feature)
        
        self._update_checkboxes()
        self._update_info()
        self.feature_toggled.emit(feature, selected)
    
    def update_importance(self, importance: Dict[str, float]):
        """
        update importance scores
        """
        self._importance = importance
        self._update_importance_column()
    
    def clear(self):
        """
        clear all features
        """
        self._features = []
        self._importance = {}
        self._selected = set()
        self._groups = {}
        self.table.setRowCount(0)
        self._update_info()
    
    # ================ SLOTS ================
    
    def _on_search_changed(self, text: str):
        """
        filter table based on search
        """
        text_lower = text.lower()
        
        for row in range(self.table.rowCount()):
            feature_item = self.table.item(row, 1)
            
            if feature_item:
                match = text_lower in feature_item.text().lower()
                self.table.setRowHidden(row, not match)
    
    def _on_checkbox_changed(self, feature: str, state: int):
        """
        handle checkbox state change
        """
        selected = state == Qt.CheckState.Checked.value
        
        if selected:
            self._selected.add(feature)
        else:
            self._selected.discard(feature)
        
        self._update_info()
        self.feature_toggled.emit(feature, selected)
        self.selection_changed.emit(list(self._selected))
    
    def _select_all(self):
        """
        select all features
        """
        self._selected = set(self._features)
        self._update_checkboxes()
        self._update_info()
        self.selection_changed.emit(list(self._selected))
    
    def _deselect_all(self):
        """
        deselect all features
        """
        self._selected = set()
        self._update_checkboxes()
        self._update_info()
        self.selection_changed.emit(list(self._selected))
    
    def _select_top(self, n: int = 20):
        """
        select top n features by importance
        """
        if not self._importance:
            return
        
        sorted_features = sorted(
            self._importance.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        top_features = [f[0] for f in sorted_features[:n]]
        self._selected = set(top_features)
        self._update_checkboxes()
        self._update_info()
        self.selection_changed.emit(list(self._selected))
    
    def _show_context_menu(self, position):
        """
        show context menu
        """
        row = self.table.rowAt(position.y())
        if row < 0:
            return
        
        feature_item = self.table.item(row, 1)
        if not feature_item:
            return
        
        feature = feature_item.text()
        
        menu = QMenu(self)
        
        # toggle selection
        is_selected = feature in self._selected
        toggle_action = QAction("Deselect" if is_selected else "Select", self)
        toggle_action.triggered.connect(lambda: self.select_feature(feature, not is_selected))
        menu.addAction(toggle_action)
        
        menu.addSeparator()
        
        # select similar
        if feature in self._groups:
            group = self._groups[feature]
            select_group_action = QAction(f"Select All {group.capitalize()}", self)
            select_group_action.triggered.connect(lambda: self._select_group(group))
            menu.addAction(select_group_action)
        
        menu.exec(self.table.mapToGlobal(position))
    
    def _select_group(self, group: str):
        """
        select all features in group
        """
        for feature, feat_group in self._groups.items():
            if feat_group == group:
                self._selected.add(feature)
        
        self._update_checkboxes()
        self._update_info()
        self.selection_changed.emit(list(self._selected))
    
    # ================ HELPERS ================
    
    def _populate_table(self):
        """
        populate table with features
        """
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self._features))
        
        for row, feature in enumerate(self._features):
            # checkbox
            chk = QCheckBox()
            chk.setChecked(feature in self._selected)
            chk.stateChanged.connect(lambda state, f=feature: self._on_checkbox_changed(f, state))
            
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.addWidget(chk)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            
            self.table.setCellWidget(row, 0, chk_widget)
            
            # feature name
            name_item = QTableWidgetItem(feature)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, name_item)
            
            # importance
            imp_value = self._importance.get(feature, 0)
            imp_item = QTableWidgetItem(f"{imp_value:.4f}")
            imp_item.setFlags(imp_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            imp_item.setData(Qt.ItemDataRole.UserRole, imp_value)
            
            # color code
            if imp_value >= 0.5:
                imp_item.setBackground(QColor(76, 175, 80, 100))
            elif imp_value >= 0.2:
                imp_item.setBackground(QColor(255, 152, 0, 100))
            
            self.table.setItem(row, 2, imp_item)
            
            # group
            group = self._groups.get(feature, 'other')
            group_item = QTableWidgetItem(group.capitalize())
            group_item.setFlags(group_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 3, group_item)
        
        self.table.setSortingEnabled(True)
        self._update_info()
    
    def _update_checkboxes(self):
        """
        update checkbox states
        """
        for row in range(self.table.rowCount()):
            feature_item = self.table.item(row, 1)
            if feature_item:
                feature = feature_item.text()
                chk_widget = self.table.cellWidget(row, 0)
                if chk_widget:
                    chk = chk_widget.findChild(QCheckBox)
                    if chk:
                        chk.blockSignals(True)
                        chk.setChecked(feature in self._selected)
                        chk.blockSignals(False)
    
    def _update_importance_column(self):
        """
        update importance column values
        """
        for row in range(self.table.rowCount()):
            feature_item = self.table.item(row, 1)
            if feature_item:
                feature = feature_item.text()
                imp_value = self._importance.get(feature, 0)
                
                imp_item = self.table.item(row, 2)
                if imp_item:
                    imp_item.setText(f"{imp_value:.4f}")
                    imp_item.setData(Qt.ItemDataRole.UserRole, imp_value)
    
    def _update_info(self):
        """
        update info labels
        """
        total = len(self._features)
        selected = len(self._selected)
        
        self.lbl_info.setText(f"{total} features")
        self.lbl_selected.setText(f"{selected} selected")