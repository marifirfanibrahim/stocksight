"""
clustering config dialog
configure rule-based clustering thresholds
uses sliders with plain language labels
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QPushButton, QGroupBox, QFormLayout,
    QSpinBox, QDoubleSpinBox, QTabWidget, QWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from typing import Dict

import config


# ============================================================================
#                     CLUSTERING CONFIG DIALOG
# ============================================================================

class ClusteringConfigDialog(QDialog):
    # dialog for configuring clustering thresholds
    
    # signals
    config_changed = pyqtSignal(dict)
    
    def __init__(self, current_config: Dict = None, parent=None):
        # initialize dialog
        super().__init__(parent)
        
        self._config = current_config or config.CLUSTERING.copy()
        self._setup_ui()
        self._load_config()
    
    # ---------- UI SETUP ----------
    
    def _setup_ui(self) -> None:
        # setup user interface
        self.setWindowTitle("Clustering Settings")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # header
        header = QLabel("Adjust How Items Are Grouped")
        header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout.addWidget(header)
        
        desc = QLabel("These settings control how items are classified into volume tiers and pattern types.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray;")
        layout.addWidget(desc)
        
        # tabs
        tabs = QTabWidget()
        
        # volume tier tab
        volume_tab = QWidget()
        volume_layout = QVBoxLayout(volume_tab)
        volume_layout.addWidget(self._create_volume_group())
        volume_layout.addStretch()
        tabs.addTab(volume_tab, "Volume Tiers")
        
        # pattern type tab
        pattern_tab = QWidget()
        pattern_layout = QVBoxLayout(pattern_tab)
        pattern_layout.addWidget(self._create_pattern_group())
        pattern_layout.addStretch()
        tabs.addTab(pattern_tab, "Pattern Types")
        
        layout.addWidget(tabs)
        
        # preview label
        self._preview_label = QLabel("")
        self._preview_label.setStyleSheet("color: #666; font-style: italic;")
        self._preview_label.setWordWrap(True)
        layout.addWidget(self._preview_label)
        
        # buttons
        button_layout = QHBoxLayout()
        
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        apply_btn = QPushButton("Apply")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self._on_apply)
        button_layout.addWidget(apply_btn)
        
        layout.addLayout(button_layout)
    
    def _create_volume_group(self) -> QGroupBox:
        # create volume tier configuration group
        group = QGroupBox("Volume Tier Thresholds")
        layout = QFormLayout(group)
        layout.setSpacing(15)
        
        # explanation
        explain = QLabel("Items are classified as A (high), B (medium), or C (low) based on sales volume.")
        explain.setWordWrap(True)
        explain.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addRow(explain)
        
        # use percentiles checkbox
        self._use_percentiles = QPushButton("Use Percentile-Based Thresholds")
        self._use_percentiles.setCheckable(True)
        self._use_percentiles.setChecked(True)
        self._use_percentiles.clicked.connect(self._update_preview)
        layout.addRow(self._use_percentiles)
        
        # a threshold
        a_layout = QHBoxLayout()
        self._a_threshold = QSpinBox()
        self._a_threshold.setRange(0, 100000)
        self._a_threshold.setSingleStep(100)
        self._a_threshold.valueChanged.connect(self._update_preview)
        a_layout.addWidget(self._a_threshold)
        a_layout.addWidget(QLabel("units/week for A-items"))
        a_layout.addStretch()
        layout.addRow("A-item minimum:", a_layout)
        
        # b threshold
        b_layout = QHBoxLayout()
        self._b_threshold = QSpinBox()
        self._b_threshold.setRange(0, 10000)
        self._b_threshold.setSingleStep(10)
        self._b_threshold.valueChanged.connect(self._update_preview)
        b_layout.addWidget(self._b_threshold)
        b_layout.addWidget(QLabel("units/week for B-items"))
        b_layout.addStretch()
        layout.addRow("B-item minimum:", b_layout)
        
        # percentile settings
        pct_layout = QHBoxLayout()
        self._a_percentile = QSpinBox()
        self._a_percentile.setRange(50, 99)
        self._a_percentile.setValue(80)
        self._a_percentile.valueChanged.connect(self._update_preview)
        pct_layout.addWidget(QLabel("Top"))
        pct_layout.addWidget(self._a_percentile)
        pct_layout.addWidget(QLabel("% are A-items"))
        pct_layout.addStretch()
        layout.addRow("Percentile:", pct_layout)
        
        return group
    
    def _create_pattern_group(self) -> QGroupBox:
        # create pattern type configuration group
        group = QGroupBox("Pattern Detection Thresholds")
        layout = QFormLayout(group)
        layout.setSpacing(15)
        
        # explanation
        explain = QLabel("Items are classified by their sales pattern: seasonal, erratic, variable, or steady.")
        explain.setWordWrap(True)
        explain.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addRow(explain)
        
        # seasonal threshold
        seasonal_layout = QHBoxLayout()
        self._seasonal_threshold = QDoubleSpinBox()
        self._seasonal_threshold.setRange(0.1, 0.9)
        self._seasonal_threshold.setSingleStep(0.05)
        self._seasonal_threshold.setDecimals(2)
        self._seasonal_threshold.valueChanged.connect(self._update_preview)
        seasonal_layout.addWidget(self._seasonal_threshold)
        seasonal_layout.addWidget(QLabel("Q4 concentration for seasonal"))
        seasonal_layout.addStretch()
        layout.addRow("Seasonal:", seasonal_layout)
        
        # erratic threshold
        erratic_layout = QHBoxLayout()
        self._erratic_threshold = QDoubleSpinBox()
        self._erratic_threshold.setRange(0.3, 2.0)
        self._erratic_threshold.setSingleStep(0.1)
        self._erratic_threshold.setDecimals(2)
        self._erratic_threshold.valueChanged.connect(self._update_preview)
        erratic_layout.addWidget(self._erratic_threshold)
        erratic_layout.addWidget(QLabel("CV for erratic pattern"))
        erratic_layout.addStretch()
        layout.addRow("Erratic:", erratic_layout)
        
        # variable threshold
        variable_layout = QHBoxLayout()
        self._variable_threshold = QDoubleSpinBox()
        self._variable_threshold.setRange(0.1, 1.0)
        self._variable_threshold.setSingleStep(0.05)
        self._variable_threshold.setDecimals(2)
        self._variable_threshold.valueChanged.connect(self._update_preview)
        variable_layout.addWidget(self._variable_threshold)
        variable_layout.addWidget(QLabel("CV for variable (below = steady)"))
        variable_layout.addStretch()
        layout.addRow("Variable:", variable_layout)
        
        return group
    
    # ---------- CONFIG MANAGEMENT ----------
    
    def _load_config(self) -> None:
        # load configuration into controls
        vol = self._config.get("volume_thresholds", {})
        pat = self._config.get("pattern_thresholds", {})
        
        self._a_threshold.setValue(vol.get("A", 1000))
        self._b_threshold.setValue(vol.get("B", 100))
        
        pct = self._config.get("volume_percentiles", {})
        self._a_percentile.setValue(pct.get("A", 80))
        
        self._use_percentiles.setChecked(self._config.get("use_percentiles", True))
        
        self._seasonal_threshold.setValue(pat.get("seasonal", 0.6))
        self._erratic_threshold.setValue(pat.get("erratic", 0.8))
        self._variable_threshold.setValue(pat.get("variable", 0.3))
        
        self._update_preview()
    
    def _get_config(self) -> Dict:
        # get current configuration from controls
        return {
            "volume_thresholds": {
                "A": self._a_threshold.value(),
                "B": self._b_threshold.value(),
                "C": 0
            },
            "volume_percentiles": {
                "A": self._a_percentile.value(),
                "B": 50,
                "C": 0
            },
            "pattern_thresholds": {
                "seasonal": self._seasonal_threshold.value(),
                "erratic": self._erratic_threshold.value(),
                "variable": self._variable_threshold.value()
            },
            "use_percentiles": self._use_percentiles.isChecked()
        }
    
    def _update_preview(self) -> None:
        # update preview label
        cfg = self._get_config()
        
        if cfg["use_percentiles"]:
            pct = cfg["volume_percentiles"]["A"]
            vol_text = f"Top {100 - pct}% by volume are A-items"
        else:
            a_val = cfg["volume_thresholds"]["A"]
            vol_text = f"Items with {a_val}+ units/week are A-items"
        
        pat = cfg["pattern_thresholds"]
        pat_text = f"CV > {pat['erratic']} = erratic, CV < {pat['variable']} = steady"
        
        self._preview_label.setText(f"{vol_text}. {pat_text}")
    
    def _reset_defaults(self) -> None:
        # reset to default configuration
        self._config = config.CLUSTERING.copy()
        self._load_config()
    
    def _on_apply(self) -> None:
        # handle apply button
        new_config = self._get_config()
        self.config_changed.emit(new_config)
        self.accept()
    
    def get_config(self) -> Dict:
        # get current configuration
        return self._get_config()