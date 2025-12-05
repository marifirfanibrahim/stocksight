"""
data tab module
tab 1 data health check
handles file upload column mapping and data quality
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QFrame, QProgressBar,
    QScrollArea, QSplitter, QFileDialog, QMessageBox,
    QGridLayout, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QDragEnterEvent, QDropEvent, QColor
from typing import Optional, Dict
import os

import config
from core.data_processor import DataProcessor
from core.column_detector import ColumnDetector
from ui.widgets.virtual_data_table import VirtualDataTable
from ui.dialogs.column_mapping_dialog import ColumnMappingDialog
from ui.dialogs.sheet_selection_dialog import SheetSelectionDialog
from utils.worker_threads import WorkerThread
from utils.file_handlers import FileHandler


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
        self._file_handler = FileHandler()
        self._worker = None
        self._flagged_skus = set()
        self._pending_file_path = None
        self._pending_sheet_name = None
        
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
        self._proceed_btn.setStyleSheet(f"background-color: {config.UI_COLORS['primary']}; color: white; font-weight: bold;")
        self._proceed_btn.setToolTip("Continue to explore patterns in your data")
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
        self._flagged_label.setStyleSheet("color: #FFC107;")
        self._flagged_label.setCursor(Qt.PointingHandCursor)
        self._flagged_label.mousePressEvent = lambda e: self._show_flagged_items()
        preview_header.addWidget(self._flagged_label)
        
        right_layout.addLayout(preview_header)
        
        self._data_table = VirtualDataTable()
        self._data_table.setToolTip("Preview of your uploaded data (first 1000 rows)")
        right_layout.addWidget(self._data_table)
        
        splitter.addWidget(right_panel)
        
        # set splitter sizes
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)
    
    def _create_upload_section(self) -> QGroupBox:
        # create file upload section
        group = QGroupBox("1. Upload Your Data")
        group.setToolTip("Import your sales/demand data file")
        layout = QVBoxLayout(group)
        
        # drop zone
        self._drop_zone = QFrame()
        self._drop_zone.setFrameStyle(QFrame.StyledPanel)
        self._drop_zone.setMinimumHeight(100)
        self._drop_zone.setCursor(Qt.PointingHandCursor)
        self._drop_zone.setToolTip("Click to browse or drag & drop your data file here")
        
        drop_layout = QVBoxLayout(self._drop_zone)
        drop_layout.setAlignment(Qt.AlignCenter)
        
        drop_icon = QLabel("📁")
        drop_icon.setFont(QFont("Segoe UI", 28))
        drop_icon.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(drop_icon)
        
        drop_text = QLabel("Drag & drop your file here or click to browse")
        drop_text.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(drop_text)
        
        self._file_types_label = QLabel("Supports: CSV, Excel (with multiple sheets), Parquet")
        self._file_types_label.setAlignment(Qt.AlignCenter)
        self._file_types_label.setStyleSheet("font-size: 10px; color: #666;")
        drop_layout.addWidget(self._file_types_label)
        
        layout.addWidget(self._drop_zone)
        
        # file info
        self._file_info_label = QLabel("")
        layout.addWidget(self._file_info_label)
        
        # column mapping button
        mapping_layout = QHBoxLayout()
        
        self._mapping_btn = QPushButton("📋 Edit Column Mapping")
        self._mapping_btn.setEnabled(False)
        self._mapping_btn.setToolTip("Adjust how columns are mapped to date, item, quantity, etc.")
        self._mapping_btn.clicked.connect(self._show_mapping_dialog)
        mapping_layout.addWidget(self._mapping_btn)
        
        mapping_layout.addStretch()
        layout.addLayout(mapping_layout)
        
        return group
    
    def _create_mapping_display_section(self) -> QGroupBox:
        # create column mapping display section
        group = QGroupBox("Column Mapping")
        group.setToolTip("Shows how your data columns are mapped")
        layout = QGridLayout(group)
        layout.setSpacing(8)
        
        # column labels with tooltips
        self._mapping_labels = {}
        
        mappings = [
            ("date", "📅 Date:", "The column containing dates/timestamps"),
            ("sku", "🏷 Item/SKU:", "The column identifying unique items"),
            ("quantity", "📊 Quantity:", "The column with sales/demand numbers"),
            ("category", "📁 Category:", "Optional grouping for items"),
            ("price", "💰 Price:", "Optional price data for analysis"),
            ("promo", "🎯 Promotion:", "Optional promotion flags")
        ]
        
        for i, (key, label_text, tooltip) in enumerate(mappings):
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold;")
            label.setToolTip(tooltip)
            layout.addWidget(label, i, 0)
            
            value_label = QLabel("Not mapped")
            value_label.setStyleSheet("color: #9E9E9E;")
            value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            value_label.setToolTip(f"Click 'Edit Column Mapping' to set the {key} column")
            self._mapping_labels[key] = value_label
            layout.addWidget(value_label, i, 1)
        
        return group
    
    def _create_quality_section(self) -> QGroupBox:
        # create data quality section
        group = QGroupBox("2. Data Quality Check")
        group.setToolTip("Automatic assessment of your data quality")
        layout = QVBoxLayout(group)
        
        # quality score
        score_layout = QHBoxLayout()
        
        self._quality_score_label = QLabel("--")
        self._quality_score_label.setFont(QFont("Segoe UI", 36, QFont.Bold))
        self._quality_score_label.setAlignment(Qt.AlignCenter)
        self._quality_score_label.setMinimumWidth(80)
        self._quality_score_label.setToolTip("Overall data quality score (0-100)")
        score_layout.addWidget(self._quality_score_label)
        
        score_info = QVBoxLayout()
        self._quality_status_label = QLabel("Upload data to check quality")
        self._quality_status_label.setFont(QFont("Segoe UI", 12))
        score_info.addWidget(self._quality_status_label)
        
        self._quality_details_label = QLabel("")
        self._quality_details_label.setWordWrap(True)
        self._quality_details_label.setToolTip("Detailed quality metrics")
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
        self._issues_label.setToolTip("Issues found in your data that may affect forecasting")
        issues_layout.addWidget(self._issues_label)
        self._issues_frame.setVisible(False)
        layout.addWidget(self._issues_frame)
        
        # fix buttons
        fix_layout = QHBoxLayout()
        
        self._fix_btn = QPushButton("🔧 Apply Recommended Fixes")
        self._fix_btn.setEnabled(False)
        self._fix_btn.setToolTip("Automatically fix common data issues like missing values and duplicates")
        self._fix_btn.clicked.connect(self._apply_fixes)
        fix_layout.addWidget(self._fix_btn)
        
        fix_layout.addStretch()
        layout.addLayout(fix_layout)
        
        return group
    
    def _create_classification_section(self) -> QGroupBox:
        # create sku classification section
        group = QGroupBox("3. Item Classification (ABC Analysis)")
        group.setToolTip("Items grouped by volume using the Pareto (80/20) principle")
        layout = QVBoxLayout(group)
        
        # classification display
        self._class_frame = QFrame()
        class_layout = QHBoxLayout(self._class_frame)
        class_layout.setSpacing(20)
        
        tier_tooltips = {
            "A": "High-volume items - top 20% contributing ~80% of volume. These get detailed forecasting.",
            "B": "Medium-volume items - next 30% of items. Balanced forecasting approach.",
            "C": "Low-volume items - bottom 50% of items. Simple forecasting for efficiency."
        }
        
        for tier, color, desc in [("A", "#4CAF50", "High Volume"), 
                                   ("B", "#FF9800", "Medium Volume"), 
                                   ("C", "#F44336", "Low Volume")]:
            tier_widget = QWidget()
            tier_widget.setToolTip(tier_tooltips[tier])
            tier_layout = QVBoxLayout(tier_widget)
            tier_layout.setAlignment(Qt.AlignCenter)
            tier_layout.setSpacing(4)
            
            # tier letter
            tier_label = QLabel(tier)
            tier_label.setFont(QFont("Segoe UI", 32, QFont.Bold))
            tier_label.setAlignment(Qt.AlignCenter)
            tier_label.setStyleSheet(f"color: {color};")
            tier_layout.addWidget(tier_label)
            
            # count and percentage
            count_label = QLabel("--")
            count_label.setObjectName(f"tier_{tier}_count")
            count_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
            count_label.setAlignment(Qt.AlignCenter)
            count_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            tier_layout.addWidget(count_label)
            
            # description
            desc_label = QLabel(desc)
            desc_label.setFont(QFont("Segoe UI", 11))
            desc_label.setStyleSheet("color: #555;")
            desc_label.setAlignment(Qt.AlignCenter)
            tier_layout.addWidget(desc_label)
            
            class_layout.addWidget(tier_widget)
        
        layout.addWidget(self._class_frame)
        
        # explanation
        explain = QLabel("Items are classified using the 80/20 rule based on total volume")
        explain.setStyleSheet("font-style: italic; color: #666;")
        explain.setToolTip("A-items are the vital few, C-items are the trivial many")
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
        # open file browser starting from app folder
        # start from app folder instead of home directory
        start_dir = str(config.BASE_DIR)
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Data File",
            start_dir,
            self._file_handler.get_open_filter()
        )
        
        if file_path:
            self._load_file(file_path)
    
    def _load_file(self, file_path: str) -> None:
        # load data file - check for multiple sheets first
        self._pending_file_path = file_path
        self._pending_sheet_name = None
        
        # check if excel file with multiple sheets
        if file_path.lower().endswith(('.xlsx', '.xls')):
            sheet_info = self._processor.get_excel_sheet_info(file_path)
            
            if len(sheet_info) > 1:
                # show sheet selection dialog
                dialog = SheetSelectionDialog(file_path, sheet_info, self)
                dialog.sheet_selected.connect(self._on_sheet_selected)
                
                if dialog.exec_() != dialog.Accepted:
                    # user cancelled
                    self._pending_file_path = None
                    return
                
                # sheet name set by signal
            elif len(sheet_info) == 1:
                # single sheet - use it directly
                self._pending_sheet_name = list(sheet_info.keys())[0]
        
        # proceed with loading
        self._do_load_file()
    
    def _on_sheet_selected(self, sheet_name: str) -> None:
        # handle sheet selection from dialog
        self._pending_sheet_name = sheet_name
    
    def _do_load_file(self) -> None:
        # actually load the file
        if not self._pending_file_path:
            return
        
        file_path = self._pending_file_path
        sheet_name = self._pending_sheet_name
        
        self._file_info_label.setText(f"Loading: {os.path.basename(file_path)}...")
        
        if sheet_name:
            self._file_info_label.setText(f"Loading: {os.path.basename(file_path)} (sheet: {sheet_name})...")
        
        # run in background
        self._worker = WorkerThread(
            self._processor.load_file, 
            file_path, 
            sheet_name
        )
        self._worker.result_signal.connect(self._on_file_loaded)
        self._worker.error_signal.connect(self._on_load_error)
        self._worker.start()
    
    def _on_file_loaded(self, result: tuple) -> None:
        # handle file loaded
        success, message = result
        
        if success:
            # update ui
            file_info = self._processor.get_summary_stats()
            sheet_info = f" (sheet: {self._pending_sheet_name})" if self._pending_sheet_name else ""
            self._file_info_label.setText(
                f"✓ Loaded {file_info.get('total_rows', 0):,} rows{sheet_info}"
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
                label.setToolTip(f"Mapped to column: {col_name}")
            else:
                label.setText("Not mapped")
                label.setStyleSheet("color: #9E9E9E;")
                label.setToolTip(f"No column mapped for {key}")
    
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
        
        # get current quality issues
        quality = self._processor.data_quality
        issues = quality.get("issues", [])
        
        # apply fixes based on issues found
        for issue in issues:
            issue_lower = issue.lower()
            
            # check for missing values
            if "missing" in issue_lower:
                success, msg = self._processor.apply_fix("fill_missing", method="ffill")
                if success:
                    fixes_applied.append("Filled missing values")
            
            # check for duplicates
            elif "duplicate" in issue_lower:
                success, msg = self._processor.apply_fix("remove_duplicates")
                if success:
                    fixes_applied.append("Removed duplicate entries")
            
            # check for negative values
            elif "negative" in issue_lower:
                success, msg = self._processor.apply_fix("fix_negatives", method="zero")
                if success:
                    fixes_applied.append("Fixed negative values")
        
        if fixes_applied:
            # recalculate quality after fixes
            self._calculate_quality()
            
            # update preview
            self._data_table.set_data(self._processor.processed_data.head(1000))
            
            # update session
            self._session.set_data(self._processor.processed_data)
            self._session.update_state(data_cleaned=True)
            
            # show what was fixed
            QMessageBox.information(
                self, 
                "Fixes Applied", 
                "Applied the following fixes:\n" + "\n".join([f"• {f}" for f in fixes_applied])
            )
            
            # enable proceed
            self._proceed_btn.setEnabled(True)
        else:
            QMessageBox.information(
                self,
                "No Fixes Needed",
                "No recommended fixes to apply.\nYour data quality is already good!"
            )
    
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
            self._flagged_label.setText(f"⚠ {count} item(s) flagged for review - click to view")
            self._flagged_label.setToolTip("Items flagged from anomaly detection for data review")
        else:
            self._flagged_label.setText("")
            self._flagged_label.setToolTip("")
    
    def _show_flagged_items(self) -> None:
        # show dialog with flagged items
        if not self._flagged_skus:
            return
        
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Flagged Items")
        dialog.setText(f"The following {len(self._flagged_skus)} item(s) are flagged for review:")
        
        # create list of flagged items
        flagged_list = "\n".join([f"• {sku}" for sku in sorted(self._flagged_skus)])
        dialog.setDetailedText(flagged_list)
        dialog.setIcon(QMessageBox.Information)
        dialog.setStandardButtons(QMessageBox.Ok)
        dialog.exec_()
    
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