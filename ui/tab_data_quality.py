"""
data quality tab with ydata profiling
upload, profile, clean, configure columns
"""


# ================ IMPORTS ================

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QComboBox, QSpinBox,
    QGroupBox, QScrollArea, QFrame, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QTextEdit, QCheckBox, QMessageBox,
    QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont
from PyQt6.QtWebEngineWidgets import QWebEngineView

from pathlib import Path
import pandas as pd

from config import Paths, ProfilingConfig, CleaningConfig
from core.state import STATE
from core.profiling import PROFILER
from core.pipeline import PIPELINE, PipelineStage
from core.data_operations import (
    load_file, get_excel_sheets, configure_columns,
    get_column_suggestions, is_columns_configured
)
from utils.cleaning import (
    get_missing_summary, get_duplicate_summary, get_outlier_summary,
    get_cleaning_recommendations, impute_missing, handle_duplicates,
    handle_outliers, clean_dataframe, rollback, redo, can_rollback, can_redo,
    ImputationMethod, DuplicateMethod, OutlierMethod
)
from utils.preprocessing import get_dataframe_info, get_column_analysis


# ================ WORKER THREAD ================

class ProfilingWorker(QThread):
    """
    background worker for profiling
    """
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, df=None, minimal=False):
        super().__init__()
        self.df = df
        self.minimal = minimal
    
    def run(self):
        """
        run profiling in background
        """
        def progress_callback(value, message):
            self.progress.emit(value, message)
        
        success = PROFILER.generate_report(
            df=self.df,
            minimal=self.minimal,
            progress_callback=progress_callback
        )
        
        if success:
            self.finished.emit(True, "Profiling complete")
        else:
            self.finished.emit(False, "Profiling failed")


# ================ DATA QUALITY TAB ================

class DataQualityTab(QWidget):
    """
    data quality and profiling tab
    """
    
    data_loaded = pyqtSignal()
    columns_configured = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self._worker = None
        
        self._create_ui()
        self._connect_signals()
    
    # ================ UI CREATION ================
    
    def _create_ui(self):
        """
        create tab ui
        """
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # ---------- LEFT PANEL ----------
        left_panel = self._create_left_panel()
        
        # ---------- RIGHT PANEL ----------
        right_panel = self._create_right_panel()
        
        # ---------- SPLITTER ----------
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([350, 850])
        
        layout.addWidget(splitter)
    
    def _create_left_panel(self) -> QWidget:
        """
        create left control panel
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # ---------- DATA SECTION ----------
        data_group = QGroupBox("Data")
        data_layout = QVBoxLayout(data_group)
        
        # upload button
        self.btn_upload = QPushButton("Upload File")
        self.btn_upload.setMinimumHeight(40)
        data_layout.addWidget(self.btn_upload)
        
        # file info
        self.lbl_file_info = QLabel("No file loaded")
        self.lbl_file_info.setWordWrap(True)
        self.lbl_file_info.setStyleSheet("color: gray;")
        data_layout.addWidget(self.lbl_file_info)
        
        # data stats
        self.lbl_data_stats = QLabel("")
        self.lbl_data_stats.setWordWrap(True)
        data_layout.addWidget(self.lbl_data_stats)
        
        layout.addWidget(data_group)
        
        # ---------- COLUMN CONFIGURATION ----------
        config_group = QGroupBox("Column Configuration")
        config_layout = QVBoxLayout(config_group)
        
        # status
        self.lbl_config_status = QLabel("Upload data first")
        self.lbl_config_status.setStyleSheet("color: gray;")
        config_layout.addWidget(self.lbl_config_status)
        
        # configure button
        self.btn_configure = QPushButton("Configure Columns")
        self.btn_configure.setEnabled(False)
        config_layout.addWidget(self.btn_configure)
        
        # configured columns display
        self.lbl_configured_cols = QLabel("")
        self.lbl_configured_cols.setWordWrap(True)
        self.lbl_configured_cols.setStyleSheet("font-size: 10px;")
        config_layout.addWidget(self.lbl_configured_cols)
        
        layout.addWidget(config_group)
        
        # ---------- PROFILING SECTION ----------
        profile_group = QGroupBox("Profiling")
        profile_layout = QVBoxLayout(profile_group)
        
        # minimal mode checkbox
        self.chk_minimal = QCheckBox("Minimal Report (faster)")
        profile_layout.addWidget(self.chk_minimal)
        
        # run profiling button
        self.btn_profile = QPushButton("Generate Profile Report")
        self.btn_profile.setEnabled(False)
        profile_layout.addWidget(self.btn_profile)
        
        # progress bar
        self.progress_profile = QProgressBar()
        self.progress_profile.setVisible(False)
        profile_layout.addWidget(self.progress_profile)
        
        # progress label
        self.lbl_profile_status = QLabel("")
        self.lbl_profile_status.setStyleSheet("color: gray; font-size: 11px;")
        profile_layout.addWidget(self.lbl_profile_status)
        
        # export report button
        self.btn_export_report = QPushButton("Export Report")
        self.btn_export_report.setProperty("secondary", True)
        self.btn_export_report.setEnabled(False)
        profile_layout.addWidget(self.btn_export_report)
        
        layout.addWidget(profile_group)
        
        # ---------- CLEANING SECTION ----------
        clean_group = QGroupBox("Cleaning")
        clean_layout = QVBoxLayout(clean_group)
        
        # imputation method
        imp_layout = QHBoxLayout()
        imp_layout.addWidget(QLabel("Missing Values:"))
        self.combo_imputation = QComboBox()
        self.combo_imputation.addItems([
            'Forward Fill', 'Backward Fill', 'Mean', 'Median',
            'Mode', 'Interpolate', 'Zero', 'Drop'
        ])
        imp_layout.addWidget(self.combo_imputation)
        clean_layout.addLayout(imp_layout)
        
        # duplicate method
        dup_layout = QHBoxLayout()
        dup_layout.addWidget(QLabel("Duplicates:"))
        self.combo_duplicates = QComboBox()
        self.combo_duplicates.addItems(['Keep Last', 'Keep First', 'Drop All'])
        dup_layout.addWidget(self.combo_duplicates)
        clean_layout.addLayout(dup_layout)
        
        # outlier method
        out_layout = QHBoxLayout()
        out_layout.addWidget(QLabel("Outliers:"))
        self.combo_outliers = QComboBox()
        self.combo_outliers.addItems(['Clip', 'Remove', 'Winsorize', 'None'])
        out_layout.addWidget(self.combo_outliers)
        clean_layout.addLayout(out_layout)
        
        # apply cleaning button
        self.btn_clean = QPushButton("Apply Cleaning")
        self.btn_clean.setEnabled(False)
        clean_layout.addWidget(self.btn_clean)
        
        # undo/redo buttons
        undo_redo_layout = QHBoxLayout()
        self.btn_undo = QPushButton("Undo")
        self.btn_undo.setProperty("secondary", True)
        self.btn_undo.setEnabled(False)
        undo_redo_layout.addWidget(self.btn_undo)
        
        self.btn_redo = QPushButton("Redo")
        self.btn_redo.setProperty("secondary", True)
        self.btn_redo.setEnabled(False)
        undo_redo_layout.addWidget(self.btn_redo)
        clean_layout.addLayout(undo_redo_layout)
        
        layout.addWidget(clean_group)
        
        # ---------- QUALITY SCORE ----------
        score_group = QGroupBox("Quality Score")
        score_layout = QVBoxLayout(score_group)
        
        self.lbl_quality_score = QLabel("--")
        self.lbl_quality_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_quality_score.setStyleSheet("font-size: 32px; font-weight: bold;")
        score_layout.addWidget(self.lbl_quality_score)
        
        self.lbl_quality_desc = QLabel("Load data to calculate")
        self.lbl_quality_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_quality_desc.setStyleSheet("color: gray;")
        score_layout.addWidget(self.lbl_quality_desc)
        
        layout.addWidget(score_group)
        
        layout.addStretch()
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """
        create right content panel
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # ---------- STACKED WIDGET ----------
        self.stack = QStackedWidget()
        
        # placeholder page
        placeholder = self._create_placeholder_page()
        self.stack.addWidget(placeholder)
        
        # summary page
        summary_page = self._create_summary_page()
        self.stack.addWidget(summary_page)
        
        # report page
        report_page = self._create_report_page()
        self.stack.addWidget(report_page)
        
        layout.addWidget(self.stack)
        
        return panel
    
    def _create_placeholder_page(self) -> QWidget:
        """
        create placeholder page
        """
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl = QLabel("Upload a data file to begin")
        lbl.setStyleSheet("font-size: 18px; color: gray;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)
        
        return page
    
    def _create_summary_page(self) -> QWidget:
        """
        create summary cards page
        """
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        self.summary_layout = QVBoxLayout(scroll_content)
        self.summary_layout.setSpacing(10)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        return page
    
    def _create_report_page(self) -> QWidget:
        """
        create profiling report page
        """
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # web view for html report
        try:
            self.report_view = QWebEngineView()
            layout.addWidget(self.report_view)
        except Exception:
            # fallback if web engine not available
            self.report_view = QTextEdit()
            self.report_view.setReadOnly(True)
            layout.addWidget(self.report_view)
        
        return page
    
    # ================ SIGNALS ================
    
    def _connect_signals(self):
        """
        connect widget signals
        """
        self.btn_upload.clicked.connect(self._on_upload_clicked)
        self.btn_configure.clicked.connect(self._on_configure_clicked)
        self.btn_profile.clicked.connect(self._on_profile_clicked)
        self.btn_export_report.clicked.connect(self._on_export_report)
        self.btn_clean.clicked.connect(self._on_clean_clicked)
        self.btn_undo.clicked.connect(self._on_undo)
        self.btn_redo.clicked.connect(self._on_redo)
    
    # ================ SLOTS ================
    
    def _on_upload_clicked(self):
        """
        handle upload button click
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Data File",
            str(Paths.DATA_DIR),
            "All Supported (*.csv *.xlsx *.xls);;CSV (*.csv);;Excel (*.xlsx *.xls)"
        )
        
        if file_path:
            self.load_file(file_path)
    
    def _on_configure_clicked(self):
        """
        handle configure columns button
        """
        if STATE.raw_data is None:
            return
        
        from ui.dialogs.sheet_dialog import ColumnMapperDialog
        
        dialog = ColumnMapperDialog(self, STATE.raw_data)
        
        if dialog.exec():
            # get mapping from dialog
            date_col = dialog.combo_date.currentText()
            sku_col = dialog.combo_sku.currentText()
            qty_col = dialog.combo_qty.currentText()
            additional = dialog.additional_columns
            
            # apply configuration
            success, message = configure_columns(date_col, sku_col, qty_col, additional)
            
            if success:
                self._on_columns_configured()
                if self.main_window:
                    self.main_window.set_status(message)
            else:
                QMessageBox.warning(self, "Configuration Error", message)
                if self.main_window:
                    self.main_window.set_status(message, True)
    
    def _on_columns_configured(self):
        """
        handle successful column configuration
        """
        # update status
        self.lbl_config_status.setText("✓ Columns configured")
        self.lbl_config_status.setStyleSheet("color: #4caf50;")
        
        # show mapping
        mapping = STATE.column_mapping
        cols_text = f"Date: {mapping.get('date', '?')}\n"
        cols_text += f"SKU: {mapping.get('sku', '?')}\n"
        cols_text += f"Quantity: {mapping.get('quantity', '?')}"
        if STATE.additional_columns:
            cols_text += f"\n+{len(STATE.additional_columns)} additional"
        self.lbl_configured_cols.setText(cols_text)
        
        # update stats with clean data
        self._update_data_display()
        
        # emit signal
        self.columns_configured.emit()
    
    def _on_profile_clicked(self):
        """
        handle profile button click
        """
        # profile raw data (before column configuration)
        df_to_profile = STATE.raw_data
        
        if df_to_profile is None:
            return
        
        # disable button
        self.btn_profile.setEnabled(False)
        self.progress_profile.setVisible(True)
        self.progress_profile.setValue(0)
        self.lbl_profile_status.setText("Starting profiling...")
        
        # start worker
        self._worker = ProfilingWorker(
            df=df_to_profile,
            minimal=self.chk_minimal.isChecked()
        )
        self._worker.progress.connect(self._on_profile_progress)
        self._worker.finished.connect(self._on_profile_finished)
        self._worker.start()
    
    def _on_profile_progress(self, value: int, message: str):
        """
        handle profiling progress
        """
        self.progress_profile.setValue(value)
        self.lbl_profile_status.setText(message)
    
    def _on_profile_finished(self, success: bool, message: str):
        """
        handle profiling complete
        """
        self.btn_profile.setEnabled(True)
        self.progress_profile.setVisible(False)
        self.lbl_profile_status.setText(message)
        
        if success:
            self._display_profile_report()
            self.btn_export_report.setEnabled(True)
            self._update_quality_score()
            
            if self.main_window:
                self.main_window.set_status("Profiling complete")
        else:
            if self.main_window:
                self.main_window.set_status("Profiling failed", True)
    
    def _on_export_report(self):
        """
        export profile report
        """
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Profile Report",
            str(Paths.PROFILES_DIR / "profile_report.html"),
            "HTML (*.html)"
        )
        
        if file_path:
            path = PROFILER.export_html(Path(file_path))
            if path:
                if self.main_window:
                    self.main_window.set_status(f"Report exported: {path.name}")
    
    def _on_clean_clicked(self):
        """
        handle clean button click
        """
        # clean raw data
        if STATE.raw_data is None:
            return
        
        # get selected methods
        imp_method = self._get_imputation_method()
        dup_method = self._get_duplicate_method()
        out_method = self._get_outlier_method()
        
        try:
            # apply cleaning to raw data
            STATE.raw_data = clean_dataframe(
                STATE.raw_data,
                imputation_method=imp_method,
                duplicate_method=dup_method,
                outlier_method=out_method,
                save_state=True
            )
            
            # if columns were configured, re-apply configuration
            if is_columns_configured() and STATE.column_mapping:
                configure_columns(
                    STATE.column_mapping['date'],
                    STATE.column_mapping['sku'],
                    STATE.column_mapping['quantity'],
                    STATE.additional_columns
                )
            
            self._update_data_display()
            self._update_undo_redo_buttons()
            
            if self.main_window:
                self.main_window.set_status("Cleaning applied")
                
        except Exception as e:
            if self.main_window:
                self.main_window.set_status(f"Cleaning error: {e}", True)
    
    def _on_undo(self):
        """
        handle undo
        """
        if rollback(1):
            self._update_data_display()
            self._update_undo_redo_buttons()
            if self.main_window:
                self.main_window.set_status("Undo successful")
    
    def _on_redo(self):
        """
        handle redo
        """
        if redo(1):
            self._update_data_display()
            self._update_undo_redo_buttons()
            if self.main_window:
                self.main_window.set_status("Redo successful")
    
    # ================ FILE LOADING ================
    
    def load_file(self, file_path: str):
        """
        load data file
        """
        path = Path(file_path)
        
        if self.main_window:
            self.main_window.set_status(f"Loading: {path.name}...")
            self.main_window.show_progress(10, "Loading file...")
        
        try:
            ext = path.suffix.lower()
            
            # check for multiple sheets
            if ext in ['.xlsx', '.xls']:
                sheets = get_excel_sheets(file_path)
                
                if len(sheets) > 1:
                    from ui.dialogs.sheet_dialog import SheetSelectionDialog
                    dialog = SheetSelectionDialog(self, sheets)
                    if dialog.exec():
                        sheet = dialog.selected_sheet
                        success, message, info = load_file(file_path, sheet)
                    else:
                        if self.main_window:
                            self.main_window.show_progress(-1)
                            self.main_window.set_status("Loading cancelled")
                        return
                else:
                    success, message, info = load_file(file_path)
            else:
                success, message, info = load_file(file_path)
            
            if success:
                self._on_data_loaded(path, info)
                if self.main_window:
                    self.main_window.set_status(message)
            else:
                if self.main_window:
                    self.main_window.set_status(message, True)
                    
        except Exception as e:
            if self.main_window:
                self.main_window.set_status(f"Load error: {e}", True)
        
        finally:
            if self.main_window:
                self.main_window.show_progress(-1)
    
    def _on_data_loaded(self, path: Path, info: Dict):
        """
        handle successful data load
        """
        # update file info
        self.lbl_file_info.setText(f"File: {path.name}")
        
        # update data stats
        stats = f"Rows: {info['rows']:,}\n"
        stats += f"Columns: {info['columns']}"
        self.lbl_data_stats.setText(stats)
        
        # update configuration status
        suggestions = info.get('suggestions', {})
        if suggestions.get('date') and suggestions.get('sku') and suggestions.get('quantity'):
            self.lbl_config_status.setText("Columns detected - click to configure")
            self.lbl_config_status.setStyleSheet("color: #ff9800;")
        else:
            self.lbl_config_status.setText("Please configure columns")
            self.lbl_config_status.setStyleSheet("color: #ff9800;")
        
        # enable buttons
        self.btn_configure.setEnabled(True)
        self.btn_profile.setEnabled(True)
        self.btn_clean.setEnabled(True)
        
        # show summary page
        self._build_summary_cards()
        self.stack.setCurrentIndex(1)
        
        # emit signal
        self.data_loaded.emit()
    
    # ================ DISPLAY ================
    
    def _update_data_display(self):
        """
        update data statistics display
        """
        if STATE.raw_data is None:
            self.lbl_data_stats.setText("")
            return
        
        df = STATE.raw_data
        
        stats = f"Rows: {len(df):,}\n"
        stats += f"Columns: {len(df.columns)}"
        
        if is_columns_configured() and STATE.clean_data is not None:
            stats += f"\nSKUs: {len(STATE.sku_list)}"
        
        self.lbl_data_stats.setText(stats)
        
        # update summary cards
        if self.stack.currentIndex() == 1:
            self._build_summary_cards()
    
    def _build_summary_cards(self):
        """
        build summary cards
        """
        # clear existing
        while self.summary_layout.count():
            child = self.summary_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if STATE.raw_data is None:
            return
        
        df = STATE.raw_data
        
        # ---------- OVERVIEW CARD ----------
        overview_card = self._create_card("Overview")
        overview_layout = overview_card.layout()
        
        overview_layout.addWidget(QLabel(f"Total Rows: {len(df):,}"))
        overview_layout.addWidget(QLabel(f"Total Columns: {len(df.columns)}"))
        overview_layout.addWidget(QLabel(f"Columns: {', '.join(df.columns[:5])}{'...' if len(df.columns) > 5 else ''}"))
        
        self.summary_layout.addWidget(overview_card)
        
        # ---------- COLUMN SUGGESTIONS CARD ----------
        suggestions = get_column_suggestions()
        suggest_card = self._create_card("Column Suggestions")
        suggest_layout = suggest_card.layout()
        
        for field, col in suggestions.items():
            if col:
                suggest_layout.addWidget(QLabel(f"{field.capitalize()}: {col}"))
            else:
                lbl = QLabel(f"{field.capitalize()}: Not detected")
                lbl.setStyleSheet("color: #ff9800;")
                suggest_layout.addWidget(lbl)
        
        self.summary_layout.addWidget(suggest_card)
        
        # ---------- MISSING VALUES CARD ----------
        missing_summary = get_missing_summary(df)
        missing_card = self._create_card("Missing Values")
        missing_layout = missing_card.layout()
        
        has_missing = False
        for col, info in missing_summary.items():
            if info['has_missing']:
                has_missing = True
                missing_layout.addWidget(
                    QLabel(f"{col}: {info['missing_count']:,} ({info['missing_pct']:.1f}%)")
                )
        
        if not has_missing:
            missing_layout.addWidget(QLabel("No missing values ✓"))
        
        self.summary_layout.addWidget(missing_card)
        
        # ---------- DUPLICATES CARD ----------
        dup_summary = get_duplicate_summary(df)
        dup_card = self._create_card("Duplicates")
        dup_layout = dup_card.layout()
        
        if dup_summary['duplicate_rows'] > 0:
            dup_layout.addWidget(
                QLabel(f"Duplicate Rows: {dup_summary['duplicate_rows']:,} ({dup_summary['duplicate_pct']:.1f}%)")
            )
        else:
            dup_layout.addWidget(QLabel("No duplicates ✓"))
        
        self.summary_layout.addWidget(dup_card)
        
        # ---------- OUTLIERS CARD ----------
        outlier_summary = get_outlier_summary(df)
        outlier_card = self._create_card("Outliers")
        outlier_layout = outlier_card.layout()
        
        has_outliers = False
        for col, info in outlier_summary.items():
            if info['outlier_pct'] > 1:
                has_outliers = True
                outlier_layout.addWidget(
                    QLabel(f"{col}: {info['outlier_count']:,} ({info['outlier_pct']:.1f}%)")
                )
        
        if not has_outliers:
            outlier_layout.addWidget(QLabel("No significant outliers ✓"))
        
        self.summary_layout.addWidget(outlier_card)
        
        # ---------- RECOMMENDATIONS CARD ----------
        recommendations = get_cleaning_recommendations(df)
        if recommendations:
            rec_card = self._create_card("Recommendations")
            rec_layout = rec_card.layout()
            
            for rec in recommendations[:5]:
                lbl = QLabel(f"• {rec['message']}")
                lbl.setWordWrap(True)
                rec_layout.addWidget(lbl)
            
            self.summary_layout.addWidget(rec_card)
        
        self.summary_layout.addStretch()
    
    def _create_card(self, title: str) -> QFrame:
        """
        create summary card
        """
        card = QFrame()
        card.setProperty("card", True)
        card.setStyleSheet("""
            QFrame[card="true"] {
                background-color: #252525;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        
        title_lbl = QLabel(title)
        title_lbl.setProperty("heading", True)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #0078d4;")
        layout.addWidget(title_lbl)
        
        return card
    
    def _display_profile_report(self):
        """
        display profile report in web view
        """
        html = PROFILER.get_html()
        
        if html:
            if isinstance(self.report_view, QWebEngineView):
                self.report_view.setHtml(html)
            else:
                self.report_view.setHtml(html)
            
            self.stack.setCurrentIndex(2)
    
    def _update_quality_score(self):
        """
        update quality score display
        """
        score = STATE.data_quality_score
        
        self.lbl_quality_score.setText(f"{score:.0f}")
        
        if score >= 80:
            self.lbl_quality_score.setStyleSheet(
                "font-size: 32px; font-weight: bold; color: #4caf50;"
            )
            self.lbl_quality_desc.setText("Good quality")
        elif score >= 60:
            self.lbl_quality_score.setStyleSheet(
                "font-size: 32px; font-weight: bold; color: #ff9800;"
            )
            self.lbl_quality_desc.setText("Needs attention")
        else:
            self.lbl_quality_score.setStyleSheet(
                "font-size: 32px; font-weight: bold; color: #f44336;"
            )
            self.lbl_quality_desc.setText("Poor quality")
    
    def _update_undo_redo_buttons(self):
        """
        update undo/redo button states
        """
        self.btn_undo.setEnabled(can_rollback())
        self.btn_redo.setEnabled(can_redo())
    
    # ================ HELPERS ================
    
    def _get_imputation_method(self) -> ImputationMethod:
        """
        get selected imputation method
        """
        text = self.combo_imputation.currentText()
        mapping = {
            'Forward Fill': ImputationMethod.FORWARD_FILL,
            'Backward Fill': ImputationMethod.BACKWARD_FILL,
            'Mean': ImputationMethod.MEAN,
            'Median': ImputationMethod.MEDIAN,
            'Mode': ImputationMethod.MODE,
            'Interpolate': ImputationMethod.INTERPOLATE,
            'Zero': ImputationMethod.ZERO,
            'Drop': ImputationMethod.DROP
        }
        return mapping.get(text, ImputationMethod.FORWARD_FILL)
    
    def _get_duplicate_method(self) -> DuplicateMethod:
        """
        get selected duplicate method
        """
        text = self.combo_duplicates.currentText()
        mapping = {
            'Keep Last': DuplicateMethod.KEEP_LAST,
            'Keep First': DuplicateMethod.KEEP_FIRST,
            'Drop All': DuplicateMethod.DROP_ALL
        }
        return mapping.get(text, DuplicateMethod.KEEP_LAST)
    
    def _get_outlier_method(self) -> OutlierMethod:
        """
        get selected outlier method
        """
        text = self.combo_outliers.currentText()
        mapping = {
            'Clip': OutlierMethod.CLIP,
            'Remove': OutlierMethod.REMOVE,
            'Winsorize': OutlierMethod.WINSORIZE,
            'None': OutlierMethod.NONE
        }
        return mapping.get(text, OutlierMethod.CLIP)
    
    # ================ PUBLIC ================
    
    def on_tab_activated(self):
        """
        called when tab is activated
        """
        pass
    
    def refresh(self):
        """
        refresh tab contents
        """
        self._update_data_display()
        self._update_undo_redo_buttons()