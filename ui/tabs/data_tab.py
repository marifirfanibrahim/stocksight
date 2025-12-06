"""
data tab module
tab 1 data health check
handles file upload column mapping and data quality
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QFrame,
    QSplitter, QFileDialog, QMessageBox,
    QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QDragEnterEvent, QDropEvent
from typing import Optional, Dict, List, Tuple
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
        
        self.setAcceptDrops(True)
    
    # ---------- UI SETUP ----------
    
    def _setup_ui(self) -> None:
        # setup layout
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        splitter = QSplitter(Qt.Horizontal)
        
        # left panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(self._create_upload_section())
        left_layout.addWidget(self._create_stats_section())
        left_layout.addWidget(self._create_mapping_display_section())
        left_layout.addWidget(self._create_quality_section())
        left_layout.addWidget(self._create_classification_section())
        
        left_layout.addStretch()
        
        self._proceed_btn = QPushButton("Proceed to Pattern Discovery →")
        self._proceed_btn.setEnabled(False)
        self._proceed_btn.setMinimumHeight(40)
        self._proceed_btn.setStyleSheet(
            f"background-color: {config.UI_COLORS['primary']}; "
            f"color: white; font-weight: bold;"
        )
        self._proceed_btn.clicked.connect(self.proceed_requested.emit)
        left_layout.addWidget(self._proceed_btn)
        
        splitter.addWidget(left_panel)
        
        # right panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        header_layout = QHBoxLayout()
        preview_label = QLabel("Data Preview")
        preview_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        header_layout.addWidget(preview_label)
        
        header_layout.addStretch()
        
        self._flagged_label = QLabel("")
        self._flagged_label.setStyleSheet("color: #FFC107;")
        self._flagged_label.setCursor(Qt.PointingHandCursor)
        self._flagged_label.mousePressEvent = lambda e: self._show_flagged_items()
        header_layout.addWidget(self._flagged_label)
        
        right_layout.addLayout(header_layout)
        
        self._data_table = VirtualDataTable()
        right_layout.addWidget(self._data_table)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)
    
    def _create_upload_section(self) -> QGroupBox:
        # upload section
        group = QGroupBox("1. Upload Your Data")
        layout = QVBoxLayout(group)
        
        self._drop_zone = QFrame()
        self._drop_zone.setFrameStyle(QFrame.StyledPanel)
        self._drop_zone.setMinimumHeight(100)
        self._drop_zone.setCursor(Qt.PointingHandCursor)
        
        dz_layout = QVBoxLayout(self._drop_zone)
        dz_layout.setAlignment(Qt.AlignCenter)
        
        icon = QLabel("📁")
        icon.setFont(QFont("Segoe UI", 28))
        icon.setAlignment(Qt.AlignCenter)
        dz_layout.addWidget(icon)
        
        text = QLabel("Drag & drop your file here or click to browse")
        text.setAlignment(Qt.AlignCenter)
        dz_layout.addWidget(text)
        
        self._file_types_label = QLabel("Supports: CSV, Excel (with multiple sheets), Parquet")
        self._file_types_label.setAlignment(Qt.AlignCenter)
        self._file_types_label.setStyleSheet("font-size: 10px; color: #666;")
        dz_layout.addWidget(self._file_types_label)
        
        layout.addWidget(self._drop_zone)
        
        self._file_info_label = QLabel("")
        layout.addWidget(self._file_info_label)
        
        map_layout = QHBoxLayout()
        self._mapping_btn = QPushButton("📋 Edit Column Mapping")
        self._mapping_btn.setEnabled(False)
        self._mapping_btn.clicked.connect(self._show_mapping_dialog)
        map_layout.addWidget(self._mapping_btn)
        map_layout.addStretch()
        layout.addLayout(map_layout)
        
        return group
    
    def _create_stats_section(self) -> QGroupBox:
        # stats section
        group = QGroupBox("Data Statistics")
        layout = QGridLayout(group)
        layout.setSpacing(10)
        
        layout.addWidget(QLabel("Total Items (SKUs):"), 0, 0)
        self._sku_count_label = QLabel("--")
        self._sku_count_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self._sku_count_label.setStyleSheet("color: #2E86AB;")
        layout.addWidget(self._sku_count_label, 0, 1)
        
        layout.addWidget(QLabel("Total Rows:"), 1, 0)
        self._total_rows_label = QLabel("--")
        self._total_rows_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(self._total_rows_label, 1, 1)
        
        layout.addWidget(QLabel("Displayed Rows:"), 2, 0)
        self._displayed_rows_label = QLabel("--")
        self._displayed_rows_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(self._displayed_rows_label, 2, 1)
        
        layout.addWidget(QLabel("Total Columns:"), 3, 0)
        self._total_cols_label = QLabel("--")
        self._total_cols_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(self._total_cols_label, 3, 1)
        
        return group
    
    def _create_mapping_display_section(self) -> QGroupBox:
        # mapping section
        group = QGroupBox("Column Mapping")
        layout = QGridLayout(group)
        layout.setSpacing(8)
        
        self._mapping_labels: Dict[str, QLabel] = {}
        
        rows = [
            ("date", "📅 Date:"),
            ("sku", "🏷 Item/SKU:"),
            ("quantity", "📊 Quantity:"),
            ("category", "📁 Category:"),
            ("price", "💰 Price:"),
            ("promo", "🎯 Promotion:")
        ]
        
        for i, (key, label_text) in enumerate(rows):
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold;")
            layout.addWidget(label, i, 0)
            
            value = QLabel("Not mapped")
            value.setStyleSheet("color: #9E9E9E;")
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self._mapping_labels[key] = value
            layout.addWidget(value, i, 1)
        
        return group
    
    def _create_quality_section(self) -> QGroupBox:
        # quality section
        group = QGroupBox("2. Data Quality Check")
        layout = QVBoxLayout(group)
        
        score_layout = QHBoxLayout()
        
        self._quality_score_label = QLabel("--")
        self._quality_score_label.setFont(QFont("Segoe UI", 36, QFont.Bold))
        self._quality_score_label.setAlignment(Qt.AlignCenter)
        self._quality_score_label.setMinimumWidth(80)
        score_layout.addWidget(self._quality_score_label)
        
        info_layout = QVBoxLayout()
        self._quality_status_label = QLabel("Upload data to check quality")
        self._quality_status_label.setFont(QFont("Segoe UI", 12))
        info_layout.addWidget(self._quality_status_label)
        
        self._quality_details_label = QLabel("")
        self._quality_details_label.setWordWrap(True)
        info_layout.addWidget(self._quality_details_label)
        
        score_layout.addLayout(info_layout)
        score_layout.addStretch()
        
        layout.addLayout(score_layout)
        
        self._issues_frame = QFrame()
        issues_layout = QVBoxLayout(self._issues_frame)
        issues_layout.setContentsMargins(0, 0, 0, 0)
        
        self._issues_label = QLabel("")
        self._issues_label.setWordWrap(True)
        self._issues_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        issues_layout.addWidget(self._issues_label)
        
        self._issues_frame.setVisible(False)
        layout.addWidget(self._issues_frame)
        
        btn_layout = QHBoxLayout()
        
        self._view_abnormal_btn = QPushButton("👁 View Abnormal Data")
        self._view_abnormal_btn.setEnabled(False)
        self._view_abnormal_btn.clicked.connect(self._view_abnormal_data)
        btn_layout.addWidget(self._view_abnormal_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return group
    
    def _create_classification_section(self) -> QGroupBox:
        # classification section
        group = QGroupBox("3. Item Classification (ABC Analysis)")
        layout = QVBoxLayout(group)
        
        self._class_frame = QFrame()
        class_layout = QHBoxLayout(self._class_frame)
        class_layout.setSpacing(20)
        
        for tier, color, desc in [
            ("A", "#4CAF50", "High Volume"),
            ("B", "#FF9800", "Medium Volume"),
            ("C", "#F44336", "Low Volume")
        ]:
            tier_widget = QWidget()
            tier_layout = QVBoxLayout(tier_widget)
            tier_layout.setAlignment(Qt.AlignCenter)
            tier_layout.setSpacing(4)
            
            t_label = QLabel(tier)
            t_label.setFont(QFont("Segoe UI", 32, QFont.Bold))
            t_label.setAlignment(Qt.AlignCenter)
            t_label.setStyleSheet(f"color: {color};")
            tier_layout.addWidget(t_label)
            
            count_label = QLabel("--")
            count_label.setObjectName(f"tier_{tier}_count")
            count_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
            count_label.setAlignment(Qt.AlignCenter)
            count_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            tier_layout.addWidget(count_label)
            
            d_label = QLabel(desc)
            d_label.setFont(QFont("Segoe UI", 11))
            d_label.setStyleSheet("color: #555;")
            d_label.setAlignment(Qt.AlignCenter)
            tier_layout.addWidget(d_label)
            
            class_layout.addWidget(tier_widget)
        
        layout.addWidget(self._class_frame)
        
        explain = QLabel("Items are classified using the 80/20 rule based on total volume")
        explain.setStyleSheet("font-style: italic; color: #666;")
        layout.addWidget(explain)
        
        return group
    
    # ---------- SIGNALS ----------
    
    def _connect_signals(self) -> None:
        # connect ui signals
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
        # handle drop
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self._load_file(file_path)
    
    # ---------- FILE LOADING ----------
    
    def _browse_file(self) -> None:
        # open file picker
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
        # start load with sheet detection
        self._pending_file_path = file_path
        self._pending_sheet_name = None
        
        if file_path.lower().endswith((".xlsx", ".xls")):
            sheet_info = self._processor.get_excel_sheet_info(file_path)
            if len(sheet_info) > 1:
                dialog = SheetSelectionDialog(file_path, sheet_info, self)
                dialog.sheet_selected.connect(self._on_sheet_selected)
                if dialog.exec_() != dialog.Accepted:
                    self._pending_file_path = None
                    return
            elif len(sheet_info) == 1:
                self._pending_sheet_name = list(sheet_info.keys())[0]
        
        self._do_load_file()
    
    def _on_sheet_selected(self, sheet_name: str) -> None:
        # store sheet name
        self._pending_sheet_name = sheet_name
    
    def _do_load_file(self) -> None:
        # run loader in worker
        if not self._pending_file_path:
            return
        
        file_path = self._pending_file_path
        sheet_name = self._pending_sheet_name
        
        if sheet_name:
            self._file_info_label.setText(
                f"Loading: {os.path.basename(file_path)} (sheet: {sheet_name})..."
            )
        else:
            self._file_info_label.setText(f"Loading: {os.path.basename(file_path)}...")
        
        self._worker = WorkerThread(
            self._processor.load_file,
            file_path,
            sheet_name
        )
        self._worker.result_signal.connect(self._on_file_loaded)
        self._worker.error_signal.connect(self._on_load_error)
        self._worker.start()
    
    def _on_file_loaded(self, result: Tuple[bool, str]) -> None:
        # file loaded
        success, message = result
        
        if not success:
            self._file_info_label.setText(f"✗ {message}")
            QMessageBox.warning(self, "Load Error", message)
            return
        
        stats = self._processor.get_summary_stats()
        sheet_info = f" (sheet: {self._pending_sheet_name})" if self._pending_sheet_name else ""
        self._file_info_label.setText(
            f"✓ Loaded {stats.get('total_rows', 0):,} rows{sheet_info}"
        )
        
        self._update_statistics()
        
        detections = self._detector.detect_columns(self._processor.raw_data)
        mapping = self._detector.get_best_mapping(detections)
        self._processor.set_column_mapping(mapping)
        self._update_mapping_display(mapping)
        
        self._mapping_btn.setEnabled(True)
        
        preview_rows = min(1000, len(self._processor.raw_data))
        self._data_table.set_data(self._processor.raw_data.head(preview_rows))
        self._displayed_rows_label.setText(f"{preview_rows:,}")
        
        self._detections = detections
        
        self._show_mapping_dialog()
    
    def _on_load_error(self, error: str) -> None:
        # loader error
        self._file_info_label.setText(f"✗ Error: {error}")
        QMessageBox.critical(self, "Error", f"Failed to load file:\n{error}")
    
    def _update_statistics(self) -> None:
        # update stats based on processed data if present
        if self._processor.processed_data is not None:
            df = self._processor.processed_data
        elif self._processor.raw_data is not None:
            df = self._processor.raw_data
        else:
            return
        
        total_rows = len(df)
        total_cols = len(df.columns)
        
        self._total_rows_label.setText(f"{total_rows:,}")
        self._total_cols_label.setText(f"{total_cols:,}")
        if self._processor.sku_list:
            self._sku_count_label.setText(f"{len(self._processor.sku_list):,}")
        else:
            self._sku_count_label.setText("--")
    
    def _update_mapping_display(self, mapping: Dict[str, str]) -> None:
        # mapping labels update
        for key, label in self._mapping_labels.items():
            if key in mapping:
                col = mapping[key]
                label.setText(f"→ {col}")
                label.setStyleSheet("color: #81C784; font-weight: bold;")
            else:
                label.setText("Not mapped")
                label.setStyleSheet("color: #9E9E9E;")
    
    # ---------- MAPPING ----------
    
    def _show_mapping_dialog(self) -> None:
        # open mapping dialog
        if self._processor.raw_data is None:
            return
        
        columns = list(self._processor.raw_data.columns)
        detections = getattr(self, "_detections", {})
        
        dialog = ColumnMappingDialog(columns, detections, self)
        dialog.mapping_confirmed.connect(self._on_mapping_confirmed)
        dialog.exec_()
    
    def _on_mapping_confirmed(self, mapping: Dict[str, str]) -> None:
        # handle mapping confirmation
        self._processor.set_column_mapping(mapping)
        self._update_mapping_display(mapping)
        
        success, message = self._processor.process_data()
        if not success:
            QMessageBox.warning(self, "Processing Error", message)
            return
        
        self._session.set_data(self._processor.processed_data)
        self._session.set_column_mapping(mapping)
        self._session.update_state(
            file_path=self._pending_file_path or "",
            total_skus=len(self._processor.sku_list),
            total_categories=len(self._processor.category_list),
            total_rows=len(self._processor.processed_data)
        )
        
        self._sku_count_label.setText(f"{len(self._processor.sku_list):,}")
        
        self._calculate_quality()
        self._classify_skus()
        
        preview_rows = min(1000, len(self._processor.processed_data))
        self._data_table.set_data(self._processor.processed_data.head(preview_rows))
        self._displayed_rows_label.setText(f"{preview_rows:,}")
        
        self._update_statistics()
        
        self.data_processed.emit()
    
    # ---------- QUALITY ----------
    
    def _calculate_quality(self) -> None:
        # quality metrics update
        quality = self._processor.calculate_quality()
        self._current_quality = quality
        
        score = quality.get("overall_score", 0)
        self._quality_score_label.setText(f"{score:.0f}")
        
        color = config.get_quality_color(score)
        self._quality_score_label.setStyleSheet(f"color: {color};")
        
        if score >= 90:
            status = "Excellent data quality!"
        elif score >= 75:
            status = "Good data quality"
        elif score >= 60:
            status = "Fair data quality - some fixes recommended"
        else:
            status = "Poor data quality - fixes required"
        
        self._quality_status_label.setText(status)
        
        issues = quality.get("issues", [])
        if issues:
            text = "\n".join([f"• {i}" for i in issues])
            self._issues_label.setText(text)
            self._issues_frame.setVisible(True)
            self._view_abnormal_btn.setEnabled(True)
        else:
            self._issues_frame.setVisible(False)
            self._view_abnormal_btn.setEnabled(False)
        
        metrics = quality.get("metrics", {})
        parts: List[str] = []
        for key, info in metrics.items():
            if isinstance(info, dict) and "value" in info:
                parts.append(f"{key.replace('_', ' ')}: {info['value']:.1f}%")
        
        self._quality_details_label.setText(" | ".join(parts))
        
        self._session.update_state(data_quality_score=score)
    
    def _view_abnormal_data(self) -> None:
        # open abnormal data dialog with fixes
        if self._processor.processed_data is None:
            return
        
        dialog = AbnormalDataDialog(
            self._processor.processed_data,
            self._processor.column_mapping,
            self._current_quality,
            self,
            processor=self._processor
        )
        dialog.exec_()
        
        # recalc after dialog to reflect changes
        self._calculate_quality()
        self._update_statistics()
        
        if self._processor.processed_data is not None:
            preview_rows = min(1000, len(self._processor.processed_data))
            self._data_table.set_data(self._processor.processed_data.head(preview_rows))
            self._displayed_rows_label.setText(f"{preview_rows:,}")
            self._session.set_data(self._processor.processed_data)
    
    # ---------- CLASSIFICATION ----------
    
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
        
        self._session.update_state(data_cleaned=True)
        self._proceed_btn.setEnabled(True)
    
    # ---------- FLAGGED ----------
    
    def add_flagged_sku(self, sku: str) -> None:
        # add flagged sku
        self._flagged_skus.add(sku)
        self._update_flagged_display()
    
    def _update_flagged_display(self) -> None:
        # flagged label update
        count = len(self._flagged_skus)
        if count > 0:
            self._flagged_label.setText(
                f"⚠ {count} item(s) flagged for review - click to view"
            )
        else:
            self._flagged_label.setText("")
    
    def _show_flagged_items(self) -> None:
        # show flagged items
        if not self._flagged_skus:
            return
        
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Flagged Items")
        dialog.setText(
            f"The following {len(self._flagged_skus)} item(s) are flagged for review:"
        )
        detail = "\n".join([f"• {s}" for s in sorted(self._flagged_skus)])
        dialog.setDetailedText(detail)
        dialog.setIcon(QMessageBox.Information)
        dialog.setStandardButtons(QMessageBox.Ok)
        dialog.exec_()
    
    def get_flagged_skus(self) -> set:
        # return flagged set
        return self._flagged_skus.copy()
    
    # ---------- PUBLIC ----------
    
    def get_processor(self) -> DataProcessor:
        # expose processor
        return self._processor
    
    def get_classification(self) -> Dict[str, List[str]]:
        # expose classification
        return self._processor.classify_skus()