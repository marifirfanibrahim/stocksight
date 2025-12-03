"""
main window for stocksight
pyqt6 tabbed interface with menu bar
"""


# ================ IMPORTS ================

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QStatusBar, QProgressBar, QLabel,
    QMessageBox, QFileDialog, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QAction, QIcon

from config import WindowConfig, Paths
from core.state import STATE, PipelineStage
from core.pipeline import PIPELINE
from core.alerts import ALERTS
from core.bookmarks import BOOKMARKS

from ui.menu_bar import MenuBar
from ui.tab_data_quality import DataQualityTab
from ui.tab_exploration import ExplorationTab
from ui.tab_features import FeaturesTab
from ui.tab_forecasting import ForecastingTab


# ================ MAIN WINDOW ================

class MainWindow(QMainWindow):
    """
    main application window
    """
    
    # signals
    status_updated = pyqtSignal(str, bool)
    progress_updated = pyqtSignal(int, str)
    
    def __init__(self):
        super().__init__()
        
        # ---------- WINDOW SETUP ----------
        self.setWindowTitle(WindowConfig.TITLE)
        self.setMinimumSize(WindowConfig.MIN_WIDTH, WindowConfig.MIN_HEIGHT)
        self.resize(WindowConfig.WIDTH, WindowConfig.HEIGHT)
        
        # ---------- STATE ----------
        self._dark_mode = WindowConfig.DARK_MODE
        
        # ---------- CREATE UI ----------
        self._create_menu_bar()
        self._create_central_widget()
        self._create_status_bar()
        
        # ---------- APPLY THEME ----------
        self._apply_theme()
        
        # ---------- CONNECT SIGNALS ----------
        self._connect_signals()
        
        # ---------- SETUP CALLBACKS ----------
        self._setup_pipeline_callbacks()
        
        # ---------- INITIAL STATE ----------
        self._update_ui_state()
    
    # ================ UI CREATION ================
    
    def _create_menu_bar(self):
        """
        create menu bar
        """
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)
        
        # connect menu actions
        self.menu_bar.file_open.triggered.connect(self._on_file_open)
        self.menu_bar.file_save.triggered.connect(self._on_file_save)
        self.menu_bar.file_export.triggered.connect(self._on_file_export)
        self.menu_bar.file_exit.triggered.connect(self.close)
        
        self.menu_bar.view_dark_mode.triggered.connect(self._toggle_theme)
        self.menu_bar.view_refresh.triggered.connect(self._refresh_current_tab)
        
        self.menu_bar.bookmarks_manage.triggered.connect(self._show_bookmarks)
        self.menu_bar.alerts_view.triggered.connect(self._show_alerts)
        self.menu_bar.settings_open.triggered.connect(self._show_settings)
    
    def _create_central_widget(self):
        """
        create central widget with tabs
        """
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # ---------- PIPELINE INDICATOR ----------
        self.pipeline_widget = PipelineIndicator()
        layout.addWidget(self.pipeline_widget)
        
        # ---------- TAB WIDGET ----------
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        layout.addWidget(self.tab_widget)
        
        # ---------- CREATE TABS ----------
        self.tab_data_quality = DataQualityTab(self)
        self.tab_exploration = ExplorationTab(self)
        self.tab_features = FeaturesTab(self)
        self.tab_forecasting = ForecastingTab(self)
        
        self.tab_widget.addTab(self.tab_data_quality, "Data Quality")
        self.tab_widget.addTab(self.tab_exploration, "Exploration")
        self.tab_widget.addTab(self.tab_features, "Features")
        self.tab_widget.addTab(self.tab_forecasting, "Forecasting")
        
        # connect tab changed
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
    
    def _create_status_bar(self):
        """
        create status bar
        """
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # status label
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label, 1)
        
        # progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # alert indicator
        self.alert_label = QLabel()
        self.alert_label.setStyleSheet("color: #FF9800; font-weight: bold;")
        self.status_bar.addPermanentWidget(self.alert_label)
        self._update_alert_indicator()
    
    # ================ THEME ================
    
    def _apply_theme(self):
        """
        apply dark or light theme
        """
        if self._dark_mode:
            self._apply_dark_theme()
        else:
            self._apply_light_theme()
    
    def _apply_dark_theme(self):
        """
        apply dark theme stylesheet
        """
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #333333;
                background-color: #252525;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
            }
            QTabBar::tab:hover:!selected {
                background-color: #3d3d3d;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton:pressed {
                background-color: #006cbd;
            }
            QPushButton:disabled {
                background-color: #4d4d4d;
                color: #808080;
            }
            QPushButton[secondary="true"] {
                background-color: #3d3d3d;
            }
            QPushButton[secondary="true"]:hover {
                background-color: #4d4d4d;
            }
            QLineEdit, QTextEdit, QPlainTextEdit {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px;
                color: #ffffff;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #0078d4;
            }
            QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px;
                color: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                selection-background-color: #0078d4;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px;
                color: #ffffff;
            }
            QSlider::groove:horizontal {
                background-color: #3d3d3d;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background-color: #0078d4;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QProgressBar {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #4d4d4d;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5d5d5d;
            }
            QScrollBar:horizontal {
                background-color: #2d2d2d;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #4d4d4d;
                border-radius: 6px;
                min-width: 20px;
            }
            QTableWidget, QTreeWidget, QListWidget {
                background-color: #252525;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                gridline-color: #3d3d3d;
            }
            QTableWidget::item, QTreeWidget::item, QListWidget::item {
                padding: 6px;
            }
            QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {
                background-color: #0078d4;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 8px;
                border: none;
                border-right: 1px solid #3d3d3d;
                border-bottom: 1px solid #3d3d3d;
            }
            QGroupBox {
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #0078d4;
            }
            QMenuBar {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QMenuBar::item:selected {
                background-color: #3d3d3d;
            }
            QMenu {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
            }
            QMenu::item:selected {
                background-color: #0078d4;
            }
            QStatusBar {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QToolTip {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                padding: 4px;
            }
            QLabel[heading="true"] {
                font-size: 14px;
                font-weight: bold;
                color: #0078d4;
            }
            QFrame[card="true"] {
                background-color: #252525;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                padding: 12px;
            }
        """)
    
    def _apply_light_theme(self):
        """
        apply light theme stylesheet
        """
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QWidget {
                background-color: #f5f5f5;
                color: #1e1e1e;
            }
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #e8e8e8;
                color: #1e1e1e;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
                color: #ffffff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #d8d8d8;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton:pressed {
                background-color: #006cbd;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #808080;
            }
            QPushButton[secondary="true"] {
                background-color: #e0e0e0;
                color: #1e1e1e;
            }
            QPushButton[secondary="true"]:hover {
                background-color: #d0d0d0;
            }
            QLineEdit, QTextEdit, QPlainTextEdit {
                background-color: #ffffff;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 6px;
                color: #1e1e1e;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #0078d4;
            }
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 6px;
                color: #1e1e1e;
            }
            QTableWidget, QTreeWidget, QListWidget {
                background-color: #ffffff;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                color: #1e1e1e;
                padding: 8px;
                border: none;
                border-right: 1px solid #d0d0d0;
                border-bottom: 1px solid #d0d0d0;
            }
            QGroupBox {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                color: #0078d4;
            }
            QMenuBar {
                background-color: #f0f0f0;
                color: #1e1e1e;
            }
            QMenu {
                background-color: #ffffff;
                color: #1e1e1e;
                border: 1px solid #d0d0d0;
            }
            QMenu::item:selected {
                background-color: #0078d4;
                color: #ffffff;
            }
            QStatusBar {
                background-color: #f0f0f0;
            }
            QLabel[heading="true"] {
                font-size: 14px;
                font-weight: bold;
                color: #0078d4;
            }
            QFrame[card="true"] {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 12px;
            }
        """)
    
    def _toggle_theme(self):
        """
        toggle between dark and light theme
        """
        self._dark_mode = not self._dark_mode
        STATE.settings['dark_mode'] = self._dark_mode
        self._apply_theme()
        
        # update menu checkmark
        self.menu_bar.view_dark_mode.setChecked(self._dark_mode)
        
        # refresh tabs
        self._refresh_current_tab()
    
    # ================ SIGNALS ================
    
    def _connect_signals(self):
        """
        connect internal signals
        """
        self.status_updated.connect(self._on_status_updated)
        self.progress_updated.connect(self._on_progress_updated)
    
    def _setup_pipeline_callbacks(self):
        """
        setup pipeline progress callbacks
        """
        PIPELINE.add_progress_callback(self._on_pipeline_progress)
        PIPELINE.add_stage_callback(self._on_pipeline_stage_change)
        ALERTS.add_callback(self._on_alert_change)
    
    def _on_pipeline_progress(self, stage, progress, message):
        """
        handle pipeline progress update
        """
        self.progress_updated.emit(int(progress), message)
        self.pipeline_widget.update_progress(stage, progress)
    
    def _on_pipeline_stage_change(self, stage, status):
        """
        handle pipeline stage change
        """
        self.pipeline_widget.update_stage(stage, status)
        self._update_ui_state()
    
    def _on_alert_change(self, action, alert_id):
        """
        handle alert change
        """
        self._update_alert_indicator()
    
    # ================ SLOTS ================
    
    def _on_status_updated(self, message: str, is_error: bool):
        """
        update status bar
        """
        self.status_label.setText(message)
        
        if is_error:
            self.status_label.setStyleSheet("color: #f44336;")
        else:
            self.status_label.setStyleSheet("")
    
    def _on_progress_updated(self, value: int, message: str):
        """
        update progress bar
        """
        if value < 0:
            self.progress_bar.setVisible(False)
        else:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(value)
        
        if message:
            self.status_label.setText(message)
    
    def _on_tab_changed(self, index: int):
        """
        handle tab change
        """
        # update tab if needed
        current_tab = self.tab_widget.currentWidget()
        if hasattr(current_tab, 'on_tab_activated'):
            current_tab.on_tab_activated()
    
    def _on_file_open(self):
        """
        handle file open action
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Data File",
            str(Paths.DATA_DIR),
            "All Supported (*.csv *.xlsx *.xls);;CSV (*.csv);;Excel (*.xlsx *.xls)"
        )
        
        if file_path:
            self.tab_data_quality.load_file(file_path)
    
    def _on_file_save(self):
        """
        handle file save action
        """
        if STATE.forecast_data is not None:
            from core.data_operations import export_results
            success, message = export_results()
            self.set_status(message, not success)
        else:
            self.set_status("No data to save", True)
    
    def _on_file_export(self):
        """
        handle export action
        """
        from ui.dialogs.export_dialog import ExportDialog
        dialog = ExportDialog(self)
        dialog.exec()
    
    def _refresh_current_tab(self):
        """
        refresh current tab
        """
        current_tab = self.tab_widget.currentWidget()
        if hasattr(current_tab, 'refresh'):
            current_tab.refresh()
    
    def _show_bookmarks(self):
        """
        show bookmarks dialog
        """
        from ui.dialogs.bookmark_dialog import BookmarkDialog
        dialog = BookmarkDialog(self)
        dialog.exec()
    
    def _show_alerts(self):
        """
        show alerts panel
        """
        from ui.dialogs.alert_dialog import AlertDialog
        dialog = AlertDialog(self)
        dialog.exec()
    
    def _show_settings(self):
        """
        show settings dialog
        """
        from ui.dialogs.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        if dialog.exec():
            self._apply_theme()
    
    # ================ PUBLIC METHODS ================
    
    def set_status(self, message: str, is_error: bool = False):
        """
        set status bar message
        """
        self.status_updated.emit(message, is_error)
    
    def show_progress(self, value: int = -1, message: str = ""):
        """
        show or hide progress bar
        """
        self.progress_updated.emit(value, message)
    
    def switch_to_tab(self, index: int):
        """
        switch to specified tab
        """
        if 0 <= index < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(index)
    
    def get_dark_mode(self) -> bool:
        """
        get current theme mode
        """
        return self._dark_mode
    
    # ================ HELPERS ================
    
    def _update_ui_state(self):
        """
        update ui based on current state
        """
        has_data = STATE.clean_data is not None
        has_forecast = STATE.forecast_data is not None
        
        # update menu items
        self.menu_bar.file_save.setEnabled(has_forecast)
        self.menu_bar.file_export.setEnabled(has_data or has_forecast)
    
    def _update_alert_indicator(self):
        """
        update alert count indicator
        """
        count = ALERTS.get_count()
        
        if count > 0:
            self.alert_label.setText(f"⚠ {count} Alert{'s' if count > 1 else ''}")
            self.alert_label.setVisible(True)
        else:
            self.alert_label.setVisible(False)
    
    # ================ EVENTS ================
    
    def closeEvent(self, event):
        """
        handle window close
        """
        if STATE.is_processing:
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "A process is running. Exit anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                STATE.request_cancel()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


# ================ PIPELINE INDICATOR ================

class PipelineIndicator(QWidget):
    """
    visual pipeline progress indicator
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setFixedHeight(40)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)
        
        # stage indicators
        self.stages = {}
        stage_names = ['Data Quality', 'Exploration', 'Features', 'Forecasting']
        stage_keys = [
            PipelineStage.DATA_QUALITY,
            PipelineStage.EXPLORATION,
            PipelineStage.FEATURES,
            PipelineStage.FORECASTING
        ]
        
        for i, (key, name) in enumerate(zip(stage_keys, stage_names)):
            # stage label
            label = QLabel(name)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFixedWidth(120)
            label.setStyleSheet("""
                QLabel {
                    background-color: #3d3d3d;
                    border-radius: 4px;
                    padding: 5px;
                    font-size: 11px;
                }
            """)
            
            layout.addWidget(label)
            self.stages[key] = label
            
            # arrow between stages
            if i < len(stage_names) - 1:
                arrow = QLabel("→")
                arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
                arrow.setFixedWidth(20)
                layout.addWidget(arrow)
        
        layout.addStretch()
    
    def update_stage(self, stage: PipelineStage, status):
        """
        update stage visual state
        """
        if stage not in self.stages:
            return
        
        label = self.stages[stage]
        
        if status is None:
            # idle
            label.setStyleSheet("""
                QLabel {
                    background-color: #3d3d3d;
                    border-radius: 4px;
                    padding: 5px;
                    font-size: 11px;
                }
            """)
        elif status.is_active:
            # active
            label.setStyleSheet("""
                QLabel {
                    background-color: #0078d4;
                    border-radius: 4px;
                    padding: 5px;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)
        elif status.is_complete:
            # complete
            label.setStyleSheet("""
                QLabel {
                    background-color: #4caf50;
                    border-radius: 4px;
                    padding: 5px;
                    font-size: 11px;
                }
            """)
        elif status.error:
            # error
            label.setStyleSheet("""
                QLabel {
                    background-color: #f44336;
                    border-radius: 4px;
                    padding: 5px;
                    font-size: 11px;
                }
            """)
    
    def update_progress(self, stage: PipelineStage, progress: float):
        """
        update stage progress
        """
        pass