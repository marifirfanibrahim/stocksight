"""
data tab module
tab 1 data health check
handles file upload column mapping and data quality
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QFrame, QProgressBar,
    QScrollArea, QSplitter, QFileDialog, QMessageBox,
    QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QDragEnterEvent, QDropEvent
from typing import Optional, Dict
import os

import config
from core.data_processor import DataProcessor
from core.column_detector import ColumnDetector
from ui.widgets.virtual_data_table import VirtualDataTable
from ui.dialogs.column_mapping_dialog import ColumnMappingDialog
from utils.worker_threads import WorkerThread


# ============================================================================
#                              DATA TAB
# ============================================================================

class DataTab(QWidget):
    # data health check tab
    
    # signals
    data_loaded = pyqtSignal(dict)
    data_processed = pyqtSignal()
    proceed_requested = pyqtSignal()
    
    def __init__(self, session_model, parent=None):
        # initialize tab
        super().__init__(parent)
        
        self._session = session_model
        self._processor = DataProcessor()
        self._detector = ColumnDetector()
        self._worker = None
        self._flagged_skus = set()
        
        self._setup_ui()
        self._connect_signals()
        
        # enable drag and drop
        self.setAcceptDrops(True)
    
    # ---------- UI SETUP ----------
    
    def _setup_ui(self) -> None:
        # setup user interface
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # main splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # left panel - upload and quality
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # upload section
        left_layout.addWidget(self._create_upload_section())
        
        # column mapping display section
        left_layout.addWidget(self._create_mapping_display_section())
        
        # quality dashboard
        left_layout.addWidget(self._create_quality_section())
        
        # classification section
        left_layout.addWidget(self._create_classification_section())
        
        left_layout.addStretch()
        
        # proceed button
        self._proceed_btn = QPushButton("Proceed to Pattern Discovery →")
        self._proceed_btn.setEnabled(False)
        self._proceed_btn.setMinimumHeight(40)
        self._proceed_btn.clicked.connect(self.proceed_requested.emit)
        left_layout.addWidget(self._proceed_btn)
        
        splitter.addWidget(left_panel)
        
        # right panel - data preview
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        preview_header = QHBoxLayout()
        preview_label = QLabel("Data Preview")
        preview_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        preview_header.addWidget(preview_label)
        
        preview_header.addStretch()
        
        # flagged items indicator
        self._flagged_label = QLabel("")
        self._flagged_label.setStyleSheet("color: #FFD54F;")
        preview_header.addWidget(self._flagged_label)
        
        right_layout.addLayout(preview_header)
        
        self._data_table = VirtualDataTable()
        right_layout.addWidget(self._data_table)
        
        splitter.addWidget(right_panel)
        
        # set splitter sizes
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)
    
    def _create_upload_section(self) -> QGroupBox:
        # create file upload section
        group = QGroupBox("1. Upload Your Data")
        layout = QVBoxLayout(group)
        
        # drop zone
        self._drop_zone = QFrame()
        self._drop_zone.setFrameStyle(QFrame.StyledPanel)
        self._drop_zone.setMinimumHeight(100)
        self._drop_zone.setCursor(Qt.PointingHandCursor)
        
        drop_layout = QVBoxLayout(self._drop_zone)
        drop_layout.setAlignment(Qt.AlignCenter)
        
        drop_icon = QLabel("📁")
        drop_icon.setFont(QFont("Segoe UI", 28))
        drop_icon.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(drop_icon)
        
        drop_text = QLabel("Drag & drop your file here or click to browse")
        drop_text.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(drop_text)
        
        self._file_types_label = QLabel("Supports: CSV, Excel, Parquet")
        self._file_types_label.setAlignment(Qt.AlignCenter)
        self._file_types_label.setStyleSheet("font-size: 10px;")
        drop_layout.addWidget(self._file_types_label)
        
        layout.addWidget(self._drop_zone)
        
        # file info
        self._file_info_label = QLabel("")
        layout.addWidget(self._file_info_label)
        
        # column mapping button
        mapping_layout = QHBoxLayout()
        
        self._mapping_btn = QPushButton("📋 Edit Column Mapping")
        self._mapping_btn.setEnabled(False)
        self._mapping_btn.clicked.connect(self._show_mapping_dialog)
        mapping_layout.addWidget(self._mapping_btn)
        
        mapping_layout.addStretch()
        layout.addLayout(mapping_layout)
        
        return group
    
    def _create_mapping_display_section(self) -> QGroupBox:
        # create column mapping display section
        group = QGroupBox("Column Mapping")
        layout = QGridLayout(group)
        layout.setSpacing(8)
        
        # column labels
        self._mapping_labels = {}
        
        mappings = [
            ("date", "📅 Date:"),
            ("sku", "🏷 Item/SKU:"),
            ("quantity", "📊 Quantity:"),
            ("category", "📁 Category:"),
            ("price", "💰 Price:"),
            ("promo", "🎯 Promotion:")
        ]
        
        for i, (key, label_text) in enumerate(mappings):
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold;")
            layout.addWidget(label, i, 0)
            
            value_label = QLabel("Not mapped")
            value_label.setStyleSheet("color: #9E9E9E;")
            value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # allow copy
            self._mapping_labels[key] = value_label
            layout.addWidget(value_label, i, 1)
        
        return group
    
    def _create_quality_section(self) -> QGroupBox:
        # create data quality section
        group = QGroupBox("2. Data Quality Check")
        layout = QVBoxLayout(group)
        
        # quality score
        score_layout = QHBoxLayout()
        
        self._quality_score_label = QLabel("--")
        self._quality_score_label.setFont(QFont("Segoe UI", 36, QFont.Bold))
        self._quality_score_label.setAlignment(Qt.AlignCenter)
        self._quality_score_label.setMinimumWidth(80)
        score_layout.addWidget(self._quality_score_label)
        
        score_info = QVBoxLayout()
        self._quality_status_label = QLabel("Upload data to check quality")
        self._quality_status_label.setFont(QFont("Segoe UI", 12))
        score_info.addWidget(self._quality_status_label)
        
        self._quality_details_label = QLabel("")
        self._quality_details_label.setWordWrap(True)
        score_info.addWidget(self._quality_details_label)
        
        score_layout.addLayout(score_info)
        score_layout.addStretch()
        
        layout.addLayout(score_layout)
        
        # issues list
        self._issues_frame = QFrame()
        issues_layout = QVBoxLayout(self._issues_frame)
        issues_layout.setContentsMargins(0, 0, 0, 0)
        self._issues_label = QLabel("")
        self._issues_label.setWordWrap(True)
        self._issues_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        issues_layout.addWidget(self._issues_label)
        self._issues_frame.setVisible(False)
        layout.addWidget(self._issues_frame)
        
        # fix buttons
        fix_layout = QHBoxLayout()
        
        self._fix_btn = QPushButton("🔧 Apply Recommended Fixes")
        self._fix_btn.setEnabled(False)
        self._fix_btn.clicked.connect(self._apply_fixes)
        fix_layout.addWidget(self._fix_btn)
        
        fix_layout.addStretch()
        layout.addLayout(fix_layout)
        
        return group
    
    def _create_classification_section(self) -> QGroupBox:
        # create sku classification section
        group = QGroupBox("3. Item Classification (ABC Analysis)")
        layout = QVBoxLayout(group)
        
        # classification bars
        self._class_frame = QFrame()
        class_layout = QHBoxLayout(self._class_frame)
        
        for tier, color, desc in [("A", "#81C784", "High Volume"), 
                                   ("B", "#FFD54F", "Medium Volume"), 
                                   ("C", "#E57373", "Low Volume")]:
            tier_widget = QWidget()
            tier_layout = QVBoxLayout(tier_widget)
            tier_layout.setAlignment(Qt.AlignCenter)
            
            tier_label = QLabel(tier)
            tier_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
            tier_label.setAlignment(Qt.AlignCenter)
            tier_label.setStyleSheet(f"color: {color};")
            tier_layout.addWidget(tier_label)
            
            count_label = QLabel("--")
            count_label.setObjectName(f"tier_{tier}_count")
            count_label.setAlignment(Qt.AlignCenter)
            count_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            tier_layout.addWidget(count_label)
            
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("font-size: 10px;")
            desc_label.setAlignment(Qt.AlignCenter)
            tier_layout.addWidget(desc_label)
            
            class_layout.addWidget(tier_widget)
        
        layout.addWidget(self._class_frame)
        
        # explanation
        explain = QLabel("Items are classified using the 80/20 rule based on total volume")
        explain.setStyleSheet("font-style: italic;")
        layout.addWidget(explain)
        
        return group
    
    def _connect_signals(self) -> None:
        # connect widget signals
        self._drop_zone.mousePressEvent = lambda e: self._browse_file()
    
    # ---------- DRAG AND DROP ----------
    
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        # handle drag enter
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dragLeaveEvent(self, event) -> None:
        # handle drag leave
        pass
    
    def dropEvent(self, event: QDropEvent) -> None:
        # handle file drop
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self._load_file(file_path)
    
    # ---------- FILE LOADING ----------
    
    def _browse_file(self) -> None:
        # open file browser
        from utils.file_handlers import FileHandler
        handler = FileHandler()
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Data File",
            handler.last_directory,
            handler.get_open_filter()
        )
        
        if file_path:
            self._load_file(file_path)
    
    def _load_file(self, file_path: str) -> None:
        # load data file
        self._file_info_label.setText(f"Loading: {os.path.basename(file_path)}...")
        
        # run in background
        self._worker = WorkerThread(self._processor.load_file, file_path)
        self._worker.result_signal.connect(self._on_file_loaded)
        self._worker.error_signal.connect(self._on_load_error)
        self._worker.start()
    
    def _on_file_loaded(self, result: tuple) -> None:
        # handle file loaded
        success, message = result
        
        if success:
            # update ui
            file_info = self._processor.get_summary_stats()
            self._file_info_label.setText(
                f"✓ Loaded {file_info.get('total_rows', 0):,} rows"
            )
            
            # detect columns
            detections = self._detector.detect_columns(self._processor.raw_data)
            
            # get best mapping
            mapping = self._detector.get_best_mapping(detections)
            self._processor.set_column_mapping(mapping)
            
            # update mapping display
            self._update_mapping_display(mapping)
            
            # enable mapping button
            self._mapping_btn.setEnabled(True)
            
            # show preview
            self._data_table.set_data(self._processor.raw_data.head(1000))
            
            # store detections for dialog
            self._detections = detections
            
            # show mapping dialog for confirmation
            self._show_mapping_dialog()
        else:
            self._file_info_label.setText(f"✗ {message}")
            QMessageBox.warning(self, "Load Error", message)
    
    def _on_load_error(self, error: str) -> None:
        # handle load error
        self._file_info_label.setText(f"✗ Error: {error}")
        QMessageBox.critical(self, "Error", f"Failed to load file:\n{error}")
    
    def _update_mapping_display(self, mapping: Dict) -> None:
        # update mapping labels to show mapped columns
        for key, label in self._mapping_labels.items():
            if key in mapping:
                col_name = mapping[key]
                label.setText(f"→ {col_name}")
                label.setStyleSheet("color: #81C784; font-weight: bold;")
            else:
                label.setText("Not mapped")
                label.setStyleSheet("color: #9E9E9E;")
    
    # ---------- COLUMN MAPPING ----------
    
    def _show_mapping_dialog(self) -> None:
        # show column mapping dialog
        if self._processor.raw_data is None:
            return
        
        columns = list(self._processor.raw_data.columns)
        detections = getattr(self, "_detections", {})
        
        dialog = ColumnMappingDialog(columns, detections, self)
        dialog.mapping_confirmed.connect(self._on_mapping_confirmed)
        dialog.exec_()
    
    def _on_mapping_confirmed(self, mapping: Dict) -> None:
        # handle confirmed mapping
        self._processor.set_column_mapping(mapping)
        
        # update display
        self._update_mapping_display(mapping)
        
        # process data
        success, message = self._processor.process_data()
        
        if success:
            # update session
            self._session.set_data(self._processor.processed_data)
            self._session.set_column_mapping(mapping)
            self._session.update_state(
                total_skus=len(self._processor.sku_list),
                total_categories=len(self._processor.category_list)
            )
            
            # calculate quality
            self._calculate_quality()
            
            # classify skus
            self._classify_skus()
            
            # update preview with processed data
            self._data_table.set_data(self._processor.processed_data.head(1000))
            
            # emit signal
            self.data_processed.emit()
        else:
            QMessageBox.warning(self, "Processing Error", message)
    
    # ---------- DATA QUALITY ----------
    
    def _calculate_quality(self) -> None:
        # calculate and display data quality
        quality = self._processor.calculate_quality()
        
        score = quality.get("overall_score", 0)
        self._quality_score_label.setText(f"{score:.0f}")
        
        # color based on score
        color = config.get_quality_color(score)
        self._quality_score_label.setStyleSheet(f"color: {color};")
        
        # status text
        if score >= 90:
            status = "Excellent data quality!"
        elif score >= 75:
            status = "Good data quality"
        elif score >= 60:
            status = "Fair data quality - some fixes recommended"
        else:
            status = "Poor data quality - fixes required"
        
        self._quality_status_label.setText(status)
        
        # issues
        issues = quality.get("issues", [])
        if issues:
            issues_text = "\n".join([f"• {issue}" for issue in issues])
            self._issues_label.setText(issues_text)
            self._issues_frame.setVisible(True)
            self._fix_btn.setEnabled(True)
        else:
            self._issues_frame.setVisible(False)
            self._fix_btn.setEnabled(False)
        
        # details
        metrics = quality.get("metrics", {})
        details_parts = []
        for key, info in metrics.items():
            if isinstance(info, dict) and "value" in info:
                details_parts.append(f"{key.replace('_', ' ')}: {info['value']:.1f}%")
        
        self._quality_details_label.setText(" | ".join(details_parts))
        
        # update session
        self._session.update_state(data_quality_score=score)
    
    def _apply_fixes(self) -> None:
        # apply recommended data fixes
        fixes_applied = []
        
        # check for missing values
        quality = self._processor.data_quality
        
        for rec in quality.get("recommendations", []):
            if "missing" in rec.lower():
                success, msg = self._processor.apply_fix("fill_missing")
                if success:
                    fixes_applied.append(msg)
            elif "duplicate" in rec.lower():
                success, msg = self._processor.apply_fix("remove_duplicates")
                if success:
                    fixes_applied.append(msg)
            elif "negative" in rec.lower():
                success, msg = self._processor.apply_fix("fix_negatives")
                if success:
                    fixes_applied.append(msg)
        
        if fixes_applied:
            # recalculate quality
            self._calculate_quality()
            
            # update preview
            self._data_table.set_data(self._processor.processed_data.head(1000))
            
            # update session
            self._session.set_data(self._processor.processed_data)
            self._session.update_state(data_cleaned=True)
            
            QMessageBox.information(
                self, 
                "Fixes Applied", 
                "Applied fixes:\n" + "\n".join([f"• {f}" for f in fixes_applied])
            )
            
            # enable proceed
            self._proceed_btn.setEnabled(True)
    
    # ---------- SKU CLASSIFICATION ----------
    
    def _classify_skus(self) -> None:
        # classify skus into abc tiers
        classification = self._processor.classify_skus()
        
        for tier in ["A", "B", "C"]:
            count = len(classification.get(tier, []))
            total = len(self._processor.sku_list)
            pct = (count / total * 100) if total > 0 else 0
            
            label = self.findChild(QLabel, f"tier_{tier}_count")
            if label:
                label.setText(f"{count:,}\n({pct:.0f}%)")
        
        # store in session
        self._session.update_state(data_cleaned=True)
        
        # enable proceed
        self._proceed_btn.setEnabled(True)
    
    # ---------- FLAGGED ITEMS ----------
    
    def add_flagged_sku(self, sku: str) -> None:
        # add sku to flagged list
        self._flagged_skus.add(sku)
        self._update_flagged_display()
    
    def _update_flagged_display(self) -> None:
        # update flagged items display
        count = len(self._flagged_skus)
        if count > 0:
            self._flagged_label.setText(f"⚠ {count} item(s) flagged for review")
        else:
            self._flagged_label.setText("")
    
    def get_flagged_skus(self) -> set:
        # get flagged skus
        return self._flagged_skus.copy()
    
    # ---------- PUBLIC METHODS ----------
    
    def get_processor(self) -> DataProcessor:
        # get data processor
        return self._processor
    
    def get_classification(self) -> Dict:
        # get sku classification
        return self._processor.classify_skus()