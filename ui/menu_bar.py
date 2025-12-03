"""
global menu bar for stocksight
file, view, bookmarks, alerts, settings
"""


# ================ IMPORTS ================

from PyQt6.QtWidgets import QMenuBar, QMenu
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtCore import Qt


# ================ MENU BAR ================

class MenuBar(QMenuBar):
    """
    application menu bar
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._create_file_menu()
        self._create_edit_menu()
        self._create_view_menu()
        self._create_bookmarks_menu()
        self._create_alerts_menu()
        self._create_tools_menu()
        self._create_help_menu()
    
    # ================ FILE MENU ================
    
    def _create_file_menu(self):
        """
        create file menu
        """
        file_menu = self.addMenu("&File")
        
        # open
        self.file_open = QAction("&Open...", self)
        self.file_open.setShortcut(QKeySequence.StandardKey.Open)
        self.file_open.setStatusTip("Open a data file")
        file_menu.addAction(self.file_open)
        
        # recent files submenu
        self.recent_menu = file_menu.addMenu("Recent Files")
        self.recent_menu.setEnabled(False)
        
        file_menu.addSeparator()
        
        # save
        self.file_save = QAction("&Save Results", self)
        self.file_save.setShortcut(QKeySequence.StandardKey.Save)
        self.file_save.setStatusTip("Save forecast results")
        self.file_save.setEnabled(False)
        file_menu.addAction(self.file_save)
        
        # export
        self.file_export = QAction("&Export...", self)
        self.file_export.setShortcut(QKeySequence("Ctrl+E"))
        self.file_export.setStatusTip("Export data and results")
        self.file_export.setEnabled(False)
        file_menu.addAction(self.file_export)
        
        file_menu.addSeparator()
        
        # load model
        self.file_load_model = QAction("Load &Model...", self)
        self.file_load_model.setStatusTip("Load a saved model")
        file_menu.addAction(self.file_load_model)
        
        # save model
        self.file_save_model = QAction("Save Model...", self)
        self.file_save_model.setStatusTip("Save trained model")
        file_menu.addAction(self.file_save_model)
        
        file_menu.addSeparator()
        
        # exit
        self.file_exit = QAction("E&xit", self)
        self.file_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self.file_exit.setStatusTip("Exit application")
        file_menu.addAction(self.file_exit)
    
    # ================ EDIT MENU ================
    
    def _create_edit_menu(self):
        """
        create edit menu
        """
        edit_menu = self.addMenu("&Edit")
        
        # undo
        self.edit_undo = QAction("&Undo", self)
        self.edit_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.edit_undo.setStatusTip("Undo last action")
        self.edit_undo.setEnabled(False)
        edit_menu.addAction(self.edit_undo)
        
        # redo
        self.edit_redo = QAction("&Redo", self)
        self.edit_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.edit_redo.setStatusTip("Redo last action")
        self.edit_redo.setEnabled(False)
        edit_menu.addAction(self.edit_redo)
        
        edit_menu.addSeparator()
        
        # clear data
        self.edit_clear_data = QAction("Clear &Data", self)
        self.edit_clear_data.setStatusTip("Clear loaded data")
        edit_menu.addAction(self.edit_clear_data)
        
        # clear results
        self.edit_clear_results = QAction("Clear &Results", self)
        self.edit_clear_results.setStatusTip("Clear forecast results")
        edit_menu.addAction(self.edit_clear_results)
    
    # ================ VIEW MENU ================
    
    def _create_view_menu(self):
        """
        create view menu
        """
        view_menu = self.addMenu("&View")
        
        # dark mode
        self.view_dark_mode = QAction("&Dark Mode", self)
        self.view_dark_mode.setCheckable(True)
        self.view_dark_mode.setChecked(True)
        self.view_dark_mode.setStatusTip("Toggle dark mode")
        view_menu.addAction(self.view_dark_mode)
        
        view_menu.addSeparator()
        
        # refresh
        self.view_refresh = QAction("&Refresh", self)
        self.view_refresh.setShortcut(QKeySequence.StandardKey.Refresh)
        self.view_refresh.setStatusTip("Refresh current view")
        view_menu.addAction(self.view_refresh)
        
        view_menu.addSeparator()
        
        # tabs
        self.view_data_quality = QAction("Data &Quality Tab", self)
        self.view_data_quality.setShortcut(QKeySequence("Ctrl+1"))
        view_menu.addAction(self.view_data_quality)
        
        self.view_exploration = QAction("&Exploration Tab", self)
        self.view_exploration.setShortcut(QKeySequence("Ctrl+2"))
        view_menu.addAction(self.view_exploration)
        
        self.view_features = QAction("&Features Tab", self)
        self.view_features.setShortcut(QKeySequence("Ctrl+3"))
        view_menu.addAction(self.view_features)
        
        self.view_forecasting = QAction("F&orecasting Tab", self)
        self.view_forecasting.setShortcut(QKeySequence("Ctrl+4"))
        view_menu.addAction(self.view_forecasting)
    
    # ================ BOOKMARKS MENU ================
    
    def _create_bookmarks_menu(self):
        """
        create bookmarks menu
        """
        bookmarks_menu = self.addMenu("&Bookmarks")
        
        # manage bookmarks
        self.bookmarks_manage = QAction("&Manage Bookmarks...", self)
        self.bookmarks_manage.setShortcut(QKeySequence("Ctrl+B"))
        self.bookmarks_manage.setStatusTip("View and manage bookmarks")
        bookmarks_menu.addAction(self.bookmarks_manage)
        
        bookmarks_menu.addSeparator()
        
        # add bookmark
        self.bookmarks_add = QAction("&Add Bookmark", self)
        self.bookmarks_add.setShortcut(QKeySequence("Ctrl+D"))
        self.bookmarks_add.setStatusTip("Bookmark current selection")
        bookmarks_menu.addAction(self.bookmarks_add)
        
        bookmarks_menu.addSeparator()
        
        # bookmark categories
        self.bookmarks_skus = bookmarks_menu.addMenu("SKU Bookmarks")
        self.bookmarks_anomalies = bookmarks_menu.addMenu("Anomaly Sets")
        self.bookmarks_forecasts = bookmarks_menu.addMenu("Forecasts")
        self.bookmarks_features = bookmarks_menu.addMenu("Feature Sets")
    
    # ================ ALERTS MENU ================
    
    def _create_alerts_menu(self):
        """
        create alerts menu
        """
        alerts_menu = self.addMenu("A&lerts")
        
        # view alerts
        self.alerts_view = QAction("&View Alerts...", self)
        self.alerts_view.setShortcut(QKeySequence("Ctrl+Shift+A"))
        self.alerts_view.setStatusTip("View all alerts")
        alerts_menu.addAction(self.alerts_view)
        
        alerts_menu.addSeparator()
        
        # dismiss all
        self.alerts_dismiss_all = QAction("&Dismiss All", self)
        self.alerts_dismiss_all.setStatusTip("Dismiss all alerts")
        alerts_menu.addAction(self.alerts_dismiss_all)
        
        alerts_menu.addSeparator()
        
        # alert types
        self.alerts_anomalies = QAction("Show &Anomaly Alerts", self)
        self.alerts_anomalies.setCheckable(True)
        self.alerts_anomalies.setChecked(True)
        alerts_menu.addAction(self.alerts_anomalies)
        
        self.alerts_quality = QAction("Show &Data Quality Alerts", self)
        self.alerts_quality.setCheckable(True)
        self.alerts_quality.setChecked(True)
        alerts_menu.addAction(self.alerts_quality)
        
        self.alerts_model = QAction("Show &Model Alerts", self)
        self.alerts_model.setCheckable(True)
        self.alerts_model.setChecked(True)
        alerts_menu.addAction(self.alerts_model)
    
    # ================ TOOLS MENU ================
    
    def _create_tools_menu(self):
        """
        create tools menu
        """
        tools_menu = self.addMenu("&Tools")
        
        # run all
        self.tools_run_pipeline = QAction("&Run Full Pipeline", self)
        self.tools_run_pipeline.setShortcut(QKeySequence("F5"))
        self.tools_run_pipeline.setStatusTip("Run complete pipeline")
        tools_menu.addAction(self.tools_run_pipeline)
        
        tools_menu.addSeparator()
        
        # compare models
        self.tools_compare_models = QAction("&Compare Models...", self)
        self.tools_compare_models.setStatusTip("Compare forecasting models")
        tools_menu.addAction(self.tools_compare_models)
        
        # diagnostics
        self.tools_diagnostics = QAction("&Diagnostics...", self)
        self.tools_diagnostics.setStatusTip("View diagnostic information")
        tools_menu.addAction(self.tools_diagnostics)
        
        tools_menu.addSeparator()
        
        # settings
        self.settings_open = QAction("&Settings...", self)
        self.settings_open.setShortcut(QKeySequence("Ctrl+,"))
        self.settings_open.setStatusTip("Open settings")
        tools_menu.addAction(self.settings_open)
    
    # ================ HELP MENU ================
    
    def _create_help_menu(self):
        """
        create help menu
        """
        help_menu = self.addMenu("&Help")
        
        # documentation
        self.help_docs = QAction("&Documentation", self)
        self.help_docs.setShortcut(QKeySequence.StandardKey.HelpContents)
        self.help_docs.setStatusTip("Open documentation")
        help_menu.addAction(self.help_docs)
        
        # keyboard shortcuts
        self.help_shortcuts = QAction("&Keyboard Shortcuts", self)
        self.help_shortcuts.setStatusTip("View keyboard shortcuts")
        help_menu.addAction(self.help_shortcuts)
        
        help_menu.addSeparator()
        
        # check updates
        self.help_updates = QAction("Check for &Updates", self)
        self.help_updates.setStatusTip("Check for updates")
        help_menu.addAction(self.help_updates)
        
        help_menu.addSeparator()
        
        # about
        self.help_about = QAction("&About Stocksight", self)
        self.help_about.setStatusTip("About Stocksight")
        help_menu.addAction(self.help_about)
    
    # ================ UPDATES ================
    
    def update_recent_files(self, files: list):
        """
        update recent files submenu
        """
        self.recent_menu.clear()
        
        if not files:
            self.recent_menu.setEnabled(False)
            return
        
        self.recent_menu.setEnabled(True)
        
        for file_path in files[:10]:
            action = QAction(file_path, self)
            action.setData(file_path)
            self.recent_menu.addAction(action)
    
    def update_bookmarks_menu(self, bookmarks: dict):
        """
        update bookmark submenus
        """
        # clear existing
        self.bookmarks_skus.clear()
        self.bookmarks_anomalies.clear()
        self.bookmarks_forecasts.clear()
        self.bookmarks_features.clear()
        
        # populate from bookmarks
        for bookmark in bookmarks.get('skus', []):
            action = QAction(bookmark['name'], self)
            action.setData(bookmark['id'])
            self.bookmarks_skus.addAction(action)
        
        for bookmark in bookmarks.get('anomalies', []):
            action = QAction(bookmark['name'], self)
            action.setData(bookmark['id'])
            self.bookmarks_anomalies.addAction(action)
        
        for bookmark in bookmarks.get('forecasts', []):
            action = QAction(bookmark['name'], self)
            action.setData(bookmark['id'])
            self.bookmarks_forecasts.addAction(action)
        
        for bookmark in bookmarks.get('features', []):
            action = QAction(bookmark['name'], self)
            action.setData(bookmark['id'])
            self.bookmarks_features.addAction(action)