"""
forecast settings dialog
configure forecasting strategy and options
presents options in business terms
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QRadioButton, QButtonGroup,
    QSpinBox, QCheckBox, QComboBox, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from typing import Dict

import config


# ============================================================================
#                     FORECAST SETTINGS DIALOG
# ============================================================================

class ForecastSettingsDialog(QDialog):
    # dialog for configuring forecast settings
    
    # signals
    settings_confirmed = pyqtSignal(dict)
    
    def __init__(self, sku_count: int = 0, parent=None):
        # initialize dialog
        super().__init__(parent)
        
        self._sku_count = sku_count
        self._setup_ui()
    
    # ---------- UI SETUP ----------
    
    def _setup_ui(self) -> None:
        # setup user interface
        self.setWindowTitle("Forecast Settings")
        self.setMinimumWidth(550)
        self.setMinimumHeight(500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # header
        header = QLabel("Choose Your Forecasting Approach")
        header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout.addWidget(header)
        
        # strategy selection
        layout.addWidget(self._create_strategy_group())
        
        # separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #ddd;")
        layout.addWidget(line)
        
        # horizon selection
        layout.addWidget(self._create_horizon_group())
        
        # additional options
        layout.addWidget(self._create_options_group())
        
        # estimate label
        self._estimate_label = QLabel("")
        self._estimate_label.setStyleSheet("color: #666; font-style: italic; padding: 10px; background: #f5f5f5; border-radius: 5px;")
        self._estimate_label.setWordWrap(True)
        layout.addWidget(self._estimate_label)
        
        layout.addStretch()
        
        # buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        start_btn = QPushButton("Start Forecasting")
        start_btn.setDefault(True)
        start_btn.clicked.connect(self._on_start)
        button_layout.addWidget(start_btn)
        
        layout.addLayout(button_layout)
        
        # initial estimate
        self._update_estimate()
    
    def _create_strategy_group(self) -> QGroupBox:
        # create strategy selection group
        group = QGroupBox("Forecasting Strategy")
        layout = QVBoxLayout(group)
        
        self._strategy_group = QButtonGroup(self)
        
        strategies = config.FORECASTING
        
        for i, (key, info) in enumerate(strategies.items()):
            # strategy container
            container = QFrame()
            container.setFrameStyle(QFrame.StyledPanel)
            container.setStyleSheet("QFrame { padding: 10px; }")
            container_layout = QVBoxLayout(container)
            container_layout.setSpacing(5)
            
            # radio with icon and name
            radio = QRadioButton(f"{info['icon']} {info['name']}")
            radio.setFont(QFont("Segoe UI", 10, QFont.Bold))
            radio.setProperty("strategy_key", key)
            radio.toggled.connect(self._update_estimate)
            self._strategy_group.addButton(radio, i)
            container_layout.addWidget(radio)
            
            # description
            desc = QLabel(info["description"])
            desc.setStyleSheet("color: gray; margin-left: 20px;")
            container_layout.addWidget(desc)
            
            # time and recommendation
            details = QLabel(f"⏱ {info['time_estimate']} | Best for: {info['recommended_for']}")
            details.setStyleSheet("color: #888; font-size: 10px; margin-left: 20px;")
            container_layout.addWidget(details)
            
            layout.addWidget(container)
            
            # select balanced by default
            if key == "balanced":
                radio.setChecked(True)
        
        return group
    
    def _create_horizon_group(self) -> QGroupBox:
        # create forecast horizon group
        group = QGroupBox("Forecast Horizon")
        layout = QHBoxLayout(group)
        
        layout.addWidget(QLabel("Forecast for the next"))
        
        self._horizon_spin = QSpinBox()
        self._horizon_spin.setRange(7, 365)
        self._horizon_spin.setValue(30)
        self._horizon_spin.setSuffix(" days")
        self._horizon_spin.valueChanged.connect(self._update_estimate)
        layout.addWidget(self._horizon_spin)
        
        layout.addStretch()
        
        # quick select buttons
        for days, label in [(7, "1W"), (30, "1M"), (90, "3M"), (180, "6M")]:
            btn = QPushButton(label)
            btn.setMaximumWidth(50)
            btn.setProperty("days", days)
            btn.clicked.connect(self._set_horizon_from_button)
            layout.addWidget(btn)
        
        return group
    
    def _create_options_group(self) -> QGroupBox:
        # create additional options group
        group = QGroupBox("Additional Options")
        layout = QVBoxLayout(group)
        
        # tier-based processing
        self._tier_processing = QCheckBox("Use tier-based processing")
        self._tier_processing.setChecked(True)
        self._tier_processing.setToolTip("A-items get detailed models, C-items get simple models")
        layout.addWidget(self._tier_processing)
        
        # include confidence intervals
        self._include_intervals = QCheckBox("Include confidence intervals")
        self._include_intervals.setChecked(True)
        self._include_intervals.setToolTip("Calculate upper and lower bounds for forecasts")
        layout.addWidget(self._include_intervals)
        
        # generate comparison
        self._model_comparison = QCheckBox("Generate model comparison report")
        self._model_comparison.setChecked(False)
        self._model_comparison.setToolTip("Compare multiple models for each item")
        layout.addWidget(self._model_comparison)
        
        # process bookmarked first
        self._bookmarks_first = QCheckBox("Process bookmarked items first")
        self._bookmarks_first.setChecked(False)
        self._bookmarks_first.setToolTip("Prioritize items you've marked as important")
        layout.addWidget(self._bookmarks_first)
        
        return group
    
    # ---------- HELPERS ----------
    
    def _set_horizon_from_button(self) -> None:
        # set horizon from quick select button
        btn = self.sender()
        days = btn.property("days")
        self._horizon_spin.setValue(days)
    
    def _get_selected_strategy(self) -> str:
        # get currently selected strategy
        selected = self._strategy_group.checkedButton()
        if selected:
            return selected.property("strategy_key")
        return "balanced"
    
    def _update_estimate(self) -> None:
        # update time estimate label
        strategy = self._get_selected_strategy()
        horizon = self._horizon_spin.value()
        
        # get base time from config
        strategy_info = config.FORECASTING.get(strategy, {})
        time_str = strategy_info.get("time_estimate", "Unknown")
        
        # adjust estimate based on sku count
        if self._sku_count > 0:
            # simple scaling
            scale_factor = self._sku_count / 10000
            
            if strategy == "simple":
                minutes = 5 + (5 * scale_factor)
            elif strategy == "balanced":
                minutes = 20 + (10 * scale_factor)
            else:  # advanced
                minutes = 60 + (60 * scale_factor)
            
            if minutes < 60:
                time_estimate = f"~{int(minutes)} minutes"
            else:
                hours = minutes / 60
                time_estimate = f"~{hours:.1f} hours"
            
            sku_text = f"{self._sku_count:,} items"
        else:
            time_estimate = time_str
            sku_text = "your items"
        
        # build estimate message
        models = strategy_info.get("models", [])
        model_count = len(models)
        
        message = (
            f"📊 Estimated time: {time_estimate} for {sku_text}\n"
            f"🔧 Using {model_count} forecasting models\n"
            f"📅 Generating {horizon}-day forecasts"
        )
        
        if self._tier_processing.isChecked():
            message += "\n✓ Tier-based processing enabled (faster for large datasets)"
        
        self._estimate_label.setText(message)
    
    # ---------- ACTIONS ----------
    
    def _on_start(self) -> None:
        # handle start button
        settings = self.get_settings()
        self.settings_confirmed.emit(settings)
        self.accept()
    
    def get_settings(self) -> Dict:
        # get current settings
        return {
            "strategy": self._get_selected_strategy(),
            "horizon": self._horizon_spin.value(),
            "tier_processing": self._tier_processing.isChecked(),
            "include_intervals": self._include_intervals.isChecked(),
            "model_comparison": self._model_comparison.isChecked(),
            "bookmarks_first": self._bookmarks_first.isChecked()
        }
    
    def set_sku_count(self, count: int) -> None:
        # update sku count and refresh estimate
        self._sku_count = count
        self._update_estimate()