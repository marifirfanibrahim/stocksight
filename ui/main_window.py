"""
main window module
primary application window
manages tabs and navigation
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QStatusBar, QMenuBar, QMenu, QAction,
    QMessageBox, QLabel, QProgressBar, QToolBar
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon, QKeySequence
from typing import Optional

import config
from ui.models.session_model import SessionModel
from ui.tabs.data_tab import DataTab
from ui.tabs.explore_tab import ExploreTab
from ui.tabs.features_tab import FeaturesTab
from ui.tabs.forecast_tab import ForecastTab
from ui.dialogs.about_dialog import AboutDialog
from utils.memory_manager import MemoryManager


# ============================================================================
#                            MAIN WINDOW
# ============================================================================

class MainWindow(QMainWindow):
    # main application window
    
    def __init__(self):
        # initialize main window
        super().__init__()
        
        self._session = SessionModel()
        self._memory_manager = MemoryManager()
        
        self._setup_window()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_tabs()
        self._setup_statusbar()
        self._connect_signals()
        
        # start memory monitor
        self._start_memory_monitor()
    
    # ---------- WINDOW SETUP ----------
    
    def _setup_window(self) -> None:
        # setup main window properties
        self.setWindowTitle(f"{config.APP_NAME} v{config.APP_VERSION}")
        self.setMinimumSize(config.WINDOW_MIN_WIDTH, config.WINDOW_MIN_HEIGHT)
        self.resize(config.WINDOW_DEFAULT_WIDTH, config.WINDOW_DEFAULT_HEIGHT)
        
        # center on screen
        screen = self.screen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    # ---------- MENU SETUP ----------
    
    def _setup_menu(self) -> None:
        # setup menu bar
        menubar = self.menuBar()
        
        # file menu
        file_menu = menubar.addMenu("&File")
        
        open_action = QAction("&Open Data...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        export_menu = file_menu.addMenu("&Export")
        
        export_csv_action = QAction("Export to &CSV", self)
        export_csv_action.triggered.connect(self._on_export_csv)
        export_menu.addAction(export_csv_action)
        
        export_excel_action = QAction("Export to &Excel", self)
        export_excel_action.triggered.connect(self._on_export_excel)
        export_menu.addAction(export_excel_action)
        
        export_ppt_action = QAction("Export to &PowerPoint", self)
        export_ppt_action.triggered.connect(self._on_export_ppt)
        export_menu.addAction(export_ppt_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        reset_action = QAction("&Reset Session", self)
        reset_action.triggered.connect(self._on_reset_session)
        edit_menu.addAction(reset_action)
        
        # view menu
        view_menu = menubar.addMenu("&View")
        
        for i, name in config.TAB_NAMES.items():
            action = QAction(f"&{i+1}. {name}", self)
            action.setShortcut(f"Ctrl+{i+1}")
            action.setData(i)
            action.triggered.connect(self._on_switch_tab)
            view_menu.addAction(action)
        
        # help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    # ---------- TOOLBAR SETUP ----------
    
    def _setup_toolbar(self) -> None:
        # setup toolbar
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # workflow step indicators
        self._step_labels = []
        
        steps = [
            ("1", "Data Health", "Load and clean your data"),
            ("2", "Patterns", "Discover item patterns"),
            ("3", "Features", "Create smart features"),
            ("4", "Forecast", "Generate forecasts")
        ]
        
        for i, (num, name, tooltip) in enumerate(steps):
            # step container
            step_widget = QWidget()
            step_layout = QHBoxLayout(step_widget)
            step_layout.setContentsMargins(10, 2, 10, 2)
            step_layout.setSpacing(5)
            
            # step number
            num_label = QLabel(num)
            num_label.setFixedSize(24, 24)
            num_label.setAlignment(Qt.AlignCenter)
            num_label.setStyleSheet("""
                QLabel {
                    background-color: #ddd;
                    color: #666;
                    border-radius: 12px;
                    font-weight: bold;
                }
            """)
            step_layout.addWidget(num_label)
            
            # step name
            name_label = QLabel(name)
            name_label.setStyleSheet("color: #666;")
            step_layout.addWidget(name_label)
            
            step_widget.setToolTip(tooltip)
            
            self._step_labels.append((num_label, name_label))
            
            toolbar.addWidget(step_widget)
            
            # arrow between steps
            if i < len(steps) - 1:
                arrow = QLabel("→")
                arrow.setStyleSheet("color: #ccc; font-size: 16px;")
                toolbar.addWidget(arrow)
        
        toolbar.addSeparator()
        
        # spacer
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().horizontalPolicy(), spacer.sizePolicy().verticalPolicy())
        spacer.setMinimumWidth(50)
        toolbar.addWidget(spacer)
        
        # session info
        self._session_info_label = QLabel("No data loaded")
        self._session_info_label.setStyleSheet("color: gray;")
        toolbar.addWidget(self._session_info_label)
    
    # ---------- TABS SETUP ----------
    
    def _setup_tabs(self) -> None:
        # setup main tab widget
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        
        # create tabs
        self._data_tab = DataTab(self._session)
        self._explore_tab = ExploreTab(self._session)
        self._features_tab = FeaturesTab(self._session)
        self._forecast_tab = ForecastTab(self._session)
        
        # add tabs
        self._tabs.addTab(self._data_tab, "1. Data Health")
        self._tabs.addTab(self._explore_tab, "2. Pattern Discovery")
        self._tabs.addTab(self._features_tab, "3. Feature Engineering")
        self._tabs.addTab(self._forecast_tab, "4. Forecast Factory")
        
        # disable tabs until data is loaded
        for i in range(1, 4):
            self._tabs.setTabEnabled(i, False)
        
        self.setCentralWidget(self._tabs)
    
    # ---------- STATUS BAR SETUP ----------
    
    def _setup_statusbar(self) -> None:
        # setup status bar
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        
        # status message
        self._status_message = QLabel("Ready")
        self._statusbar.addWidget(self._status_message, stretch=1)
        
        # memory indicator
        self._memory_label = QLabel("Memory: --")
        self._memory_label.setStyleSheet("color: gray;")
        self._statusbar.addPermanentWidget(self._memory_label)
        
        # progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumWidth(150)
        self._progress_bar.setVisible(False)
        self._statusbar.addPermanentWidget(self._progress_bar)
    
    # ---------- SIGNAL CONNECTIONS ----------
    
    def _connect_signals(self) -> None:
        # connect tab signals
        
        # data tab signals
        self._data_tab.data_loaded.connect(self._on_data_loaded)
        self._data_tab.data_processed.connect(self._on_data_processed)
        self._data_tab.proceed_requested.connect(lambda: self._switch_to_tab(1))
        
        # explore tab signals
        self._explore_tab.clusters_created.connect(self._on_clusters_created)
        self._explore_tab.proceed_requested.connect(lambda: self._switch_to_tab(2))
        self._explore_tab.navigate_to_data.connect(self._on_navigate_to_data)
        
        # features tab signals
        self._features_tab.features_created.connect(self._on_features_created)
        self._features_tab.proceed_requested.connect(lambda: self._switch_to_tab(3))
        
        # forecast tab signals
        self._forecast_tab.forecasts_generated.connect(self._on_forecasts_generated)
        
        # session signals
        self._session.state_changed.connect(self._on_session_changed)
    
    # ---------- MEMORY MONITORING ----------
    
    def _start_memory_monitor(self) -> None:
        # start memory monitoring timer
        self._memory_timer = QTimer(self)
        self._memory_timer.timeout.connect(self._update_memory_display)
        self._memory_timer.start(5000)  # update every 5 seconds
    
    def _update_memory_display(self) -> None:
        # update memory usage display
        info = self._memory_manager.get_memory_info()
        
        rss = info.get("rss_mb", 0)
        pct = info.get("percent", 0)
        
        self._memory_label.setText(f"Memory: {rss:.0f} MB ({pct:.1f}%)")
        
        # color based on usage
        if pct > 80:
            self._memory_label.setStyleSheet("color: red;")
        elif pct > 60:
            self._memory_label.setStyleSheet("color: orange;")
        else:
            self._memory_label.setStyleSheet("color: gray;")
    
    # ---------- EVENT HANDLERS ----------
    
    def _on_tab_changed(self, index: int) -> None:
        # handle tab change
        self._update_step_indicators(index)
    
    def _on_data_loaded(self, summary: dict) -> None:
        # handle data loaded
        self._update_session_info()
        self._set_status("Data loaded successfully")
    
    def _on_data_processed(self) -> None:
        # handle data processed
        # enable explore tab
        self._tabs.setTabEnabled(1, True)
        
        # pass processor to other tabs
        processor = self._data_tab.get_processor()
        self._explore_tab.set_processor(processor)
        self._features_tab.set_processor(processor)
        self._forecast_tab.set_processor(processor)
        
        self._update_step_indicators(0, completed=True)
        self._update_session_info()
        self._set_status("Data processed - ready for pattern discovery")
    
    def _on_clusters_created(self, clusters: dict) -> None:
        # handle clusters created
        # enable features tab
        self._tabs.setTabEnabled(2, True)
        
        # pass clustering to features tab
        clustering = self._explore_tab.get_clustering()
        self._features_tab.set_clustering(clustering)
        
        self._update_step_indicators(1, completed=True)
        self._set_status(f"Created {len(clusters):,} cluster assignments")
    
    def _on_features_created(self, features: dict) -> None:
        # handle features created
        # enable forecast tab
        self._tabs.setTabEnabled(3, True)
        
        self._update_step_indicators(2, completed=True)
        self._set_status("Features created - ready for forecasting")
    
    def _on_forecasts_generated(self, forecasts: dict) -> None:
        # handle forecasts generated
        self._update_step_indicators(3, completed=True)
        self._set_status(f"Generated forecasts for {len(forecasts):,} items")
    
    def _on_session_changed(self, property_name: str) -> None:
        # handle session state change
        self._update_session_info()
    
    def _on_navigate_to_data(self, sku: str) -> None:
        # handle navigation to data tab for correction
        self._data_tab.add_flagged_sku(sku)
        # don't switch tab automatically - user may want to continue reviewing
    
    # ---------- UI UPDATES ----------
    
    def _update_step_indicators(self, current_index: int, completed: bool = False) -> None:
        # update workflow step indicators
        for i, (num_label, name_label) in enumerate(self._step_labels):
            if i < current_index or (i == current_index and completed):
                # completed step
                num_label.setStyleSheet("""
                    QLabel {
                        background-color: #28A745;
                        color: white;
                        border-radius: 12px;
                        font-weight: bold;
                    }
                """)
                name_label.setStyleSheet("color: #28A745; font-weight: bold;")
            elif i == current_index:
                # current step
                num_label.setStyleSheet("""
                    QLabel {
                        background-color: #2E86AB;
                        color: white;
                        border-radius: 12px;
                        font-weight: bold;
                    }
                """)
                name_label.setStyleSheet("color: #2E86AB; font-weight: bold;")
            else:
                # future step
                num_label.setStyleSheet("""
                    QLabel {
                        background-color: #ddd;
                        color: #666;
                        border-radius: 12px;
                        font-weight: bold;
                    }
                """)
                name_label.setStyleSheet("color: #666;")
    
    def _update_session_info(self) -> None:
        # update session info display
        state = self._session.state
        
        if not state.file_loaded:
            self._session_info_label.setText("No data loaded")
            return
        
        parts = []
        
        if state.total_skus > 0:
            parts.append(f"{state.total_skus:,} items")
        
        if state.total_rows > 0:
            parts.append(f"{state.total_rows:,} rows")
        
        if state.data_quality_score > 0:
            parts.append(f"Quality: {state.data_quality_score:.0f}%")
        
        self._session_info_label.setText(" | ".join(parts))
        self._session_info_label.setStyleSheet("color: #333;")
    
    def _set_status(self, message: str) -> None:
        # set status bar message
        self._status_message.setText(message)
    
    def _switch_to_tab(self, index: int) -> None:
        # switch to specific tab
        if self._tabs.isTabEnabled(index):
            self._tabs.setCurrentIndex(index)
    
    # ---------- MENU ACTIONS ----------
    
    def _on_open_file(self) -> None:
        # open file action
        self._switch_to_tab(0)
        self._data_tab._browse_file()
    
    def _on_export_csv(self) -> None:
        # export csv action
        self._forecast_tab._export_csv()
    
    def _on_export_excel(self) -> None:
        # export excel action
        self._forecast_tab._export_excel()
    
    def _on_export_ppt(self) -> None:
        # export ppt action
        self._forecast_tab._export_ppt()
    
    def _on_reset_session(self) -> None:
        # reset session action
        reply = QMessageBox.question(
            self,
            "Reset Session",
            "Are you sure you want to reset the session?\nAll unsaved work will be lost.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._session.reset()
            
            # reset tabs
            for i in range(1, 4):
                self._tabs.setTabEnabled(i, False)
            
            self._tabs.setCurrentIndex(0)
            self._update_step_indicators(0)
            self._update_session_info()
            self._set_status("Session reset")
    
    def _on_switch_tab(self) -> None:
        # switch tab from menu
        action = self.sender()
        index = action.data()
        self._switch_to_tab(index)
    
    def _show_about(self) -> None:
        # show about dialog
        dialog = AboutDialog(self)
        dialog.exec_()
    
    # ---------- WINDOW EVENTS ----------
    
    def closeEvent(self, event) -> None:
        # handle window close
        # check for unsaved work
        if self._session.state.forecasts_generated:
            reply = QMessageBox.question(
                self,
                "Exit Application",
                "You have generated forecasts.\nDo you want to exit without exporting?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
        
        # cleanup
        self._memory_manager.force_cleanup()
        
        event.accept()