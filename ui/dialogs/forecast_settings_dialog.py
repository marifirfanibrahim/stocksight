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
    
    def __init__(self, sku_count: int = 0, a_item_count: int = 0, parent=None):
        # initialize dialog
        super().__init__(parent)
        
        self._sku_count = sku_count
        self._a_item_count = a_item_count
        self._horizon_spin = None
        self._strategy_group = None
        self._frequency_combo = None
        self._tier_processing = None
        self._include_intervals = None
        self._model_comparison = None
        self._bookmarks_first = None
        self._estimate_label = None
        
        self._setup_ui()
    
    # ---------- UI SETUP ----------
    
    def _setup_ui(self) -> None:
        # setup user interface
        self.setWindowTitle("Forecast Settings")
        self.setMinimumWidth(580)
        self.setMinimumHeight(620)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
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
        layout.addWidget(line)
        
        # frequency and horizon
        layout.addWidget(self._create_frequency_group())
        
        # additional options
        layout.addWidget(self._create_options_group())
        
        # estimate label
        self._estimate_label = QLabel("")
        self._estimate_label.setStyleSheet("padding: 10px; border-radius: 5px;")
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
        
        # initial estimate update
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
            desc.setStyleSheet("margin-left: 20px;")
            container_layout.addWidget(desc)
            
            # time and recommendation
            details = QLabel(f"⏱ {info['time_estimate']} | Best for: {info['recommended_for']}")
            details.setStyleSheet("font-size: 10px; margin-left: 20px;")
            container_layout.addWidget(details)
            
            # special note for advanced - clarify A-items only
            if key == "advanced":
                scope_note = QLabel(f"⚠ Will only run on A-items ({self._a_item_count} items)")
                scope_note.setStyleSheet("color: #E65100; font-size: 10px; margin-left: 20px; font-weight: bold;")
                container_layout.addWidget(scope_note)
            
            layout.addWidget(container)
            
            # select balanced by default
            if key == "balanced":
                radio.setChecked(True)
        
        return group
    
    def _create_frequency_group(self) -> QGroupBox:
        # create frequency and horizon group
        group = QGroupBox("Forecast Frequency & Horizon")
        layout = QVBoxLayout(group)
        
        # frequency selector
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Forecast at:"))
        
        self._frequency_combo = QComboBox()
        self._frequency_combo.addItems([
            "Daily (day-by-day)",
            "Weekly (week totals)",
            "Monthly (month totals)"
        ])
        self._frequency_combo.currentIndexChanged.connect(self._on_frequency_changed)
        freq_layout.addWidget(self._frequency_combo)
        
        freq_layout.addStretch()
        layout.addLayout(freq_layout)
        
        # horizon selector
        horizon_layout = QHBoxLayout()
        horizon_layout.addWidget(QLabel("Forecast horizon:"))
        
        self._horizon_spin = QSpinBox()
        self._horizon_spin.setRange(7, 365)
        self._horizon_spin.setValue(30)
        self._horizon_spin.setSuffix(" days")
        self._horizon_spin.valueChanged.connect(self._update_estimate)
        horizon_layout.addWidget(self._horizon_spin)
        
        horizon_layout.addStretch()
        
        # quick select buttons
        for days, label in [(7, "1W"), (30, "1M"), (90, "3M"), (180, "6M"), (365, "1Y")]:
            btn = QPushButton(label)
            btn.setMaximumWidth(45)
            btn.setProperty("days", days)
            btn.clicked.connect(self._set_horizon_from_button)
            horizon_layout.addWidget(btn)
        
        layout.addLayout(horizon_layout)
        
        # periods info label
        self._periods_label = QLabel("")
        self._periods_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self._periods_label)
        
        self._update_periods_label()
        
        return group
    
    def _create_options_group(self) -> QGroupBox:
        # create additional options group
        group = QGroupBox("Additional Options")
        layout = QVBoxLayout(group)
        
        # tier-based processing
        self._tier_processing = QCheckBox("Use tier-based processing")
        self._tier_processing.setChecked(True)
        self._tier_processing.stateChanged.connect(self._update_estimate)
        layout.addWidget(self._tier_processing)
        
        tier_note = QLabel("A-items get individual attention, C-items use simpler models")
        tier_note.setStyleSheet("color: #666; font-size: 9px; margin-left: 20px;")
        layout.addWidget(tier_note)
        
        # include confidence intervals
        self._include_intervals = QCheckBox("Include confidence intervals")
        self._include_intervals.setChecked(True)
        layout.addWidget(self._include_intervals)
        
        # generate comparison
        self._model_comparison = QCheckBox("Generate model comparison report")
        self._model_comparison.setChecked(False)
        layout.addWidget(self._model_comparison)
        
        # process bookmarked first
        self._bookmarks_first = QCheckBox("Process bookmarked items first")
        self._bookmarks_first.setChecked(False)
        layout.addWidget(self._bookmarks_first)
        
        return group
    
    # ---------- HELPERS ----------
    
    def _set_horizon_from_button(self) -> None:
        # set horizon from quick select button
        btn = self.sender()
        days = btn.property("days")
        if self._horizon_spin:
            self._horizon_spin.setValue(days)
    
    def _get_selected_strategy(self) -> str:
        # get currently selected strategy
        if self._strategy_group:
            selected = self._strategy_group.checkedButton()
            if selected:
                return selected.property("strategy_key")
        return "balanced"
    
    def _get_selected_frequency(self) -> str:
        # get currently selected frequency
        if self._frequency_combo:
            text = self._frequency_combo.currentText()
            if "Daily" in text:
                return "D"
            elif "Weekly" in text:
                return "W"
            elif "Monthly" in text:
                return "M"
        return "D"
    
    def _on_frequency_changed(self) -> None:
        # handle frequency change
        self._update_periods_label()
        self._update_estimate()
    
    def _update_periods_label(self) -> None:
        # update periods info label
        if not self._horizon_spin or not self._periods_label:
            return
        
        horizon = self._horizon_spin.value()
        frequency = self._get_selected_frequency()
        
        if frequency == "D":
            periods = horizon
            period_text = "days"
        elif frequency == "W":
            periods = max(1, horizon // 7)
            period_text = "weeks"
        elif frequency == "M":
            periods = max(1, horizon // 30)
            period_text = "months"
        else:
            periods = horizon
            period_text = "periods"
        
        self._periods_label.setText(f"This will generate {periods} {period_text} of forecasts")
    
    def _update_estimate(self) -> None:
        # update time estimate label
        if not self._estimate_label or not self._horizon_spin:
            return
        
        strategy = self._get_selected_strategy()
        horizon = self._horizon_spin.value()
        frequency = self._get_selected_frequency()
        
        # get base time from config
        strategy_info = config.FORECASTING.get(strategy, {})
        time_str = strategy_info.get("time_estimate", "Unknown")
        
        # determine item count based on strategy
        if strategy == "advanced":
            # advanced only runs on A-items
            item_count = self._a_item_count
            item_text = f"{item_count:,} A-items only"
        else:
            item_count = self._sku_count
            item_text = f"{item_count:,} items"
        
        # adjust estimate based on item count and frequency
        if item_count > 0:
            scale_factor = item_count / 10000
            
            # frequency affects processing time
            freq_factor = {"D": 1.0, "W": 0.6, "M": 0.4}.get(frequency, 1.0)
            
            if strategy == "simple":
                minutes = (5 + (5 * scale_factor)) * freq_factor
            elif strategy == "balanced":
                minutes = (20 + (10 * scale_factor)) * freq_factor
            else:  # advanced
                minutes = (60 + (60 * scale_factor)) * freq_factor
            
            if minutes < 60:
                time_estimate = f"~{int(minutes)} minutes"
            else:
                hours = minutes / 60
                time_estimate = f"~{hours:.1f} hours"
        else:
            time_estimate = time_str
            item_text = "your items"
        
        # build estimate message
        models = strategy_info.get("models", [])
        model_count = len(models)
        
        # frequency label
        freq_labels = {"D": "daily", "W": "weekly", "M": "monthly"}
        freq_label = freq_labels.get(frequency, "daily")
        
        # calculate periods
        if frequency == "D":
            periods = horizon
        elif frequency == "W":
            periods = max(1, horizon // 7)
        elif frequency == "M":
            periods = max(1, horizon // 30)
        else:
            periods = horizon
        
        message = (
            f"📊 Estimated time: {time_estimate} for {item_text}\n"
            f"🔧 Using {model_count} forecasting models\n"
            f"📅 Generating {periods} {freq_label} forecast periods"
        )
        
        if strategy == "advanced":
            message += "\n⚠ Advanced strategy runs on A-items only for best accuracy"
        elif self._tier_processing and self._tier_processing.isChecked():
            message += "\n✓ Tier-based processing enabled (faster for large datasets)"
        
        self._estimate_label.setText(message)
        
        # update periods label
        self._update_periods_label()
    
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
            "horizon": self._horizon_spin.value() if self._horizon_spin else 30,
            "frequency": self._get_selected_frequency(),
            "tier_processing": self._tier_processing.isChecked() if self._tier_processing else True,
            "include_intervals": self._include_intervals.isChecked() if self._include_intervals else True,
            "model_comparison": self._model_comparison.isChecked() if self._model_comparison else False,
            "bookmarks_first": self._bookmarks_first.isChecked() if self._bookmarks_first else False
        }
    
    def set_sku_count(self, count: int) -> None:
        # update sku count and refresh estimate
        self._sku_count = count
        self._update_estimate()