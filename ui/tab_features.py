"""
feature engineering tab with tsfresh and featuretools
automated extraction, importance ranking, manual overrides
"""


# ================ IMPORTS ================

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QComboBox, QSpinBox,
    QGroupBox, QScrollArea, QFrame, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QListWidget, QListWidgetItem,
    QCheckBox, QSlider, QStackedWidget, QDoubleSpinBox,
    QAbstractItemView, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QPixmap, QImage, QColor

import base64

from config import FeatureConfig, Paths
from core.state import STATE
from core.feature_engine import FEATURES
from core.charting import generate_feature_importance_chart
from core.bookmarks import BOOKMARKS, BookmarkType


# ================ WORKER THREAD ================

class FeatureWorker(QThread):
    """
    background worker for feature extraction
    """
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, method='tsfresh', settings='efficient'):
        super().__init__()
        self.method = method
        self.settings = settings
    
    def run(self):
        """
        run feature extraction
        """
        def progress_callback(value, message):
            self.progress.emit(value, message)
        
        try:
            if self.method == 'tsfresh':
                result = FEATURES.extract_tsfresh_features(
                    extraction_settings=self.settings,
                    progress_callback=progress_callback
                )
            elif self.method == 'featuretools':
                result = FEATURES.extract_featuretools_features(
                    progress_callback=progress_callback
                )
            else:
                result = None
            
            if result is not None:
                self.finished.emit(True, f"Extracted {len(result.columns)} features")
            else:
                self.finished.emit(False, "Feature extraction failed")
                
        except Exception as e:
            self.finished.emit(False, str(e))


class ImportanceWorker(QThread):
    """
    background worker for importance calculation
    """
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    
    def run(self):
        """
        calculate feature importance
        """
        def progress_callback(value, message):
            self.progress.emit(value, message)
        
        try:
            result = FEATURES.calculate_importance(progress_callback=progress_callback)
            
            if result:
                self.finished.emit(True, f"Calculated importance for {len(result)} features")
            else:
                self.finished.emit(False, "Importance calculation failed")
                
        except Exception as e:
            self.finished.emit(False, str(e))


# ================ FEATURES TAB ================

class FeaturesTab(QWidget):
    """
    feature engineering tab
    """
    
    features_updated = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self._worker = None
        
        self._create_ui()
        self._connect_signals()
    
    # ================ UI CREATION ================
    
    def _create_ui(self):
        """
        create tab ui
        """
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # ---------- LEFT PANEL ----------
        left_panel = self._create_left_panel()
        
        # ---------- RIGHT PANEL ----------
        right_panel = self._create_right_panel()
        
        # ---------- SPLITTER ----------
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([350, 850])
        
        layout.addWidget(splitter)
    
    def _create_left_panel(self) -> QWidget:
        """
        create left control panel
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # ---------- EXTRACTION SECTION ----------
        extract_group = QGroupBox("Feature Extraction")
        extract_layout = QVBoxLayout(extract_group)
        
        # method selection
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("Method:"))
        self.combo_method = QComboBox()
        self.combo_method.addItems(['TSFresh', 'Featuretools'])
        method_layout.addWidget(self.combo_method)
        extract_layout.addLayout(method_layout)
        
        # tsfresh settings
        self.tsfresh_settings_widget = QWidget()
        tsfresh_layout = QVBoxLayout(self.tsfresh_settings_widget)
        tsfresh_layout.setContentsMargins(0, 0, 0, 0)
        
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel("Settings:"))
        self.combo_tsfresh_settings = QComboBox()
        self.combo_tsfresh_settings.addItems(['Minimal', 'Efficient', 'Comprehensive'])
        self.combo_tsfresh_settings.setCurrentIndex(1)
        settings_layout.addWidget(self.combo_tsfresh_settings)
        tsfresh_layout.addLayout(settings_layout)
        
        extract_layout.addWidget(self.tsfresh_settings_widget)
        
        # featuretools settings
        self.featuretools_settings_widget = QWidget()
        featuretools_layout = QVBoxLayout(self.featuretools_settings_widget)
        featuretools_layout.setContentsMargins(0, 0, 0, 0)
        
        depth_layout = QHBoxLayout()
        depth_layout.addWidget(QLabel("Max Depth:"))
        self.spin_max_depth = QSpinBox()
        self.spin_max_depth.setRange(1, 5)
        self.spin_max_depth.setValue(2)
        depth_layout.addWidget(self.spin_max_depth)
        featuretools_layout.addLayout(depth_layout)
        
        self.featuretools_settings_widget.setVisible(False)
        extract_layout.addWidget(self.featuretools_settings_widget)
        
        # extract button
        self.btn_extract = QPushButton("Extract Features")
        self.btn_extract.setEnabled(False)
        extract_layout.addWidget(self.btn_extract)
        
        # progress
        self.progress_extract = QProgressBar()
        self.progress_extract.setVisible(False)
        extract_layout.addWidget(self.progress_extract)
        
        self.lbl_extract_status = QLabel("")
        self.lbl_extract_status.setStyleSheet("color: gray; font-size: 11px;")
        extract_layout.addWidget(self.lbl_extract_status)
        
        layout.addWidget(extract_group)
        
        # ---------- IMPORTANCE SECTION ----------
        importance_group = QGroupBox("Feature Importance")
        importance_layout = QVBoxLayout(importance_group)
        
        # calculate importance button
        self.btn_calculate_importance = QPushButton("Calculate Importance")
        self.btn_calculate_importance.setEnabled(False)
        importance_layout.addWidget(self.btn_calculate_importance)
        
        # threshold slider
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Threshold:"))
        self.slider_threshold = QSlider(Qt.Orientation.Horizontal)
        self.slider_threshold.setRange(0, 100)
        self.slider_threshold.setValue(int(FeatureConfig.RELEVANCE_THRESHOLD * 100))
        threshold_layout.addWidget(self.slider_threshold)
        self.lbl_threshold = QLabel(f"{FeatureConfig.RELEVANCE_THRESHOLD:.2f}")
        threshold_layout.addWidget(self.lbl_threshold)
        importance_layout.addLayout(threshold_layout)
        
        # auto select button
        self.btn_auto_select = QPushButton("Auto-Select Features")
        self.btn_auto_select.setProperty("secondary", True)
        self.btn_auto_select.setEnabled(False)
        importance_layout.addWidget(self.btn_auto_select)
        
        layout.addWidget(importance_group)
        
        # ---------- SELECTION SECTION ----------
        selection_group = QGroupBox("Feature Selection")
        selection_layout = QVBoxLayout(selection_group)
        
        # stats
        self.lbl_feature_stats = QLabel("No features extracted")
        self.lbl_feature_stats.setStyleSheet("color: gray;")
        selection_layout.addWidget(self.lbl_feature_stats)
        
        # group toggles
        selection_layout.addWidget(QLabel("Feature Groups:"))
        
        self.group_checkboxes = {}
        for group_name in ['Statistical', 'Temporal', 'Frequency', 'Entropy', 'Other']:
            chk = QCheckBox(group_name)
            chk.setChecked(True)
            chk.setEnabled(False)
            self.group_checkboxes[group_name.lower()] = chk
            selection_layout.addWidget(chk)
        
        # select/deselect all
        btn_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.setProperty("secondary", True)
        self.btn_select_all.setEnabled(False)
        btn_layout.addWidget(self.btn_select_all)
        
        self.btn_deselect_all = QPushButton("Deselect All")
        self.btn_deselect_all.setProperty("secondary", True)
        self.btn_deselect_all.setEnabled(False)
        btn_layout.addWidget(self.btn_deselect_all)
        selection_layout.addLayout(btn_layout)
        
        layout.addWidget(selection_group)
        
        # ---------- EXPORT SECTION ----------
        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout(export_group)
        
        # format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        self.combo_export_format = QComboBox()
        self.combo_export_format.addItems(['CSV', 'Parquet', 'Pickle'])
        format_layout.addWidget(self.combo_export_format)
        export_layout.addLayout(format_layout)
        
        # export button
        self.btn_export = QPushButton("Export Features")
        self.btn_export.setEnabled(False)
        export_layout.addWidget(self.btn_export)
        
        # bookmark button
        self.btn_bookmark = QPushButton("Bookmark Feature Set")
        self.btn_bookmark.setProperty("secondary", True)
        self.btn_bookmark.setEnabled(False)
        export_layout.addWidget(self.btn_bookmark)
        
        layout.addWidget(export_group)
        
        layout.addStretch()
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """
        create right content panel
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # ---------- STACKED WIDGET ----------
        self.stack = QStackedWidget()
        
        # placeholder
        placeholder = self._create_placeholder()
        self.stack.addWidget(placeholder)
        
        # feature table
        table_page = self._create_table_page()
        self.stack.addWidget(table_page)
        
        # importance chart
        chart_page = self._create_chart_page()
        self.stack.addWidget(chart_page)
        
        layout.addWidget(self.stack)
        
        # ---------- VIEW TOGGLE ----------
        view_layout = QHBoxLayout()
        view_layout.addStretch()
        
        self.btn_view_table = QPushButton("Table View")
        self.btn_view_table.setProperty("secondary", True)
        view_layout.addWidget(self.btn_view_table)
        
        self.btn_view_chart = QPushButton("Chart View")
        self.btn_view_chart.setProperty("secondary", True)
        view_layout.addWidget(self.btn_view_chart)
        
        layout.addLayout(view_layout)
        
        return panel
    
    def _create_placeholder(self) -> QWidget:
        """
        create placeholder widget
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl = QLabel("Extract features to begin")
        lbl.setStyleSheet("font-size: 18px; color: gray;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)
        
        return widget
    
    def _create_table_page(self) -> QWidget:
        """
        create feature table page
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.txt_feature_search = QLineEdit()
        self.txt_feature_search.setPlaceholderText("Filter features...")
        search_layout.addWidget(self.txt_feature_search)
        layout.addLayout(search_layout)
        
        # table
        self.feature_table = QTableWidget()
        self.feature_table.setColumnCount(4)
        self.feature_table.setHorizontalHeaderLabels(['', 'Feature', 'Importance', 'Group'])
        self.feature_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.feature_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.feature_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.feature_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.feature_table.setColumnWidth(0, 40)
        self.feature_table.setColumnWidth(2, 100)
        self.feature_table.setColumnWidth(3, 100)
        self.feature_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.feature_table.setAlternatingRowColors(True)
        layout.addWidget(self.feature_table)
        
        return widget
    
    def _create_chart_page(self) -> QWidget:
        """
        create importance chart page
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # scroll area for chart
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.chart_label = QLabel()
        self.chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidget(self.chart_label)
        
        layout.addWidget(scroll)
        
        return widget
    
    # ================ SIGNALS ================
    
    def _connect_signals(self):
        """
        connect widget signals
        """
        self.combo_method.currentIndexChanged.connect(self._on_method_changed)
        self.btn_extract.clicked.connect(self._on_extract_clicked)
        
        self.btn_calculate_importance.clicked.connect(self._on_calculate_importance)
        self.slider_threshold.valueChanged.connect(self._on_threshold_changed)
        self.btn_auto_select.clicked.connect(self._on_auto_select)
        
        self.btn_select_all.clicked.connect(self._on_select_all)
        self.btn_deselect_all.clicked.connect(self._on_deselect_all)
        
        for name, chk in self.group_checkboxes.items():
            chk.stateChanged.connect(lambda state, n=name: self._on_group_toggled(n, state))
        
        self.btn_export.clicked.connect(self._on_export)
        self.btn_bookmark.clicked.connect(self._on_bookmark)
        
        self.btn_view_table.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.btn_view_chart.clicked.connect(self._show_importance_chart)
        
        self.txt_feature_search.textChanged.connect(self._on_feature_search)
    
    # ================ SLOTS ================
    
    def _on_method_changed(self, index: int):
        """
        handle method selection change
        """
        if index == 0:
            self.tsfresh_settings_widget.setVisible(True)
            self.featuretools_settings_widget.setVisible(False)
        else:
            self.tsfresh_settings_widget.setVisible(False)
            self.featuretools_settings_widget.setVisible(True)
    
    def _on_extract_clicked(self):
        """
        handle extract button click
        """
        if STATE.clean_data is None:
            return
        
        # get method
        method = 'tsfresh' if self.combo_method.currentIndex() == 0 else 'featuretools'
        settings = self.combo_tsfresh_settings.currentText().lower()
        
        # disable button and show progress
        self.btn_extract.setEnabled(False)
        self.progress_extract.setVisible(True)
        self.progress_extract.setValue(0)
        self.lbl_extract_status.setText("Starting extraction...")
        
        # start worker
        self._worker = FeatureWorker(method=method, settings=settings)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.finished.connect(self._on_extract_finished)
        self._worker.start()
    
    def _on_worker_progress(self, value: int, message: str):
        """
        handle worker progress
        """
        self.progress_extract.setValue(value)
        self.lbl_extract_status.setText(message)
    
    def _on_extract_finished(self, success: bool, message: str):
        """
        handle extraction complete
        """
        self.btn_extract.setEnabled(True)
        self.progress_extract.setVisible(False)
        self.lbl_extract_status.setText(message)
        
        if success:
            self._update_feature_display()
            self._enable_controls(True)
            self.stack.setCurrentIndex(1)
            
            if self.main_window:
                self.main_window.set_status(message)
        else:
            if self.main_window:
                self.main_window.set_status(message, True)
    
    def _on_calculate_importance(self):
        """
        calculate feature importance
        """
        self.btn_calculate_importance.setEnabled(False)
        self.progress_extract.setVisible(True)
        self.lbl_extract_status.setText("Calculating importance...")
        
        self._worker = ImportanceWorker()
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.finished.connect(self._on_importance_finished)
        self._worker.start()
    
    def _on_importance_finished(self, success: bool, message: str):
        """
        handle importance calculation complete
        """
        self.btn_calculate_importance.setEnabled(True)
        self.progress_extract.setVisible(False)
        self.lbl_extract_status.setText(message)
        
        if success:
            self._update_feature_table()
            self.btn_auto_select.setEnabled(True)
            
            if self.main_window:
                self.main_window.set_status(message)
    
    def _on_threshold_changed(self, value: int):
        """
        handle threshold slider change
        """
        threshold = value / 100
        self.lbl_threshold.setText(f"{threshold:.2f}")
    
    def _on_auto_select(self):
        """
        auto-select features based on threshold
        """
        threshold = self.slider_threshold.value() / 100
        selected = FEATURES.select_features(threshold=threshold)
        
        self._update_feature_table()
        self._update_feature_stats()
        
        if self.main_window:
            self.main_window.set_status(f"Selected {len(selected)} features")
    
    def _on_select_all(self):
        """
        select all features
        """
        available = STATE.available_features
        FEATURES.set_selected_features(available)
        self._update_feature_table()
        self._update_feature_stats()
    
    def _on_deselect_all(self):
        """
        deselect all features
        """
        FEATURES.set_selected_features([])
        self._update_feature_table()
        self._update_feature_stats()
    
    def _on_group_toggled(self, group_name: str, state: int):
        """
        handle group checkbox toggle
        """
        enabled = state == Qt.CheckState.Checked.value
        FEATURES.enable_feature_group(group_name, enabled)
        self._update_feature_table()
        self._update_feature_stats()
    
    def _on_feature_search(self, text: str):
        """
        filter feature table
        """
        text_lower = text.lower()
        
        for row in range(self.feature_table.rowCount()):
            feature_item = self.feature_table.item(row, 1)
            if feature_item:
                match = text_lower in feature_item.text().lower()
                self.feature_table.setRowHidden(row, not match)
    
    def _on_export(self):
        """
        export features
        """
        format_map = {
            'CSV': 'csv',
            'Parquet': 'parquet',
            'Pickle': 'pickle'
        }
        format_str = format_map.get(self.combo_export_format.currentText(), 'csv')
        
        path = FEATURES.export_features(format=format_str)
        
        if path:
            if self.main_window:
                self.main_window.set_status(f"Features exported: {path.name}")
    
    def _on_bookmark(self):
        """
        bookmark current feature set
        """
        selected = FEATURES.get_selected_features()
        
        if selected:
            BOOKMARKS.bookmark_features(
                name=f"Feature Set ({len(selected)} features)",
                feature_names=selected
            )
            
            if self.main_window:
                self.main_window.set_status("Feature set bookmarked")
    
    # ================ DISPLAY ================
    
    def _update_feature_display(self):
        """
        update feature display
        """
        self._update_feature_table()
        self._update_feature_stats()
        self._update_group_checkboxes()
    
    def _update_feature_table(self):
        """
        update feature table
        """
        features = FEATURES.get_features()
        importance = FEATURES.get_importance()
        selected = FEATURES.get_selected_features()
        groups = FEATURES.get_feature_groups()
        
        if features is None:
            self.feature_table.setRowCount(0)
            return
        
        # build group lookup
        feature_to_group = {}
        for group_name, feature_list in groups.items():
            for f in feature_list:
                feature_to_group[f] = group_name
        
        # populate table
        self.feature_table.setRowCount(len(features.columns))
        
        for row, feature_name in enumerate(features.columns):
            # checkbox
            chk = QCheckBox()
            chk.setChecked(feature_name in selected)
            chk.stateChanged.connect(lambda state, f=feature_name: self._on_feature_toggled(f, state))
            
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.addWidget(chk)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            
            self.feature_table.setCellWidget(row, 0, chk_widget)
            
            # feature name
            name_item = QTableWidgetItem(feature_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.feature_table.setItem(row, 1, name_item)
            
            # importance
            imp_value = importance.get(feature_name, 0)
            imp_item = QTableWidgetItem(f"{imp_value:.4f}")
            imp_item.setFlags(imp_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # color code importance
            if imp_value >= 0.5:
                imp_item.setBackground(QColor(76, 175, 80, 100))
            elif imp_value >= 0.2:
                imp_item.setBackground(QColor(255, 152, 0, 100))
            
            self.feature_table.setItem(row, 2, imp_item)
            
            # group
            group = feature_to_group.get(feature_name, 'other')
            group_item = QTableWidgetItem(group.capitalize())
            group_item.setFlags(group_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.feature_table.setItem(row, 3, group_item)
    
    def _on_feature_toggled(self, feature_name: str, state: int):
        """
        handle individual feature toggle
        """
        enabled = state == Qt.CheckState.Checked.value
        FEATURES.toggle_feature(feature_name, enabled)
        self._update_feature_stats()
    
    def _update_feature_stats(self):
        """
        update feature statistics label
        """
        stats = FEATURES.get_feature_stats()
        
        if not stats:
            self.lbl_feature_stats.setText("No features extracted")
            return
        
        text = f"Total: {stats['total_features']}\n"
        text += f"Selected: {stats['selected_features']}"
        
        self.lbl_feature_stats.setText(text)
    
    def _update_group_checkboxes(self):
        """
        update group checkbox states
        """
        groups = FEATURES.get_feature_groups()
        
        for name, chk in self.group_checkboxes.items():
            has_features = name in groups and len(groups[name]) > 0
            chk.setEnabled(has_features)
            
            if has_features:
                chk.setText(f"{name.capitalize()} ({len(groups[name])})")
    
    def _show_importance_chart(self):
        """
        generate and display importance chart
        """
        importance = FEATURES.get_importance()
        
        if not importance:
            return
        
        dark_mode = self.main_window.get_dark_mode() if self.main_window else True
        
        img_base64 = generate_feature_importance_chart(importance, dark_mode=dark_mode)
        
        if img_base64:
            try:
                img_data = base64.b64decode(img_base64)
                img = QImage()
                img.loadFromData(img_data)
                pixmap = QPixmap.fromImage(img)
                
                self.chart_label.setPixmap(pixmap)
                self.stack.setCurrentIndex(2)
                
            except Exception as e:
                print(f"chart display error: {e}")
    
    def _enable_controls(self, enabled: bool):
        """
        enable/disable controls
        """
        self.btn_calculate_importance.setEnabled(enabled)
        self.btn_select_all.setEnabled(enabled)
        self.btn_deselect_all.setEnabled(enabled)
        self.btn_export.setEnabled(enabled)
        self.btn_bookmark.setEnabled(enabled)
        
        for chk in self.group_checkboxes.values():
            chk.setEnabled(enabled)
    
    # ================ PUBLIC ================
    
    def on_tab_activated(self):
        """
        called when tab is activated
        """
        has_data = STATE.clean_data is not None
        self.btn_extract.setEnabled(has_data)
        
        if STATE.feature_extraction_complete:
            self._update_feature_display()
            self._enable_controls(True)
            self.stack.setCurrentIndex(1)
    
    def refresh(self):
        """
        refresh tab contents
        """
        if STATE.feature_extraction_complete:
            self._update_feature_display()