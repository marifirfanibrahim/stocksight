"""
sku navigator widget
browse and filter skus by various criteria
supports category cluster and search filtering
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QComboBox, QLabel,
    QPushButton, QMenu, QAction, QAbstractItemView,
    QTreeWidgetItemIterator
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from typing import Dict, List, Optional, Any

import config


# ============================================================================
#                           SKU NAVIGATOR
# ============================================================================

class SKUNavigator(QWidget):
    # sku browsing and filtering widget
    
    # signals
    sku_selected = pyqtSignal(str)
    sku_double_clicked = pyqtSignal(str)
    selection_changed = pyqtSignal(list)
    bookmark_toggled = pyqtSignal(str, bool)
    
    def __init__(self, parent=None):
        # initialize widget
        super().__init__(parent)
        
        self._skus = []
        self._sku_data = {}
        self._clusters = {}
        self._categories = {}
        self._bookmarks = set()
        self._current_view = "all"
        
        self._setup_ui()
        self._connect_signals()
    
    # ---------- UI SETUP ----------
    
    def _setup_ui(self) -> None:
        # setup user interface
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # search box
        search_layout = QHBoxLayout()
        
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search items...")
        self._search_box.setClearButtonEnabled(True)
        search_layout.addWidget(self._search_box)
        
        layout.addLayout(search_layout)
        
        # view selector
        view_layout = QHBoxLayout()
        
        view_layout.addWidget(QLabel("View:"))
        
        self._view_combo = QComboBox()
        self._view_combo.addItems([
            "All Items",
            "By Category",
            "By Volume Tier",
            "By Pattern",
            "By Cluster",
            "Bookmarked"
        ])
        view_layout.addWidget(self._view_combo)
        
        view_layout.addStretch()
        
        # count label
        self._count_label = QLabel("0 items")
        view_layout.addWidget(self._count_label)
        
        layout.addLayout(view_layout)
        
        # tree widget
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Item", "Info"])
        self._tree.setAlternatingRowColors(True)
        self._tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.header().setStretchLastSection(True)
        
        # disable editing but allow selection
        self._tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        layout.addWidget(self._tree)
        
        # action buttons
        button_layout = QHBoxLayout()
        
        self._bookmark_btn = QPushButton("★ Bookmark")
        self._bookmark_btn.setEnabled(False)
        button_layout.addWidget(self._bookmark_btn)
        
        self._select_all_btn = QPushButton("Select All")
        button_layout.addWidget(self._select_all_btn)
        
        self._clear_btn = QPushButton("Clear")
        button_layout.addWidget(self._clear_btn)
        
        layout.addLayout(button_layout)
    
    def _connect_signals(self) -> None:
        # connect widget signals
        self._search_box.textChanged.connect(self._on_search)
        self._view_combo.currentIndexChanged.connect(self._on_view_changed)
        self._tree.itemSelectionChanged.connect(self._on_selection_changed)
        self._tree.itemDoubleClicked.connect(self._on_double_click)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._bookmark_btn.clicked.connect(self._toggle_bookmark)
        self._select_all_btn.clicked.connect(self._select_all)
        self._clear_btn.clicked.connect(self._clear_selection)
    
    # ---------- DATA MANAGEMENT ----------
    
    def set_skus(self, skus: List[str], sku_data: Optional[Dict[str, Dict]] = None) -> None:
        # set sku list with optional metadata
        self._skus = skus
        self._sku_data = sku_data or {}
        self._refresh_tree()
    
    def set_clusters(self, clusters: Dict[str, Any]) -> None:
        # set cluster assignments
        self._clusters = clusters
        if self._view_combo.currentText() in ["By Cluster", "By Volume Tier", "By Pattern"]:
            self._refresh_tree()
    
    def set_categories(self, categories: Dict[str, List[str]]) -> None:
        # set category assignments
        self._categories = categories
        if self._view_combo.currentText() == "By Category":
            self._refresh_tree()
    
    def set_bookmarks(self, bookmarks: List[str]) -> None:
        # set bookmarked skus
        self._bookmarks = set(bookmarks)
        self._refresh_tree()
    
    def add_bookmark(self, sku: str) -> None:
        # add sku to bookmarks
        self._bookmarks.add(sku)
        self._update_bookmark_display(sku)
    
    def remove_bookmark(self, sku: str) -> None:
        # remove sku from bookmarks
        self._bookmarks.discard(sku)
        self._update_bookmark_display(sku)
    
    # ---------- TREE BUILDING ----------
    
    def _refresh_tree(self) -> None:
        # refresh tree based on current view
        self._tree.clear()
        
        view = self._view_combo.currentText()
        search = self._search_box.text().lower()
        
        # filter skus by search
        filtered_skus = self._skus
        if search:
            filtered_skus = [s for s in self._skus if search in s.lower()]
        
        if view == "All Items":
            self._build_flat_tree(filtered_skus)
        elif view == "By Category":
            self._build_category_tree(filtered_skus)
        elif view == "By Volume Tier":
            self._build_tier_tree(filtered_skus)
        elif view == "By Pattern":
            self._build_pattern_tree(filtered_skus)
        elif view == "By Cluster":
            self._build_cluster_tree(filtered_skus)
        elif view == "Bookmarked":
            bookmarked = [s for s in filtered_skus if s in self._bookmarks]
            self._build_flat_tree(bookmarked)
        
        self._update_count()
    
    def _build_flat_tree(self, skus: List[str]) -> None:
        # build flat list of skus
        for sku in skus:
            item = self._create_sku_item(sku)
            self._tree.addTopLevelItem(item)
    
    def _build_category_tree(self, skus: List[str]) -> None:
        # build tree grouped by category
        cat_groups = {}
        for sku in skus:
            cat = self._get_sku_category(sku)
            if cat not in cat_groups:
                cat_groups[cat] = []
            cat_groups[cat].append(sku)
        
        for cat in sorted(cat_groups.keys()):
            cat_item = QTreeWidgetItem([cat, f"{len(cat_groups[cat])} items"])
            cat_item.setData(0, Qt.UserRole, {"type": "group", "group_type": "category", "name": cat})
            cat_item.setFlags(cat_item.flags() | Qt.ItemIsAutoTristate)
            
            for sku in cat_groups[cat]:
                sku_item = self._create_sku_item(sku)
                cat_item.addChild(sku_item)
            
            self._tree.addTopLevelItem(cat_item)
    
    def _build_tier_tree(self, skus: List[str]) -> None:
        # build tree grouped by volume tier
        tier_groups = {"A": [], "B": [], "C": [], "Unknown": []}
        
        for sku in skus:
            tier = self._get_sku_tier(sku)
            tier_groups.get(tier, tier_groups["Unknown"]).append(sku)
        
        for tier in ["A", "B", "C"]:
            if tier_groups[tier]:
                tier_label = config.CLUSTER_LABELS["volume"].get(tier, tier)
                tier_item = QTreeWidgetItem([tier_label, f"{len(tier_groups[tier])} items"])
                tier_item.setData(0, Qt.UserRole, {"type": "group", "group_type": "tier", "name": tier})
                tier_item.setFlags(tier_item.flags() | Qt.ItemIsAutoTristate)
                
                for sku in tier_groups[tier]:
                    sku_item = self._create_sku_item(sku)
                    tier_item.addChild(sku_item)
                
                self._tree.addTopLevelItem(tier_item)
    
    def _build_pattern_tree(self, skus: List[str]) -> None:
        # build tree grouped by pattern type
        pattern_groups = {"seasonal": [], "erratic": [], "variable": [], "steady": [], "unknown": []}
        
        for sku in skus:
            pattern = self._get_sku_pattern(sku)
            pattern_groups.get(pattern, pattern_groups["unknown"]).append(sku)
        
        for pattern in ["seasonal", "erratic", "variable", "steady"]:
            if pattern_groups[pattern]:
                pattern_label = config.CLUSTER_LABELS["pattern"].get(pattern, pattern)
                pattern_item = QTreeWidgetItem([pattern_label, f"{len(pattern_groups[pattern])} items"])
                pattern_item.setData(0, Qt.UserRole, {"type": "group", "group_type": "pattern", "name": pattern})
                pattern_item.setFlags(pattern_item.flags() | Qt.ItemIsAutoTristate)
                
                for sku in pattern_groups[pattern]:
                    sku_item = self._create_sku_item(sku)
                    pattern_item.addChild(sku_item)
                
                self._tree.addTopLevelItem(pattern_item)
    
    def _build_cluster_tree(self, skus: List[str]) -> None:
        # build tree grouped by full cluster
        cluster_groups = {}
        
        for sku in skus:
            cluster = self._get_sku_cluster_label(sku)
            if cluster not in cluster_groups:
                cluster_groups[cluster] = []
            cluster_groups[cluster].append(sku)
        
        for cluster in sorted(cluster_groups.keys()):
            cluster_item = QTreeWidgetItem([cluster, f"{len(cluster_groups[cluster])} items"])
            cluster_item.setData(0, Qt.UserRole, {"type": "group", "group_type": "cluster", "name": cluster})
            cluster_item.setFlags(cluster_item.flags() | Qt.ItemIsAutoTristate)
            
            for sku in cluster_groups[cluster]:
                sku_item = self._create_sku_item(sku)
                cluster_item.addChild(sku_item)
            
            self._tree.addTopLevelItem(cluster_item)
    
    def _create_sku_item(self, sku: str) -> QTreeWidgetItem:
        # create tree item for sku
        info = self._get_sku_info_text(sku)
        item = QTreeWidgetItem([sku, info])
        item.setData(0, Qt.UserRole, {"type": "sku", "sku": sku})
        item.setFlags(item.flags() | Qt.ItemIsSelectable)
        
        # disable editing
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        
        # mark bookmarked items
        if sku in self._bookmarks:
            item.setText(0, f"★ {sku}")
            item.setForeground(0, QColor(config.UI_COLORS["primary"]))
        
        return item
    
    # ---------- HELPER METHODS ----------
    
    def _get_sku_category(self, sku: str) -> str:
        # get category for sku
        for cat, cat_skus in self._categories.items():
            if sku in cat_skus:
                return cat
        
        # fallback to sku prefix
        return sku[:3] if len(sku) >= 3 else "Other"
    
    def _get_sku_tier(self, sku: str) -> str:
        # get volume tier for sku
        if sku in self._clusters:
            return self._clusters[sku].volume_tier
        return "Unknown"
    
    def _get_sku_pattern(self, sku: str) -> str:
        # get pattern type for sku
        if sku in self._clusters:
            return self._clusters[sku].pattern_type
        return "unknown"
    
    def _get_sku_cluster_label(self, sku: str) -> str:
        # get full cluster label for sku
        if sku in self._clusters:
            return self._clusters[sku].cluster_label
        return "Unclassified"
    
    def _get_sku_info_text(self, sku: str) -> str:
        # get info text for sku
        parts = []
        
        if sku in self._clusters:
            cluster = self._clusters[sku]
            parts.append(cluster.volume_tier)
            parts.append(cluster.pattern_type)
        
        if sku in self._sku_data:
            data = self._sku_data[sku]
            if "total_volume" in data:
                parts.append(f"{data['total_volume']:,.0f}")
        
        return " | ".join(parts) if parts else ""
    
    def _update_bookmark_display(self, sku: str) -> None:
        # update display for single sku
        iterator = QTreeWidgetItemIterator(self._tree)
        while iterator.value():
            item = iterator.value()
            data = item.data(0, Qt.UserRole)
            if data and data.get("type") == "sku" and data.get("sku") == sku:
                if sku in self._bookmarks:
                    item.setText(0, f"★ {sku}")
                    item.setForeground(0, QColor(config.UI_COLORS["primary"]))
                else:
                    item.setText(0, sku)
                    item.setForeground(0, QColor(config.UI_COLORS["text"]))
                break
            iterator += 1
    
    def _update_count(self) -> None:
        # update item count label
        count = 0
        iterator = QTreeWidgetItemIterator(self._tree)
        while iterator.value():
            item = iterator.value()
            data = item.data(0, Qt.UserRole)
            if data and data.get("type") == "sku":
                count += 1
            iterator += 1
        
        self._count_label.setText(f"{count:,} items")
    
    # ---------- EVENT HANDLERS ----------
    
    def _on_search(self, text: str) -> None:
        # handle search text change
        self._refresh_tree()
    
    def _on_view_changed(self, index: int) -> None:
        # handle view change
        self._refresh_tree()
    
    def _on_selection_changed(self) -> None:
        # handle selection change
        selected_skus = self.get_selected_skus()
        self._bookmark_btn.setEnabled(len(selected_skus) > 0)
        self.selection_changed.emit(selected_skus)
        
        if len(selected_skus) == 1:
            self.sku_selected.emit(selected_skus[0])
    
    def _on_double_click(self, item: QTreeWidgetItem, column: int) -> None:
        # handle double click
        data = item.data(0, Qt.UserRole)
        if data and data.get("type") == "sku":
            self.sku_double_clicked.emit(data["sku"])
        elif data and data.get("type") == "group":
            # expand/collapse group on double click
            item.setExpanded(not item.isExpanded())
    
    def _show_context_menu(self, position) -> None:
        # show context menu
        item = self._tree.itemAt(position)
        if not item:
            return
        
        data = item.data(0, Qt.UserRole)
        menu = QMenu(self)
        
        if data and data.get("type") == "sku":
            sku = data["sku"]
            
            # copy action
            copy_action = QAction("Copy Item Name", menu)
            copy_action.triggered.connect(lambda: self._copy_to_clipboard(sku))
            menu.addAction(copy_action)
            
            menu.addSeparator()
            
            # bookmark action
            if sku in self._bookmarks:
                bookmark_action = QAction("Remove Bookmark", menu)
                bookmark_action.triggered.connect(lambda: self._remove_bookmark_action(sku))
            else:
                bookmark_action = QAction("Add Bookmark", menu)
                bookmark_action.triggered.connect(lambda: self._add_bookmark_action(sku))
            menu.addAction(bookmark_action)
            
        elif data and data.get("type") == "group":
            # copy group name
            copy_action = QAction("Copy Group Name", menu)
            copy_action.triggered.connect(lambda: self._copy_to_clipboard(data.get("name", "")))
            menu.addAction(copy_action)
        
        menu.exec_(self._tree.viewport().mapToGlobal(position))
    
    def _copy_to_clipboard(self, text: str) -> None:
        # copy text to clipboard
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
    
    def _toggle_bookmark(self) -> None:
        # toggle bookmark for selected items
        for sku in self.get_selected_skus():
            if sku in self._bookmarks:
                self._bookmarks.discard(sku)
                self.bookmark_toggled.emit(sku, False)
            else:
                self._bookmarks.add(sku)
                self.bookmark_toggled.emit(sku, True)
        
        self._refresh_tree()
    
    def _add_bookmark_action(self, sku: str) -> None:
        # add bookmark from context menu
        self._bookmarks.add(sku)
        self.bookmark_toggled.emit(sku, True)
        self._update_bookmark_display(sku)
    
    def _remove_bookmark_action(self, sku: str) -> None:
        # remove bookmark from context menu
        self._bookmarks.discard(sku)
        self.bookmark_toggled.emit(sku, False)
        self._update_bookmark_display(sku)
    
    def _select_all(self) -> None:
        # select all visible items
        self._tree.selectAll()
    
    def _clear_selection(self) -> None:
        # clear selection
        self._tree.clearSelection()
    
    # ---------- PUBLIC METHODS ----------
    
    def get_selected_skus(self) -> List[str]:
        # get list of selected skus
        selected = []
        for item in self._tree.selectedItems():
            data = item.data(0, Qt.UserRole)
            if data and data.get("type") == "sku":
                selected.append(data["sku"])
        return selected
    
    def select_sku(self, sku: str) -> None:
        # select specific sku
        iterator = QTreeWidgetItemIterator(self._tree)
        while iterator.value():
            item = iterator.value()
            data = item.data(0, Qt.UserRole)
            if data and data.get("type") == "sku" and data.get("sku") == sku:
                self._tree.clearSelection()
                item.setSelected(True)
                self._tree.scrollToItem(item)
                
                # expand parent if exists
                parent = item.parent()
                if parent:
                    parent.setExpanded(True)
                break
            iterator += 1
    
    def get_skus_in_category(self, category: str) -> List[str]:
        # get all skus in a category
        return self._categories.get(category, [])
    
    def get_skus_in_tier(self, tier: str) -> List[str]:
        # get all skus in a tier
        return [sku for sku, cluster in self._clusters.items() if cluster.volume_tier == tier]
    
    def get_skus_in_pattern(self, pattern: str) -> List[str]:
        # get all skus with a pattern
        return [sku for sku, cluster in self._clusters.items() if cluster.pattern_type == pattern]