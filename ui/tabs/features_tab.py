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
from PyQt5.QtWidgets import QApplication
import csv
from datetime import datetime
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QBrush
from typing import Optional, Dict, List

import config
from core.feature_engineer import FeatureEngineer
from utils.worker_threads import WorkerThread
from ui.widgets.progress_dialog import ProgressDialog
from ui.dialogs.help_dialog import ForecastHelpDialog


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
        # add short tooltips for analysts to understand choices
        self._feature_set_combo.setItemData(0, "Automatically choose features by item tier (recommended)", Qt.ToolTipRole)
        self._feature_set_combo.setItemData(1, "All curated features (slower). Use for deep analysis.", Qt.ToolTipRole)
        self._feature_set_combo.setItemData(2, "Top 10 features (balanced)", Qt.ToolTipRole)
        self._feature_set_combo.setItemData(3, "Basic 5 features (fast)", Qt.ToolTipRole)
        self._feature_set_combo.setItemData(4, "Choose features manually", Qt.ToolTipRole)
        self._feature_set_combo.currentIndexChanged.connect(self._on_feature_set_changed)
        header_layout.addWidget(self._feature_set_combo)
        # details button to show which features are in the selected set
        details_btn = QPushButton("Details")
        details_btn.setMaximumWidth(90)
        details_btn.setToolTip("Show which features are included in the selected feature set")
        details_btn.clicked.connect(self._show_feature_set_details)
        header_layout.addWidget(details_btn)
        
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
        # increase contrast and size for better readability for business analysts
        self._status_label.setStyleSheet("color: #444; font-size: 11px;")
        bottom_layout.addWidget(self._status_label)
        
        bottom_layout.addStretch()
        
        # create features button (primary)
        self._create_btn = QPushButton("Create Features")
        self._create_btn.setMinimumWidth(150)
        self._create_btn.clicked.connect(self._create_features)
        # make this the primary action visually
        self._create_btn.setStyleSheet(f"background-color: {config.UI_COLORS['primary']}; color: white; font-weight: bold;")
        bottom_layout.addWidget(self._create_btn)

        # proceed button (secondary)
        self._proceed_btn = QPushButton("Proceed to Forecasting →")
        self._proceed_btn.setEnabled(False)
        self._proceed_btn.setMinimumHeight(40)
        bottom_layout.addWidget(self._proceed_btn)
        self._proceed_btn.clicked.connect(self.proceed_requested.emit)
        
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
            # tooltip from feature descriptions for analyst readability
            desc = descriptions.get(feature, "")
            if desc:
                name_item.setToolTip(desc)
            self._feature_table.setItem(i, 1, name_item)
            
            # description
            desc = descriptions.get(feature, "")
            desc_item = QTableWidgetItem(desc)
            self._feature_table.setItem(i, 2, desc_item)
            
            # impact indicator (prepend a colored bullet to make scanning easier)
            impact = self._get_feature_impact(feature)
            bullet = "●"
            impact_text = f"{bullet} {impact}"
            impact_item = QTableWidgetItem(impact_text)
            impact_item.setTextAlignment(Qt.AlignCenter)
            impact_item.setData(Qt.UserRole, impact)
            # color the bullet/text to match existing background hints
            if impact == "High":
                impact_item.setForeground(QBrush(QColor(34, 112, 66)))
            elif impact == "Medium":
                impact_item.setForeground(QBrush(QColor(180, 140, 20)))
            else:
                impact_item.setForeground(QBrush(QColor(100, 100, 100)))
            impact_item.setToolTip(f"Impact level: {impact}")
            
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
            # add short helper tooltip for the tier combo
            combo.setToolTip(
                "Choose the feature set for this tier. 'All 20' is most detailed; 'Basic 5' is fastest."
            )
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
        self._advanced_check.setToolTip(
            "Adds more statistical features (lags, seasonal components). May increase runtime and memory usage."
        )
        layout.addWidget(self._advanced_check)

        # clearer advanced warning (hidden by default)
        self._advanced_warning = QLabel(
            "Advanced features add statistical transforms (lags, seasonality).\n" \
            "Recommended for larger datasets; increases runtime and memory."
        )
        self._advanced_warning.setStyleSheet("color: orange; font-size: 10px; margin-left: 20px;")
        self._advanced_warning.setVisible(False)
        self._advanced_warning.setToolTip(
            "Typical impact: ~3x runtime for small datasets; benefits vary by category."
        )
        layout.addWidget(self._advanced_warning)

        # process-based parallelism toggle (exposed in UI)
        self._use_processes_check = QCheckBox("Use process-based parallelism")
        self._use_processes_check.setToolTip(
            "Use processes for CPU-bound workloads. May increase memory and be slower on small datasets, especially on Windows."
        )
        # reflect current config default
        try:
            # prefer persisted session preference if available
            pref = None
            if hasattr(self, "_session") and getattr(self._session, "get_preference", None):
                pref = self._session.get_preference("use_processes", None)

            if pref is not None:
                self._use_processes_check.setChecked(bool(pref))
            else:
                self._use_processes_check.setChecked(bool(config.PERFORMANCE.get("use_processes", False)))
        except Exception:
            pass
        def _on_use_processes_changed(state):
            enabled = state == Qt.Checked
            try:
                config.PERFORMANCE.update({"use_processes": enabled})
            except Exception:
                pass
            try:
                # persist into session preferences
                if hasattr(self, "_session") and getattr(self._session, "set_preference", None):
                    self._session.set_preference("use_processes", enabled)
            except Exception:
                pass

        self._use_processes_check.stateChanged.connect(_on_use_processes_changed)
        layout.addWidget(self._use_processes_check)
        
        # Accessibility: text size and high-contrast theme
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Text size:"))
        self._text_size_combo = QComboBox()
        for s in config.UI_SETTINGS.get("text_size_options", [11, 12, 13, 14]):
            self._text_size_combo.addItem(str(s), s)
        # prefer persisted preference
        try:
            pref_size = None
            if hasattr(self, "_session") and getattr(self._session, "get_preference", None):
                pref_size = self._session.get_preference("text_size", None)
            if pref_size is not None:
                idx = self._text_size_combo.findData(int(pref_size))
                if idx >= 0:
                    self._text_size_combo.setCurrentIndex(idx)
            else:
                default_size = config.UI_SETTINGS.get("default_text_size", 12)
                idx = self._text_size_combo.findData(int(default_size))
                if idx >= 0:
                    self._text_size_combo.setCurrentIndex(idx)
        except Exception:
            pass

        self._text_size_combo.currentIndexChanged.connect(self._on_text_size_changed)
        size_layout.addWidget(self._text_size_combo)
        size_layout.addStretch()
        layout.addLayout(size_layout)

        self._high_contrast_check = QCheckBox("High contrast theme")
        self._high_contrast_check.setToolTip("Enable a high-contrast color theme for better readability")
        try:
            pref_hc = None
            if hasattr(self, "_session") and getattr(self._session, "get_preference", None):
                pref_hc = self._session.get_preference("high_contrast", None)
            if pref_hc is not None:
                self._high_contrast_check.setChecked(bool(pref_hc))
            else:
                self._high_contrast_check.setChecked(bool(config.UI_SETTINGS.get("high_contrast_default", False)))
        except Exception:
            pass

        self._high_contrast_check.stateChanged.connect(self._on_high_contrast_changed)
        layout.addWidget(self._high_contrast_check)
        
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

        # sample preview table (hidden until populated)
        self._preview_table = QTableWidget()
        self._preview_table.setVisible(False)
        self._preview_table.setMinimumHeight(140)
        self._preview_table.setAlternatingRowColors(True)
        # respond to edits (notes) — use cellChanged handler, suppressed during population
        self._preview_populating = False
        self._preview_table.cellChanged.connect(self._on_preview_cell_changed)
        layout.addWidget(self._preview_table)

        # explanation label under preview (small text)
        self._preview_explain_label = QLabel("")
        self._preview_explain_label.setWordWrap(True)
        # slightly darker and larger for readability
        self._preview_explain_label.setStyleSheet("color: #444; font-size: 12px; margin-top:4px;")
        layout.addWidget(self._preview_explain_label)

        # short help link
        help_btn = QPushButton("Learn more")
        help_btn.setMaximumWidth(120)
        help_btn.clicked.connect(self._open_forecast_help)
        layout.addWidget(help_btn)
        
        export_btn = QPushButton("Export Notes")
        export_btn.setMaximumWidth(120)
        export_btn.setToolTip("Export analyst notes/bookmarks as CSV to app data folder")
        export_btn.clicked.connect(self._export_bookmarks)
        layout.addWidget(export_btn)
        
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

    def _show_feature_set_details(self) -> None:
        # show a dialog listing the features in the currently selected feature set
        text = self._feature_set_combo.currentText()
        items = []
        if text == "All 20 Features":
            items = config.FEATURES.get("curated", [])
        elif text == "Top 10 Features":
            items = config.FEATURES.get("top_10", [])
        elif text == "Basic 5 Features":
            items = config.FEATURES.get("basic_5", [])
        elif text == "Tier-Based (Recommended)":
            # show per-tier summary (first few features as example)
            items = [f"A: {', '.join(config.FEATURES.get('curated', [])[:5])}",
                     f"B: {', '.join(config.FEATURES.get('top_10', [])[:5])}",
                     f"C: {', '.join(config.FEATURES.get('basic_5', [])[:5])}"]
        else:
            items = []

        body = "\n".join(items) if items else "No details available"
        QMessageBox.information(self, f"Features in {text}", body)

    def _on_text_size_changed(self, index: int) -> None:
        try:
            size = int(self._text_size_combo.currentData())
        except Exception:
            size = config.UI_SETTINGS.get("default_text_size", 12)

        # apply to application font
        try:
            app = QApplication.instance()
            if app is not None:
                f = app.font()
                f.setPointSize(size)
                app.setFont(f)
        except Exception:
            pass

        # persist preference
        try:
            if hasattr(self, "_session") and getattr(self._session, "set_preference", None):
                self._session.set_preference("text_size", size)
        except Exception:
            pass

    def _on_high_contrast_changed(self, state: int) -> None:
        enabled = state == Qt.Checked
        # apply a simple high-contrast stylesheet
        try:
            app = QApplication.instance()
            if app is not None:
                if enabled:
                    # minimal high-contrast stylesheet
                    app.setStyleSheet(
                        "QWidget { background-color: #000000; color: #FFFFFF; }"
                        "QPushButton { background-color: #222222; color: #FFFFFF; border: 1px solid #FFFFFF; }"
                        "QTableWidget { background-color: #000000; color: #FFFFFF; gridline-color: #444444; }"
                    )
                else:
                    app.setStyleSheet("")
        except Exception:
            pass

        try:
            if hasattr(self, "_session") and getattr(self._session, "set_preference", None):
                self._session.set_preference("high_contrast", enabled)
        except Exception:
            pass

    def _open_forecast_help(self) -> None:
        # open an existing help dialog that covers forecasting and advanced options
        dlg = ForecastHelpDialog(self)
        dlg.exec_()

    def _on_preview_cell_changed(self, row: int, col: int) -> None:
        # called when a cell is edited by the user; save notes for SKU bookmarks
        if getattr(self, "_preview_populating", False):
            return

        try:
            headers = [self._preview_table.horizontalHeaderItem(i).text() for i in range(self._preview_table.columnCount())]
        except Exception:
            return

        # note column is last column
        note_col_index = len(headers) - 1
        if col != note_col_index:
            return

        # find sku value in the row (heuristic: look for a header named sku or the mapped sku column)
        sku_val = None
        sku_candidates = [h for h in headers if h.lower() == "sku"]
        sku_index = None
        if sku_candidates:
            sku_index = headers.index(sku_candidates[0])
        else:
            # try to match processor mapping name
            try:
                mapped = self._processor.get_mapped_column("sku") if self._processor else None
                if mapped:
                    lowered = [h.lower() for h in headers]
                    if mapped.lower() in lowered:
                        sku_index = lowered.index(mapped.lower())
            except Exception:
                sku_index = None

        try:
            if sku_index is not None and sku_index < self._preview_table.columnCount():
                sku_item = self._preview_table.item(row, sku_index)
                if sku_item:
                    sku_val = sku_item.text()
        except Exception:
            sku_val = None

        # get note text
        note_item = self._preview_table.item(row, col)
        note_text = note_item.text() if note_item else ""

        if sku_val:
            try:
                # add or update bookmark with note
                if hasattr(self._session, "add_bookmark"):
                    self._session.add_bookmark(sku_val, note_text)
            except Exception:
                pass

    def _export_bookmarks(self) -> None:
        # export bookmarks to CSV in APP_DATA_DIR with timestamped filename
        try:
            bookmarks = self._session.get_bookmarks() if hasattr(self._session, "get_bookmarks") else []
            if not bookmarks:
                QMessageBox.information(self, "No Notes", "No analyst notes/bookmarks to export.")
                return

            p = config.APP_DATA_DIR
            p.mkdir(parents=True, exist_ok=True)
            fname = f"bookmarks_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            path = str(p / fname)

            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["sku", "note", "timestamp"])
                for b in bookmarks:
                    writer.writerow([b.get("sku"), b.get("note", ""), b.get("timestamp", "")])

            QMessageBox.information(self, "Exported", f"Notes exported to: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Error", f"Failed to export notes: {exc}")
    
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
            time_str = f"~{int(base_time)} seconds (approx.)"
        else:
            time_str = f"~{base_time/60:.1f} minutes (approx.)"

        self._estimate_label.setText(f"Estimated time: {time_str} for {sku_count:,} items")
        self._estimate_label.setToolTip(
            "Estimate is approximate and depends on CPU, parallel settings, and data size."
        )
        
        # populate sample preview table
        try:
            # if features were already created and stored in session, show real sample
            session_feats = None
            if hasattr(self._session, "get_features"):
                session_feats = self._session.get_features().get("data")

            headers = []
            rows = []

            if session_feats is not None and hasattr(session_feats, "head"):
                # attempt to use processor mappings for sku/date names
                sku_col = None
                date_col = None
                try:
                    if self._processor is not None:
                        sku_col = self._processor.get_mapped_column("sku")
                        date_col = self._processor.get_mapped_column("date")
                except Exception:
                    sku_col = None
                    date_col = None

                # choose columns that exist in the dataframe
                available_cols = list(getattr(session_feats, "columns", []))
                if sku_col in available_cols:
                    headers.append(sku_col)
                if date_col in available_cols and date_col not in headers:
                    headers.append(date_col)

                # add selected features that exist in data
                for f in selected:
                    if f in available_cols and f not in headers:
                        headers.append(f)

                sample = session_feats.head(5)
                # build rows from sample
                for _, r in sample.iterrows():
                    row = [str(r.get(c, "")) if c in sample.columns else "" for c in headers]
                    rows.append(row)
            else:
                # no real features yet; show placeholder preview
                headers = ["SKU", "Date"] + [f.replace("_", " ").title() for f in selected[:5]]
                for _ in range(5):
                    rows.append(["—"] * len(headers))

            # populate table widget
            if headers:
                # update explanation label with short descriptions for visible columns
                try:
                    explain_parts = []
                    for h in headers[:6]:
                        if h in config.FEATURE_DESCRIPTIONS:
                            explain_parts.append(f"{h}: {config.FEATURE_DESCRIPTIONS[h]}")
                    if explain_parts:
                        self._preview_explain_label.setText("  |  ".join(explain_parts))
                    else:
                        self._preview_explain_label.setText("")
                except Exception:
                    self._preview_explain_label.setText("")
                # add a Note column for analyst annotations
                note_col = "Note"
                if note_col not in headers:
                    headers.append(note_col)

                self._preview_populating = True
                try:
                    self._preview_table.setColumnCount(len(headers))
                    self._preview_table.setRowCount(len(rows))
                    self._preview_table.setHorizontalHeaderLabels(headers)

                    # set header tooltips from feature descriptions
                    for i, h in enumerate(headers):
                        desc = ""
                        # map known feature descriptions
                        if h in config.FEATURE_DESCRIPTIONS:
                            desc = config.FEATURE_DESCRIPTIONS.get(h, "")
                        elif h.lower() in ["sku", "date"]:
                            desc = "Identifier column" if h.lower() == "sku" else "Date column"
                        else:
                            desc = ""

                        hi = self._preview_table.horizontalHeaderItem(i)
                        if hi is not None and desc:
                            hi.setToolTip(desc)

                    # find index of sku column (if present) using mapped column name
                    sku_index = None
                    sku_col_name = None
                    try:
                        if self._processor is not None:
                            sku_col_name = self._processor.get_mapped_column("sku")
                    except Exception:
                        sku_col_name = None

                    if sku_col_name:
                        lowered = [str(h).lower() for h in headers]
                        try:
                            sku_index = lowered.index(sku_col_name.lower())
                        except ValueError:
                            sku_index = None

                    # map existing bookmarks by sku
                    bookmarks = {}
                    try:
                        for b in (self._session.get_bookmarks() if hasattr(self._session, "get_bookmarks") else []):
                            bookmarks[b["sku"]] = b.get("note", "")
                    except Exception:
                        bookmarks = {}

                    for r_index, r_vals in enumerate(rows):
                        for c_index, val in enumerate(r_vals):
                            item = QTableWidgetItem(str(val))
                            # make the Note column editable
                            if c_index == len(headers) - 1:
                                item.setFlags(item.flags() | Qt.ItemIsEditable)
                                # if sku is available, prefill note from bookmarks
                                try:
                                    if sku_index is not None and sku_index < len(rows[r_index]):
                                        sku_val = rows[r_index][sku_index]
                                        note_text = bookmarks.get(sku_val, "")
                                        item.setText(note_text or "")
                                except Exception:
                                    pass
                            else:
                                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

                            self._preview_table.setItem(r_index, c_index, item)

                    self._preview_table.setVisible(True)
                finally:
                    self._preview_populating = False
            else:
                self._preview_table.setVisible(False)
        except Exception:
            # on any failure, hide preview table
            try:
                self._preview_table.setVisible(False)
            except Exception:
                pass
    
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
                progress_callback,
                parallel=True,
                max_workers=config.PERFORMANCE.get("max_workers", 4),
                use_processes=config.PERFORMANCE.get("use_processes", False)
            )
        
        self._worker = WorkerThread(do_feature_creation)
        # update progress dialog and the tab status label
        self._worker.progress_signal.connect(progress.set_progress)
        self._worker.progress_signal.connect(lambda p: self._status_label.setText(f"Creating features — {int(p)}%"))
        self._worker.progress_text_signal.connect(lambda t: (progress.set_status(str(t)), self._status_label.setText(str(t))))
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