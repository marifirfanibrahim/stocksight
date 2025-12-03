"""
settings dialog
application preferences and configuration
"""


# ================ IMPORTS ================

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QWidget, QGroupBox,
    QCheckBox, QSpinBox, QComboBox, QLineEdit,
    QFormLayout, QDoubleSpinBox, QFileDialog,
    QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import json
from pathlib import Path

from config import (
    Paths, WindowConfig, AutoTSConfig, ProfilingConfig,
    CleaningConfig, ExplorationConfig, FeatureConfig,
    ExportConfig
)
from core.state import STATE


# ================ SETTINGS DIALOG ================

class SettingsDialog(QDialog):
    """
    application settings dialog
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Settings")
        self.setMinimumSize(500, 600)
        self.setModal(True)
        
        self._create_ui()
        self._load_settings()
    
    def _create_ui(self):
        """
        create dialog ui
        """
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # ---------- TAB WIDGET ----------
        self.tabs = QTabWidget()
        
        # general tab
        general_tab = self._create_general_tab()
        self.tabs.addTab(general_tab, "General")
        
        # forecasting tab
        forecast_tab = self._create_forecast_tab()
        self.tabs.addTab(forecast_tab, "Forecasting")
        
        # profiling tab
        profiling_tab = self._create_profiling_tab()
        self.tabs.addTab(profiling_tab, "Profiling")
        
        # export tab
        export_tab = self._create_export_tab()
        self.tabs.addTab(export_tab, "Export")
        
        # advanced tab
        advanced_tab = self._create_advanced_tab()
        self.tabs.addTab(advanced_tab, "Advanced")
        
        layout.addWidget(self.tabs)
        
        # ---------- BUTTONS ----------
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_reset = QPushButton("Reset to Defaults")
        self.btn_reset.setProperty("secondary", True)
        self.btn_reset.clicked.connect(self._reset_defaults)
        btn_layout.addWidget(self.btn_reset)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setProperty("secondary", True)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        
        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self._save_and_close)
        btn_layout.addWidget(self.btn_save)
        
        layout.addLayout(btn_layout)
    
    def _create_general_tab(self) -> QWidget:
        """
        create general settings tab
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # ---------- APPEARANCE ----------
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout(appearance_group)
        
        self.chk_dark_mode = QCheckBox("Dark Mode")
        appearance_layout.addRow(self.chk_dark_mode)
        
        self.combo_font_size = QComboBox()
        self.combo_font_size.addItems(['Small', 'Medium', 'Large'])
        self.combo_font_size.setCurrentIndex(1)
        appearance_layout.addRow("Font Size:", self.combo_font_size)
        
        layout.addWidget(appearance_group)
        
        # ---------- BEHAVIOR ----------
        behavior_group = QGroupBox("Behavior")
        behavior_layout = QFormLayout(behavior_group)
        
        self.chk_auto_advance = QCheckBox("Auto-advance pipeline stages")
        behavior_layout.addRow(self.chk_auto_advance)
        
        self.chk_auto_clean = QCheckBox("Auto-clean data on load")
        behavior_layout.addRow(self.chk_auto_clean)
        
        self.chk_confirm_exit = QCheckBox("Confirm before exit")
        self.chk_confirm_exit.setChecked(True)
        behavior_layout.addRow(self.chk_confirm_exit)
        
        layout.addWidget(behavior_group)
        
        # ---------- OUTPUT ----------
        output_group = QGroupBox("Output Directory")
        output_layout = QVBoxLayout(output_group)
        
        dir_layout = QHBoxLayout()
        self.txt_output_dir = QLineEdit()
        self.txt_output_dir.setPlaceholderText("Default: Documents/Stocksight")
        dir_layout.addWidget(self.txt_output_dir)
        
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_output_dir)
        dir_layout.addWidget(btn_browse)
        
        output_layout.addLayout(dir_layout)
        
        self.chk_use_documents = QCheckBox("Use Documents folder")
        self.chk_use_documents.setChecked(True)
        output_layout.addWidget(self.chk_use_documents)
        
        layout.addWidget(output_group)
        
        layout.addStretch()
        
        return tab
    
    def _create_forecast_tab(self) -> QWidget:
        """
        create forecasting settings tab
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # ---------- DEFAULTS ----------
        defaults_group = QGroupBox("Default Values")
        defaults_layout = QFormLayout(defaults_group)
        
        self.spin_default_periods = QSpinBox()
        self.spin_default_periods.setRange(1, 365)
        self.spin_default_periods.setValue(AutoTSConfig.DEFAULT_FORECAST_DAYS)
        defaults_layout.addRow("Forecast Periods:", self.spin_default_periods)
        
        self.combo_default_granularity = QComboBox()
        self.combo_default_granularity.addItems(['Daily', 'Weekly', 'Monthly', 'Quarterly'])
        defaults_layout.addRow("Granularity:", self.combo_default_granularity)
        
        self.combo_default_speed = QComboBox()
        self.combo_default_speed.addItems(['Superfast', 'Fast', 'Balanced', 'Accurate'])
        self.combo_default_speed.setCurrentIndex(1)
        defaults_layout.addRow("Speed:", self.combo_default_speed)
        
        layout.addWidget(defaults_group)
        
        # ---------- MODEL ----------
        model_group = QGroupBox("Model Settings")
        model_layout = QFormLayout(model_group)
        
        self.spin_confidence = QDoubleSpinBox()
        self.spin_confidence.setRange(0.5, 0.99)
        self.spin_confidence.setSingleStep(0.05)
        self.spin_confidence.setValue(AutoTSConfig.PREDICTION_INTERVAL)
        model_layout.addRow("Confidence Interval:", self.spin_confidence)
        
        self.chk_show_confidence = QCheckBox("Show confidence bands")
        self.chk_show_confidence.setChecked(AutoTSConfig.SHOW_CONFIDENCE_BANDS)
        model_layout.addRow(self.chk_show_confidence)
        
        self.chk_no_negatives = QCheckBox("Prevent negative forecasts")
        self.chk_no_negatives.setChecked(True)
        model_layout.addRow(self.chk_no_negatives)
        
        layout.addWidget(model_group)
        
        # ---------- PERFORMANCE ----------
        perf_group = QGroupBox("Performance")
        perf_layout = QFormLayout(perf_group)
        
        self.combo_n_jobs = QComboBox()
        self.combo_n_jobs.addItems(['Auto', '1', '2', '4', '8'])
        perf_layout.addRow("Parallel Jobs:", self.combo_n_jobs)
        
        self.spin_max_skus = QSpinBox()
        self.spin_max_skus.setRange(10, 1000)
        self.spin_max_skus.setValue(100)
        perf_layout.addRow("Max SKUs per Batch:", self.spin_max_skus)
        
        layout.addWidget(perf_group)
        
        layout.addStretch()
        
        return tab
    
    def _create_profiling_tab(self) -> QWidget:
        """
        create profiling settings tab
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # ---------- REPORT ----------
        report_group = QGroupBox("Report Settings")
        report_layout = QFormLayout(report_group)
        
        self.chk_minimal_report = QCheckBox("Minimal report (faster)")
        report_layout.addRow(self.chk_minimal_report)
        
        self.chk_explorative = QCheckBox("Explorative analysis")
        self.chk_explorative.setChecked(ProfilingConfig.EXPLORATIVE)
        report_layout.addRow(self.chk_explorative)
        
        layout.addWidget(report_group)
        
        # ---------- SAMPLING ----------
        sampling_group = QGroupBox("Data Sampling")
        sampling_layout = QFormLayout(sampling_group)
        
        self.chk_sample_large = QCheckBox("Sample large datasets")
        self.chk_sample_large.setChecked(ProfilingConfig.SAMPLE_FOR_LARGE)
        sampling_layout.addRow(self.chk_sample_large)
        
        self.spin_sample_size = QSpinBox()
        self.spin_sample_size.setRange(1000, 100000)
        self.spin_sample_size.setValue(ProfilingConfig.SAMPLE_SIZE)
        sampling_layout.addRow("Sample Size:", self.spin_sample_size)
        
        self.spin_large_threshold = QSpinBox()
        self.spin_large_threshold.setRange(10000, 1000000)
        self.spin_large_threshold.setValue(ProfilingConfig.LARGE_THRESHOLD)
        sampling_layout.addRow("Large Dataset Threshold:", self.spin_large_threshold)
        
        layout.addWidget(sampling_group)
        
        # ---------- THRESHOLDS ----------
        threshold_group = QGroupBox("Thresholds")
        threshold_layout = QFormLayout(threshold_group)
        
        self.spin_missing_threshold = QDoubleSpinBox()
        self.spin_missing_threshold.setRange(0.01, 0.5)
        self.spin_missing_threshold.setSingleStep(0.01)
        self.spin_missing_threshold.setValue(ProfilingConfig.MISSING_THRESHOLD)
        threshold_layout.addRow("Missing Value Warning:", self.spin_missing_threshold)
        
        self.spin_corr_threshold = QDoubleSpinBox()
        self.spin_corr_threshold.setRange(0.5, 1.0)
        self.spin_corr_threshold.setSingleStep(0.05)
        self.spin_corr_threshold.setValue(ProfilingConfig.CORRELATION_THRESHOLD)
        threshold_layout.addRow("High Correlation:", self.spin_corr_threshold)
        
        layout.addWidget(threshold_group)
        
        layout.addStretch()
        
        return tab
    
    def _create_export_tab(self) -> QWidget:
        """
        create export settings tab
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # ---------- FORMAT ----------
        format_group = QGroupBox("Default Format")
        format_layout = QFormLayout(format_group)
        
        self.combo_default_format = QComboBox()
        self.combo_default_format.addItems(['CSV', 'Excel', 'JSON', 'Parquet'])
        format_layout.addRow("Export Format:", self.combo_default_format)
        
        self.chk_include_timestamp = QCheckBox("Include timestamp in filename")
        self.chk_include_timestamp.setChecked(True)
        format_layout.addRow(self.chk_include_timestamp)
        
        layout.addWidget(format_group)
        
        # ---------- CONTENT ----------
        content_group = QGroupBox("Export Content")
        content_layout = QFormLayout(content_group)
        
        self.chk_export_data = QCheckBox("Export cleaned data")
        self.chk_export_data.setChecked(True)
        content_layout.addRow(self.chk_export_data)
        
        self.chk_export_forecast = QCheckBox("Export forecast")
        self.chk_export_forecast.setChecked(True)
        content_layout.addRow(self.chk_export_forecast)
        
        self.chk_export_confidence = QCheckBox("Export confidence intervals")
        self.chk_export_confidence.setChecked(True)
        content_layout.addRow(self.chk_export_confidence)
        
        self.chk_export_charts = QCheckBox("Export charts")
        self.chk_export_charts.setChecked(True)
        content_layout.addRow(self.chk_export_charts)
        
        self.chk_export_summary = QCheckBox("Export summary report")
        self.chk_export_summary.setChecked(True)
        content_layout.addRow(self.chk_export_summary)
        
        layout.addWidget(content_group)
        
        # ---------- CSV ----------
        csv_group = QGroupBox("CSV Options")
        csv_layout = QFormLayout(csv_group)
        
        self.combo_csv_encoding = QComboBox()
        self.combo_csv_encoding.addItems(['utf-8', 'latin-1', 'cp1252'])
        csv_layout.addRow("Encoding:", self.combo_csv_encoding)
        
        self.chk_csv_index = QCheckBox("Include index column")
        self.chk_csv_index.setChecked(True)
        csv_layout.addRow(self.chk_csv_index)
        
        layout.addWidget(csv_group)
        
        layout.addStretch()
        
        return tab
    
    def _create_advanced_tab(self) -> QWidget:
        """
        create advanced settings tab
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # ---------- FEATURES ----------
        features_group = QGroupBox("Feature Engineering")
        features_layout = QFormLayout(features_group)
        
        self.combo_tsfresh_defaults = QComboBox()
        self.combo_tsfresh_defaults.addItems(['minimal', 'efficient', 'comprehensive'])
        self.combo_tsfresh_defaults.setCurrentIndex(1)
        features_layout.addRow("TSFresh Settings:", self.combo_tsfresh_defaults)
        
        self.spin_max_features = QSpinBox()
        self.spin_max_features.setRange(10, 500)
        self.spin_max_features.setValue(FeatureConfig.MAX_FEATURES)
        features_layout.addRow("Max Features:", self.spin_max_features)
        
        self.spin_relevance_threshold = QDoubleSpinBox()
        self.spin_relevance_threshold.setRange(0.01, 0.5)
        self.spin_relevance_threshold.setSingleStep(0.01)
        self.spin_relevance_threshold.setValue(FeatureConfig.RELEVANCE_THRESHOLD)
        features_layout.addRow("Relevance Threshold:", self.spin_relevance_threshold)
        
        layout.addWidget(features_group)
        
        # ---------- ANOMALY ----------
        anomaly_group = QGroupBox("Anomaly Detection")
        anomaly_layout = QFormLayout(anomaly_group)
        
        self.combo_anomaly_method = QComboBox()
        self.combo_anomaly_method.addItems([
            'Isolation Forest',
            'Local Outlier Factor',
            'Z-Score',
            'IQR'
        ])
        anomaly_layout.addRow("Default Method:", self.combo_anomaly_method)
        
        self.spin_contamination = QDoubleSpinBox()
        self.spin_contamination.setRange(0.01, 0.2)
        self.spin_contamination.setSingleStep(0.01)
        self.spin_contamination.setValue(ExplorationConfig.ANOMALY_CONTAMINATION)
        anomaly_layout.addRow("Contamination:", self.spin_contamination)
        
        layout.addWidget(anomaly_group)
        
        # ---------- CLEANING ----------
        cleaning_group = QGroupBox("Data Cleaning")
        cleaning_layout = QFormLayout(cleaning_group)
        
        self.combo_default_imputation = QComboBox()
        self.combo_default_imputation.addItems([
            'Forward Fill', 'Backward Fill', 'Mean', 'Median', 'Interpolate'
        ])
        cleaning_layout.addRow("Default Imputation:", self.combo_default_imputation)
        
        self.spin_outlier_threshold = QDoubleSpinBox()
        self.spin_outlier_threshold.setRange(1.0, 5.0)
        self.spin_outlier_threshold.setSingleStep(0.5)
        self.spin_outlier_threshold.setValue(CleaningConfig.OUTLIER_STD_THRESHOLD)
        cleaning_layout.addRow("Outlier Threshold (σ):", self.spin_outlier_threshold)
        
        self.spin_max_rollback = QSpinBox()
        self.spin_max_rollback.setRange(1, 50)
        self.spin_max_rollback.setValue(CleaningConfig.MAX_ROLLBACK_STATES)
        cleaning_layout.addRow("Max Rollback States:", self.spin_max_rollback)
        
        layout.addWidget(cleaning_group)
        
        layout.addStretch()
        
        return tab
    
    # ================ HELPERS ================
    
    def _browse_output_dir(self):
        """
        browse for output directory
        """
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            str(Paths.USER_OUTPUT)
        )
        
        if dir_path:
            self.txt_output_dir.setText(dir_path)
    
    def _load_settings(self):
        """
        load current settings
        """
        # load from state
        self.chk_dark_mode.setChecked(STATE.settings.get('dark_mode', True))
        self.chk_auto_advance.setChecked(STATE.settings.get('auto_advance', False))
        self.chk_auto_clean.setChecked(STATE.settings.get('auto_clean', False))
        
        # load from settings file if exists
        try:
            if Paths.SETTINGS_FILE.exists():
                with open(Paths.SETTINGS_FILE, 'r') as f:
                    saved = json.load(f)
                
                if 'output_dir' in saved:
                    self.txt_output_dir.setText(saved['output_dir'])
                    
        except Exception as e:
            print(f"error loading settings: {e}")
    
    def _save_settings(self):
        """
        save settings
        """
        # update state
        STATE.settings['dark_mode'] = self.chk_dark_mode.isChecked()
        STATE.settings['auto_advance'] = self.chk_auto_advance.isChecked()
        STATE.settings['auto_clean'] = self.chk_auto_clean.isChecked()
        
        # build settings dict
        settings = {
            'dark_mode': self.chk_dark_mode.isChecked(),
            'auto_advance': self.chk_auto_advance.isChecked(),
            'auto_clean': self.chk_auto_clean.isChecked(),
            'output_dir': self.txt_output_dir.text(),
            'default_periods': self.spin_default_periods.value(),
            'default_granularity': self.combo_default_granularity.currentText(),
            'default_speed': self.combo_default_speed.currentText(),
            'confidence_interval': self.spin_confidence.value()
        }
        
        # save to file
        try:
            Paths.DATA_DIR.mkdir(parents=True, exist_ok=True)
            
            with open(Paths.SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=2)
                
        except Exception as e:
            print(f"error saving settings: {e}")
    
    def _reset_defaults(self):
        """
        reset to default values
        """
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # reset values
            self.chk_dark_mode.setChecked(True)
            self.chk_auto_advance.setChecked(False)
            self.chk_auto_clean.setChecked(False)
            self.txt_output_dir.clear()
            self.spin_default_periods.setValue(AutoTSConfig.DEFAULT_FORECAST_DAYS)
            self.combo_default_granularity.setCurrentIndex(0)
            self.combo_default_speed.setCurrentIndex(1)
            self.spin_confidence.setValue(AutoTSConfig.PREDICTION_INTERVAL)
    
    def _save_and_close(self):
        """
        save settings and close dialog
        """
        self._save_settings()
        self.accept()