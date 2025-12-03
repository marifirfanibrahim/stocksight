"""
export dialog
configure and execute data export
"""


# ================ IMPORTS ================

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QCheckBox, QComboBox,
    QLineEdit, QFileDialog, QProgressBar, QFormLayout,
    QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from pathlib import Path
from datetime import datetime

from config import Paths, ExportConfig
from core.state import STATE
from core.data_operations import get_output_directory
from utils.export import (
    export_all, export_forecast, export_dataframe,
    ExportFormat
)


# ================ EXPORT WORKER ================

class ExportWorker(QThread):
    """
    background export worker
    """
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str, dict)
    
    def __init__(self, options: dict):
        super().__init__()
        self.options = options
    
    def run(self):
        """
        run export
        """
        try:
            self.progress.emit(10, "Preparing export...")
            
            output_dir = Path(self.options.get('output_dir', get_output_directory()))
            export_format = self.options.get('format', 'csv')
            
            paths = export_all(
                export_format=export_format,
                output_dir=output_dir,
                include_data=self.options.get('include_data', True),
                include_forecast=self.options.get('include_forecast', True),
                include_features=self.options.get('include_features', False),
                include_summary=self.options.get('include_summary', True)
            )
            
            self.progress.emit(100, "Export complete")
            self.finished.emit(True, f"Exported to {output_dir}", paths)
            
        except Exception as e:
            self.finished.emit(False, str(e), {})


# ================ EXPORT DIALOG ================

class ExportDialog(QDialog):
    """
    export configuration dialog
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Export Data")
        self.setMinimumSize(450, 500)
        self.setModal(True)
        
        self._worker = None
        
        self._create_ui()
        self._update_state()
    
    def _create_ui(self):
        """
        create dialog ui
        """
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # ---------- DESTINATION ----------
        dest_group = QGroupBox("Destination")
        dest_layout = QVBoxLayout(dest_group)
        
        dir_layout = QHBoxLayout()
        
        self.txt_output_dir = QLineEdit()
        self.txt_output_dir.setText(str(get_output_directory()))
        dir_layout.addWidget(self.txt_output_dir)
        
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_directory)
        dir_layout.addWidget(btn_browse)
        
        dest_layout.addLayout(dir_layout)
        
        layout.addWidget(dest_group)
        
        # ---------- FORMAT ----------
        format_group = QGroupBox("Format")
        format_layout = QFormLayout(format_group)
        
        self.combo_format = QComboBox()
        self.combo_format.addItems(['CSV', 'Excel', 'JSON', 'Parquet'])
        format_layout.addRow("File Format:", self.combo_format)
        
        self.chk_timestamp = QCheckBox("Add timestamp to filenames")
        self.chk_timestamp.setChecked(True)
        format_layout.addRow(self.chk_timestamp)
        
        layout.addWidget(format_group)
        
        # ---------- CONTENT ----------
        content_group = QGroupBox("Content")
        content_layout = QVBoxLayout(content_group)
        
        self.chk_data = QCheckBox("Cleaned Data")
        self.chk_data.setChecked(True)
        content_layout.addWidget(self.chk_data)
        
        self.chk_forecast = QCheckBox("Forecast Results")
        self.chk_forecast.setChecked(True)
        content_layout.addWidget(self.chk_forecast)
        
        self.chk_confidence = QCheckBox("Confidence Intervals")
        self.chk_confidence.setChecked(True)
        content_layout.addWidget(self.chk_confidence)
        
        self.chk_features = QCheckBox("Extracted Features")
        content_layout.addWidget(self.chk_features)
        
        self.chk_charts = QCheckBox("Charts (PNG)")
        self.chk_charts.setChecked(True)
        content_layout.addWidget(self.chk_charts)
        
        self.chk_summary = QCheckBox("Summary Report (TXT)")
        self.chk_summary.setChecked(True)
        content_layout.addWidget(self.chk_summary)
        
        self.chk_metrics = QCheckBox("Model Metrics")
        content_layout.addWidget(self.chk_metrics)
        
        layout.addWidget(content_group)
        
        # ---------- PROGRESS ----------
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: gray;")
        layout.addWidget(self.lbl_status)
        
        # ---------- BUTTONS ----------
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setProperty("secondary", True)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        
        self.btn_export = QPushButton("Export")
        self.btn_export.clicked.connect(self._start_export)
        btn_layout.addWidget(self.btn_export)
        
        layout.addLayout(btn_layout)
    
    def _browse_directory(self):
        """
        browse for output directory
        """
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            self.txt_output_dir.text()
        )
        
        if dir_path:
            self.txt_output_dir.setText(dir_path)
    
    def _update_state(self):
        """
        update checkbox states based on available data
        """
        has_data = STATE.clean_data is not None
        has_forecast = STATE.forecast_data is not None
        has_features = STATE.feature_data is not None
        has_metrics = bool(STATE.model_metrics)
        
        self.chk_data.setEnabled(has_data)
        self.chk_data.setChecked(has_data)
        
        self.chk_forecast.setEnabled(has_forecast)
        self.chk_forecast.setChecked(has_forecast)
        
        self.chk_confidence.setEnabled(has_forecast and STATE.upper_forecast is not None)
        
        self.chk_features.setEnabled(has_features)
        
        self.chk_metrics.setEnabled(has_metrics)
        
        # update export button
        self.btn_export.setEnabled(has_data or has_forecast)
    
    def _start_export(self):
        """
        start export process
        """
        # build options
        format_map = {
            'CSV': 'csv',
            'Excel': 'xlsx',
            'JSON': 'json',
            'Parquet': 'parquet'
        }
        
        options = {
            'output_dir': self.txt_output_dir.text(),
            'format': format_map.get(self.combo_format.currentText(), 'csv'),
            'include_data': self.chk_data.isChecked(),
            'include_forecast': self.chk_forecast.isChecked(),
            'include_features': self.chk_features.isChecked(),
            'include_summary': self.chk_summary.isChecked()
        }
        
        # disable controls
        self.btn_export.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # start worker
        self._worker = ExportWorker(options)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()
    
    def _on_progress(self, value: int, message: str):
        """
        handle progress update
        """
        self.progress_bar.setValue(value)
        self.lbl_status.setText(message)
    
    def _on_finished(self, success: bool, message: str, paths: dict):
        """
        handle export complete
        """
        self.btn_export.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            self.lbl_status.setText(message)
            self.lbl_status.setStyleSheet("color: #4caf50;")
            
            # show success dialog
            reply = QMessageBox.information(
                self,
                "Export Complete",
                f"{message}\n\nOpen output folder?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                import os
                import sys
                
                output_dir = self.txt_output_dir.text()
                
                if sys.platform == 'win32':
                    os.startfile(output_dir)
                elif sys.platform == 'darwin':
                    os.system(f'open "{output_dir}"')
                else:
                    os.system(f'xdg-open "{output_dir}"')
            
            self.accept()
        else:
            self.lbl_status.setText(f"Error: {message}")
            self.lbl_status.setStyleSheet("color: #f44336;")