"""
data tab module
tab 1 data health check
handles file upload column mapping and data quality
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QFrame, QProgressBar,
    QScrollArea, QSplitter, QFileDialog, QMessageBox,
    QGridLayout, QListWidget, QListWidgetItem, QCheckBox,
    QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QDragEnterEvent, QDropEvent, QColor
from typing import Optional, Dict, List
import os

import config
from core.data_processor import DataProcessor
from core.column_detector import ColumnDetector
from ui.widgets.virtual_data_table import VirtualDataTable
from ui.dialogs.column_mapping_dialog import ColumnMappingDialog
from ui.dialogs.sheet_selection_dialog import SheetSelectionDialog
from ui.dialogs.abnormal_data_dialog import AbnormalDataDialog
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
    sku_flagged = pyqtSignal(str)  # signal when sku flagged, no tab change
    
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
        self._current_quality = {}
        
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
        
        # data statistics section
        left_layout.addWidget(self._create_stats_section())
        
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
        self._mapping_btn.clicked.connect(self._show_mapping_dialog)
        mapping_layout.addWidget(self._mapping_btn)
        
        mapping_layout.addStretch()
        layout.addLayout(mapping_layout)
        
        return group
    
    def _create_stats_section(self) -> QGroupBox:
        # create data statistics section
        group = QGroupBox("Data Statistics")
        layout = QGridLayout(group)
        layout.setSpacing(10)
        
        # sku count
        layout.addWidget(QLabel("Total Items (SKUs):"), 0, 0)
        self._sku_count_label = QLabel("--")
        self._sku_count_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self._sku_count_label.setStyleSheet("color: #2E86AB;")
        layout.addWidget(self._sku_count_label, 0, 1)
        
        # total rows
        layout.addWidget(QLabel("Total Rows:"), 1, 0)
        self._total_rows_label = QLabel("--")
        self._total_rows_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(self._total_rows_label, 1, 1)
        
        # displayed rows
        layout.addWidget(QLabel("Displayed Rows:"), 2, 0)
        self._displayed_rows_label = QLabel("--")
        self._displayed_rows_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(self._displayed_rows_label, 2, 1)
        
        # total columns
        layout.addWidget(QLabel("Total Columns:"), 3, 0)
        self._total_cols_label = QLabel("--")
        self._total_cols_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(self._total_cols_label, 3, 1)
        
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
            value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
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
        
        # action buttons
        action_layout = QHBoxLayout()
        
        self._view_abnormal_btn = QPushButton("👁 View Abnormal Data")
        self._view_abnormal_btn.setEnabled(False)
        self._view_abnormal_btn.clicked.connect(self._view_abnormal_data)
        action_layout.addWidget(self._view_abnormal_btn)
        
        self._fix_btn = QPushButton("🔧 Apply Fixes...")
        self._fix_btn.setEnabled(False)
        self._fix_btn.clicked.connect(self._show_fix_dialog)
        action_layout.addWidget(self._fix_btn)
        
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        return group
    
    def _create_classification_section(self) -> QGroupBox:
        # create sku classification section
        group = QGroupBox("3. Item Classification (ABC Analysis)")
        layout = QVBoxLayout(group)
        
        # classification display
        self._class_frame = QFrame()
        class_layout = QHBoxLayout(self._class_frame)
        class_layout.setSpacing(20)
        
        for tier, color, desc in [("A", "#4CAF50", "High Volume"), 
                                   ("B", "#FF9800", "Medium Volume"), 
                                   ("C", "#F44336", "Low Volume")]:
            tier_widget = QWidget()
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
            
            # update statistics
            self._update_statistics()
            
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
            preview_rows = min(1000, len(self._processor.raw_data))
            self._data_table.set_data(self._processor.raw_data.head(preview_rows))
            self._displayed_rows_label.setText(f"{preview_rows:,}")
            
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
    
    def _update_statistics(self) -> None:
        # update data statistics display
        if self._processor.raw_data is None:
            return
        
        total_rows = len(self._processor.raw_data)
        total_cols = len(self._processor.raw_data.columns)
        
        self._total_rows_label.setText(f"{total_rows:,}")
        self._total_cols_label.setText(f"{total_cols:,}")
        
        # sku count updated after processing
        self._sku_count_label.setText("--")
        self._displayed_rows_label.setText("--")
    
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
                file_path=self._pending_file_path or "",
                total_skus=len(self._processor.sku_list),
                total_categories=len(self._processor.category_list),
                total_rows=len(self._processor.processed_data)
            )
            
            # update sku count
            self._sku_count_label.setText(f"{len(self._processor.sku_list):,}")
            
            # calculate quality
            self._calculate_quality()
            
            # classify skus
            self._classify_skus()
            
            # update preview with processed data
            preview_rows = min(1000, len(self._processor.processed_data))
            self._data_table.set_data(self._processor.processed_data.head(preview_rows))
            self._displayed_rows_label.setText(f"{preview_rows:,}")
            
            # emit signal
            self.data_processed.emit()
        else:
            QMessageBox.warning(self, "Processing Error", message)
    
    # ---------- DATA QUALITY ----------
    
    def _calculate_quality(self) -> None:
        # calculate and display data quality
        quality = self._processor.calculate_quality()
        self._current_quality = quality
        
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
            self._view_abnormal_btn.setEnabled(True)
        else:
            self._issues_frame.setVisible(False)
            self._fix_btn.setEnabled(False)
            self._view_abnormal_btn.setEnabled(False)
        
        # details
        metrics = quality.get("metrics", {})
        details_parts = []
        for key, info in metrics.items():
            if isinstance(info, dict) and "value" in info:
                details_parts.append(f"{key.replace('_', ' ')}: {info['value']:.1f}%")
        
        self._quality_details_label.setText(" | ".join(details_parts))
        
        # update session
        self._session.update_state(data_quality_score=score)
    
    def _view_abnormal_data(self) -> None:
        # show abnormal data dialog
        if self._processor.processed_data is None:
            return
        
        dialog = AbnormalDataDialog(
            self._processor.processed_data,
            self._processor.column_mapping,
            self._current_quality,
            self
        )
        
        # connect fix signal
        dialog.fix_requested.connect(self._apply_single_fix)
        
        dialog.exec_()
    
    def _show_fix_dialog(self) -> None:
        # show dialog to choose which fixes to apply
        if self._processor.processed_data is None:
            return
        
        # create fix selection dialog
        dialog = FixSelectionDialog(self._current_quality, self)
        
        if dialog.exec_() == QDialog.Accepted:
            selected_fixes = dialog.get_selected_fixes()
            if selected_fixes:
                self._apply_selected_fixes(selected_fixes)
    
    def _apply_single_fix(self, fix_type: str, options: Dict) -> None:
        # apply a single fix type
        self._apply_selected_fixes([fix_type])
    
    def _apply_selected_fixes(self, fix_types: List[str]) -> None:
        # apply selected data fixes with confirmation
        if not fix_types:
            return
        
        # build fix descriptions
        fix_descriptions = {
            "missing": "Fill missing values using forward fill",
            "duplicates": "Aggregate duplicate entries by summing quantities",
            "negative": "Set negative values to zero",
            "outliers": "Remove rows with statistical outliers"
        }
        
        fix_list = "\n".join([f"• {fix_descriptions.get(f, f)}" for f in fix_types])
        
        reply = QMessageBox.question(
            self,
            "Confirm Fixes",
            f"The following fixes will be applied:\n\n{fix_list}\n\n"
            "This will modify your data. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        fixes_applied = []
        
        # apply each fix
        for fix_type in fix_types:
            if fix_type == "missing":
                success, msg = self._processor.apply_fix("fill_missing", method="ffill")
                if success:
                    fixes_applied.append("Filled missing values")
            
            elif fix_type == "duplicates":
                success, msg = self._processor.apply_fix("remove_duplicates")
                if success:
                    fixes_applied.append("Aggregated duplicate entries")
            
            elif fix_type == "negative":
                success, msg = self._processor.apply_fix("fix_negatives", method="zero")
                if success:
                    fixes_applied.append("Fixed negative values")
            
            elif fix_type == "outliers":
                success, msg = self._processor.apply_fix("remove_outliers", threshold=3.0)
                if success:
                    fixes_applied.append("Removed outliers")
        
        if fixes_applied:
            # recalculate quality after fixes
            self._calculate_quality()
            
            # update preview
            preview_rows = min(1000, len(self._processor.processed_data))
            self._data_table.set_data(self._processor.processed_data.head(preview_rows))
            self._displayed_rows_label.setText(f"{preview_rows:,}")
            
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
                "No Fixes Applied",
                "No fixes were successfully applied."
            )
    
    def _apply_fixes(self) -> None:
        # deprecated - use _show_fix_dialog instead
        self._show_fix_dialog()
    
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
        # add sku to flagged list - no tab change
        self._flagged_skus.add(sku)
        self._update_flagged_display()
        # emit signal instead of changing tab
        self.sku_flagged.emit(sku)
    
    def _update_flagged_display(self) -> None:
        # update flagged items display
        count = len(self._flagged_skus)
        if count > 0:
            self._flagged_label.setText(f"⚠ {count} item(s) flagged for review - click to view")
        else:
            self._flagged_label.setText("")
    
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


# ============================================================================
#                        FIX SELECTION DIALOG
# ============================================================================

class FixSelectionDialog(QDialog):
    # dialog for selecting which fixes to apply
    
    def __init__(self, quality_info: Dict, parent=None):
        # initialize dialog
        super().__init__(parent)
        
        self._quality_info = quality_info
        self._fix_checks = {}
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        # setup user interface
        self.setWindowTitle("Select Fixes to Apply")
        self.setMinimumWidth(450)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # header
        header = QLabel("Choose which fixes to apply to your data:")
        header.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(header)
        
        # description
        desc = QLabel("Each fix will modify your data. Review the options below.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)
        
        # fix options
        issues = self._quality_info.get("issues", [])
        issues_lower = " ".join(issues).lower()
        
        fix_options = [
            ("missing", "Fill missing values", 
             "Uses forward fill to replace missing values with previous values",
             "missing" in issues_lower),
            ("duplicates", "Aggregate duplicate entries",
             "Sums quantities for rows with same item and date",
             "duplicate" in issues_lower),
            ("negative", "Fix negative values",
             "Sets negative quantity values to zero",
             "negative" in issues_lower),
            ("outliers", "Remove statistical outliers",
             "Removes rows with values outside 3 standard deviations",
             False)  # outliers always optional
        ]
        
        for key, title, desc, has_issue in fix_options:
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 10)
            container_layout.setSpacing(2)
            
            check = QCheckBox(title)
            check.setFont(QFont("Segoe UI", 10, QFont.Bold))
            check.setEnabled(has_issue or key == "outliers")
            check.setChecked(has_issue)
            self._fix_checks[key] = check
            container_layout.addWidget(check)
            
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #666; margin-left: 20px; font-size: 9pt;")
            container_layout.addWidget(desc_label)
            
            if not has_issue and key != "outliers":
                no_issue = QLabel("✓ No issues detected")
                no_issue.setStyleSheet("color: #28A745; margin-left: 20px; font-size: 9pt;")
                container_layout.addWidget(no_issue)
            
            layout.addWidget(container)
        
        layout.addStretch()
        
        # buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_selected_fixes(self) -> List[str]:
        # get list of selected fix types
        return [key for key, check in self._fix_checks.items() 
                if check.isEnabled() and check.isChecked()]