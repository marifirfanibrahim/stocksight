"""
features tab module
tab 3 feature engineering
manages feature creation and selection
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QFrame, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QComboBox, QSpinBox, QMessageBox,
    QScrollArea, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QBrush
from typing import Optional, Dict, List

import config
from core.feature_engineer import FeatureEngineer
from utils.worker_threads import WorkerThread
from ui.widgets.progress_dialog import ProgressDialog


# ============================================================================
#                            FEATURES TAB
# ============================================================================

class FeaturesTab(QWidget):
    # feature engineering tab
    
    # signals
    features_created = pyqtSignal(dict)
    proceed_requested = pyqtSignal()
    
    def __init__(self, session_model, parent=None):
        # initialize tab
        super().__init__(parent)
        
        self._session = session_model
        self._engineer = FeatureEngineer()
        self._processor = None
        self._clustering = None
        self._worker = None
        self._feature_checks = {}
        
        self._setup_ui()
    
    # ---------- UI SETUP ----------
    
    def _setup_ui(self) -> None:
        # setup user interface
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # header
        header_layout = QHBoxLayout()
        
        header = QLabel("Feature Engineering")
        header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # feature set selector
        header_layout.addWidget(QLabel("Feature Set:"))
        
        self._feature_set_combo = QComboBox()
        self._feature_set_combo.addItems([
            "Tier-Based (Recommended)",
            "All 20 Features",
            "Top 10 Features",
            "Basic 5 Features",
            "Custom Selection"
        ])
        self._feature_set_combo.currentIndexChanged.connect(self._on_feature_set_changed)
        header_layout.addWidget(self._feature_set_combo)
        
        layout.addLayout(header_layout)
        
        # main content splitter
        content_layout = QHBoxLayout()
        
        # left side - feature list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(self._create_feature_list_group())
        
        content_layout.addWidget(left_widget, stretch=2)
        
        # right side - settings and preview
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_layout.addWidget(self._create_tier_config_group())
        right_layout.addWidget(self._create_advanced_group())
        right_layout.addWidget(self._create_preview_group())
        right_layout.addStretch()
        
        content_layout.addWidget(right_widget, stretch=1)
        
        layout.addLayout(content_layout)
        
        # bottom bar
        bottom_layout = QHBoxLayout()
        
        self._status_label = QLabel("Configure features and click Create to generate")
        self._status_label.setStyleSheet("color: gray;")
        bottom_layout.addWidget(self._status_label)
        
        bottom_layout.addStretch()
        
        # create features button
        self._create_btn = QPushButton("Create Features")
        self._create_btn.setMinimumWidth(150)
        self._create_btn.clicked.connect(self._create_features)
        bottom_layout.addWidget(self._create_btn)
        
        # proceed button
        self._proceed_btn = QPushButton("Proceed to Forecasting →")
        self._proceed_btn.setEnabled(False)
        self._proceed_btn.setMinimumHeight(40)
        self._proceed_btn.setStyleSheet(f"background-color: {config.UI_COLORS['primary']}; color: white; font-weight: bold;")
        self._proceed_btn.clicked.connect(self.proceed_requested.emit)
        bottom_layout.addWidget(self._proceed_btn)
        
        layout.addLayout(bottom_layout)
    
    def _create_feature_list_group(self) -> QGroupBox:
        # create feature list group
        group = QGroupBox("Available Features")
        layout = QVBoxLayout(group)
        
        # description
        desc = QLabel("Select features to create. Each feature helps the model understand patterns in your data.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # feature table
        self._feature_table = QTableWidget()
        self._feature_table.setColumnCount(4)
        self._feature_table.setHorizontalHeaderLabels(["", "Feature", "Description", "Impact"])
        self._feature_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self._feature_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self._feature_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._feature_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self._feature_table.setColumnWidth(0, 30)
        self._feature_table.setColumnWidth(1, 150)
        self._feature_table.setColumnWidth(3, 80)
        self._feature_table.setAlternatingRowColors(True)
        self._feature_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._feature_table.verticalHeader().setVisible(False)
        
        # populate features
        self._populate_feature_table()
        
        layout.addWidget(self._feature_table)
        
        # select buttons - including impact-based selection
        btn_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all_features)
        btn_layout.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(self._select_no_features)
        btn_layout.addWidget(select_none_btn)
        
        btn_layout.addStretch()
        
        # impact-based selection buttons
        select_high_btn = QPushButton("+ High Impact")
        select_high_btn.setToolTip("Add all high impact features to selection")
        select_high_btn.clicked.connect(lambda: self._select_by_impact("High"))
        btn_layout.addWidget(select_high_btn)
        
        select_medium_btn = QPushButton("+ Medium Impact")
        select_medium_btn.setToolTip("Add all medium impact features to selection")
        select_medium_btn.clicked.connect(lambda: self._select_by_impact("Medium"))
        btn_layout.addWidget(select_medium_btn)
        
        select_low_btn = QPushButton("+ Low Impact")
        select_low_btn.setToolTip("Add all low impact features to selection")
        select_low_btn.clicked.connect(lambda: self._select_by_impact("Low"))
        btn_layout.addWidget(select_low_btn)
        
        layout.addLayout(btn_layout)
        
        return group
    
    def _populate_feature_table(self) -> None:
        # populate feature table with curated features
        features = config.FEATURES["curated"]
        descriptions = config.FEATURE_DESCRIPTIONS
        
        self._feature_table.setRowCount(len(features))
        self._feature_checks = {}
        
        for i, feature in enumerate(features):
            # checkbox
            check = QCheckBox()
            check.setChecked(True)
            check.stateChanged.connect(self._update_feature_count)
            self._feature_checks[feature] = check
            
            check_widget = QWidget()
            check_layout = QHBoxLayout(check_widget)
            check_layout.addWidget(check)
            check_layout.setAlignment(Qt.AlignCenter)
            check_layout.setContentsMargins(0, 0, 0, 0)
            self._feature_table.setCellWidget(i, 0, check_widget)
            
            # feature name
            name_item = QTableWidgetItem(feature.replace("_", " ").title())
            name_item.setData(Qt.UserRole, feature)
            self._feature_table.setItem(i, 1, name_item)
            
            # description
            desc = descriptions.get(feature, "")
            desc_item = QTableWidgetItem(desc)
            self._feature_table.setItem(i, 2, desc_item)
            
            # impact indicator
            impact = self._get_feature_impact(feature)
            impact_item = QTableWidgetItem(impact)
            impact_item.setTextAlignment(Qt.AlignCenter)
            impact_item.setData(Qt.UserRole, impact)
            
            if impact == "High":
                impact_item.setBackground(QBrush(QColor(200, 230, 200)))
            elif impact == "Medium":
                impact_item.setBackground(QBrush(QColor(255, 255, 200)))
            else:
                impact_item.setBackground(QBrush(QColor(240, 240, 240)))
            
            self._feature_table.setItem(i, 3, impact_item)
    
    def _get_feature_impact(self, feature: str) -> str:
        # get impact level for feature
        high_impact = ["lag_1", "lag_7", "rolling_mean_7", "seasonal_index", "trend_component"]
        medium_impact = ["lag_28", "rolling_mean_28", "month", "day_of_week", "is_holiday"]
        
        if feature in high_impact:
            return "High"
        elif feature in medium_impact:
            return "Medium"
        else:
            return "Low"
    
    def _create_tier_config_group(self) -> QGroupBox:
        # create tier configuration group
        group = QGroupBox("Tier-Based Configuration")
        layout = QVBoxLayout(group)
        
        desc = QLabel("Different item tiers get different feature sets for optimal speed and accuracy.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray;")
        layout.addWidget(desc)
        
        # tier settings
        self._tier_combos = {}
        
        for tier, label, default in [
            ("A", "A-Items (High Volume)", "All 20 Features"),
            ("B", "B-Items (Medium Volume)", "Top 10 Features"),
            ("C", "C-Items (Low Volume)", "Basic 5 Features")
        ]:
            tier_layout = QHBoxLayout()
            
            tier_label = QLabel(label)
            tier_label.setMinimumWidth(150)
            tier_layout.addWidget(tier_label)
            
            combo = QComboBox()
            combo.addItems(["All 20 Features", "Top 10 Features", "Basic 5 Features"])
            combo.setCurrentText(default)
            self._tier_combos[tier] = combo
            tier_layout.addWidget(combo)
            
            layout.addLayout(tier_layout)
        
        return group
    
    def _create_advanced_group(self) -> QGroupBox:
        # create advanced options group
        group = QGroupBox("Advanced Options")
        layout = QVBoxLayout(group)
        
        # advanced extraction toggle
        self._advanced_check = QCheckBox("Enable advanced feature extraction")
        self._advanced_check.stateChanged.connect(self._on_advanced_changed)
        layout.addWidget(self._advanced_check)
        
        self._advanced_warning = QLabel("⚠ Adds 5-10 minutes processing time\n+15-25% potential accuracy improvement")
        self._advanced_warning.setStyleSheet("color: orange; font-size: 10px; margin-left: 20px;")
        self._advanced_warning.setVisible(False)
        layout.addWidget(self._advanced_warning)
        
        # lag customization
        lag_layout = QHBoxLayout()
        lag_layout.addWidget(QLabel("Max lag days:"))
        
        self._max_lag_spin = QSpinBox()
        self._max_lag_spin.setRange(7, 365)
        self._max_lag_spin.setValue(28)
        lag_layout.addWidget(self._max_lag_spin)
        
        lag_layout.addStretch()
        layout.addLayout(lag_layout)
        
        return group
    
    def _create_preview_group(self) -> QGroupBox:
        # create preview group
        group = QGroupBox("Feature Preview")
        layout = QVBoxLayout(group)
        
        self._preview_label = QLabel("Select features to see preview")
        self._preview_label.setWordWrap(True)
        self._preview_label.setStyleSheet("color: gray;")
        layout.addWidget(self._preview_label)
        
        self._estimate_label = QLabel("")
        self._estimate_label.setWordWrap(True)
        layout.addWidget(self._estimate_label)
        
        return group
    
    # ---------- EVENT HANDLERS ----------
    
    def _on_feature_set_changed(self, index: int) -> None:
        # handle feature set selection change
        text = self._feature_set_combo.currentText()
        
        if text == "All 20 Features":
            self._select_features(config.FEATURES["curated"])
        elif text == "Top 10 Features":
            self._select_features(config.FEATURES["top_10"])
        elif text == "Basic 5 Features":
            self._select_features(config.FEATURES["basic_5"])
        elif text == "Custom Selection":
            pass
        elif text == "Tier-Based (Recommended)":
            self._select_all_features()
        
        self._update_feature_count()
    
    def _select_features(self, feature_list: List[str]) -> None:
        # select specific features
        for feature, check in self._feature_checks.items():
            check.setChecked(feature in feature_list)
    
    def _select_all_features(self) -> None:
        # select all features
        for check in self._feature_checks.values():
            check.setChecked(True)
        self._update_feature_count()
    
    def _select_no_features(self) -> None:
        # deselect all features
        for check in self._feature_checks.values():
            check.setChecked(False)
        self._update_feature_count()
    
    def _select_by_impact(self, impact_level: str) -> None:
        # add features by impact level to current selection (cumulative)
        for i in range(self._feature_table.rowCount()):
            impact_item = self._feature_table.item(i, 3)
            if impact_item and impact_item.data(Qt.UserRole) == impact_level:
                name_item = self._feature_table.item(i, 1)
                if name_item:
                    feature = name_item.data(Qt.UserRole)
                    if feature in self._feature_checks:
                        self._feature_checks[feature].setChecked(True)
        
        self._update_feature_count()
        
        # switch to custom selection mode
        self._feature_set_combo.setCurrentText("Custom Selection")
    
    def _on_advanced_changed(self, state: int) -> None:
        # handle advanced checkbox change
        self._advanced_warning.setVisible(state == Qt.Checked)
        self._update_preview()
    
    def _update_feature_count(self) -> None:
        # update selected feature count
        selected = sum(1 for c in self._feature_checks.values() if c.isChecked())
        total = len(self._feature_checks)
        
        self._status_label.setText(f"{selected} of {total} features selected")
        self._update_preview()
    
    def _update_preview(self) -> None:
        # update preview label
        selected = [f for f, c in self._feature_checks.items() if c.isChecked()]
        
        if not selected:
            self._preview_label.setText("No features selected")
            self._estimate_label.setText("")
            return
        
        # categorize features
        lag_features = [f for f in selected if f.startswith("lag_")]
        rolling_features = [f for f in selected if f.startswith("rolling_")]
        date_features = [f for f in selected if f in ["year", "month", "week_of_year", "day_of_week", "is_weekend"]]
        other_features = [f for f in selected if f not in lag_features + rolling_features + date_features]
        
        preview_parts = []
        if lag_features:
            preview_parts.append(f"• {len(lag_features)} lag features")
        if rolling_features:
            preview_parts.append(f"• {len(rolling_features)} rolling features")
        if date_features:
            preview_parts.append(f"• {len(date_features)} date features")
        if other_features:
            preview_parts.append(f"• {len(other_features)} other features")
        
        self._preview_label.setText("\n".join(preview_parts))
        
        # estimate time
        sku_count = self._session.state.total_skus or 1000
        base_time = 0.01 * sku_count * len(selected) / 20
        
        if self._advanced_check.isChecked():
            base_time *= 3
        
        if base_time < 60:
            time_str = f"~{int(base_time)} seconds"
        else:
            time_str = f"~{base_time/60:.1f} minutes"
        
        self._estimate_label.setText(f"Estimated time: {time_str} for {sku_count:,} items")
    
    # ---------- FEATURE CREATION ----------
    
    def _create_features(self) -> None:
        # create features for all skus
        if self._processor is None:
            QMessageBox.warning(self, "No Data", "Please load data first")
            return
        
        selected = [f for f, c in self._feature_checks.items() if c.isChecked()]
        
        if not selected:
            QMessageBox.warning(self, "No Features", "Please select at least one feature")
            return
        
        # show progress
        progress = ProgressDialog("Creating Features", self)
        progress.set_status("Generating features for all items...")
        progress.start()
        
        # get tier mapping
        tier_mapping = {}
        clusters = self._session.get_clusters()
        for sku, cluster in clusters.items():
            tier_mapping[sku] = cluster.volume_tier
        
        # get column names
        sku_col = self._processor.get_mapped_column("sku")
        date_col = self._processor.get_mapped_column("date")
        qty_col = self._processor.get_mapped_column("quantity")
        price_col = self._processor.get_mapped_column("price")
        promo_col = self._processor.get_mapped_column("promo")
        
        # run in background
        def do_feature_creation(progress_callback=None):
            return self._engineer.create_features_batch(
                self._processor.processed_data,
                sku_col, date_col, qty_col,
                tier_mapping,
                price_col, promo_col,
                progress_callback
            )
        
        self._worker = WorkerThread(do_feature_creation)
        self._worker.progress_signal.connect(progress.set_progress)
        self._worker.result_signal.connect(lambda r: self._on_features_created(r, progress))
        self._worker.error_signal.connect(lambda e: self._on_feature_error(e, progress))
        self._worker.start()
    
    def _on_features_created(self, featured_data, progress: ProgressDialog) -> None:
        # handle features created
        progress.finish("Features created successfully")
        
        # calculate importance
        qty_col = self._processor.get_mapped_column("quantity")
        selected = [f for f, c in self._feature_checks.items() if c.isChecked()]
        
        importance = self._engineer.get_feature_importance(
            featured_data.dropna(),
            qty_col,
            selected
        )
        
        # update session
        self._session.set_features({
            "data": featured_data,
            "selected_features": selected,
            "importance": importance
        })
        
        # update ui
        self._update_importance_display(importance)
        
        # emit signal
        self.features_created.emit({"selected": selected, "importance": importance})
        
        # enable proceed
        self._proceed_btn.setEnabled(True)
        
        self._status_label.setText(f"Created {len(selected)} features for {self._session.state.total_skus:,} items")
    
    def _on_feature_error(self, error: str, progress: ProgressDialog) -> None:
        # handle feature creation error
        progress.finish(f"Error: {error}", auto_close=False)
        QMessageBox.critical(self, "Feature Error", f"Failed to create features:\n{error}")
    
    def _update_importance_display(self, importance: Dict[str, float]) -> None:
        # update feature table with importance
        for i in range(self._feature_table.rowCount()):
            name_item = self._feature_table.item(i, 1)
            if name_item:
                feature = name_item.data(Qt.UserRole)
                imp = importance.get(feature, 0)
                
                # update impact column
                impact_text = f"{imp*100:.1f}%"
                impact_item = self._feature_table.item(i, 3)
                if impact_item:
                    impact_item.setText(impact_text)
                    
                    if imp >= 0.1:
                        impact_item.setBackground(QBrush(QColor(200, 230, 200)))
                    elif imp >= 0.05:
                        impact_item.setBackground(QBrush(QColor(255, 255, 200)))
                    else:
                        impact_item.setBackground(QBrush(QColor(240, 240, 240)))
    
    # ---------- PUBLIC METHODS ----------
    
    def set_processor(self, processor) -> None:
        # set data processor
        self._processor = processor
        self._update_preview()
    
    def set_clustering(self, clustering) -> None:
        # set clustering instance
        self._clustering = clustering
    
    def get_selected_features(self) -> List[str]:
        # get list of selected features
        return [f for f, c in self._feature_checks.items() if c.isChecked()]
    
    def get_tier_config(self) -> Dict[str, str]:
        # get tier feature configuration
        result = {}
        for tier, combo in self._tier_combos.items():
            text = combo.currentText()
            if text == "All 20 Features":
                result[tier] = "all_20"
            elif text == "Top 10 Features":
                result[tier] = "top_10"
            else:
                result[tier] = "basic_5"
        return result