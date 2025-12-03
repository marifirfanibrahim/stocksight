"""
forecasting tab with autots
training, evaluation, visualization, export
"""


# ================ IMPORTS ================

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QComboBox, QSpinBox,
    QGroupBox, QScrollArea, QFrame, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QListWidget, QListWidgetItem,
    QCheckBox, QSlider, QStackedWidget, QDoubleSpinBox,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QPixmap, QImage

import base64
from pathlib import Path

from config import AutoTSConfig, DataConfig, Paths
from core.state import STATE
from core.forecasting import FORECASTER
from core.charting import generate_forecast_chart, generate_summary_chart, generate_model_comparison_chart
from core.data_operations import export_results, get_output_directory
from core.bookmarks import BOOKMARKS
from utils.preprocessing import prepare_for_autots


# ================ WORKER THREAD ================

class ForecastWorker(QThread):
    """
    background worker for forecasting
    """
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, periods=30, granularity='Daily', speed='Fast'):
        super().__init__()
        self.periods = periods
        self.granularity = granularity
        self.speed = speed
    
    def run(self):
        """
        run forecast
        """
        def progress_callback(value, message):
            self.progress.emit(value, message)
        
        success, message = FORECASTER.run_forecast(
            forecast_periods=self.periods,
            granularity=self.granularity,
            speed=self.speed,
            progress_callback=progress_callback
        )
        
        self.finished.emit(success, message)


class CompareWorker(QThread):
    """
    background worker for model comparison
    """
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str, dict)
    
    def __init__(self, periods=30):
        super().__init__()
        self.periods = periods
    
    def run(self):
        """
        run model comparison
        """
        def progress_callback(value, message):
            self.progress.emit(value, message)
        
        try:
            results = FORECASTER.compare_models(
                forecast_periods=self.periods,
                progress_callback=progress_callback
            )
            
            if 'error' in results:
                self.finished.emit(False, results['error'], {})
            else:
                self.finished.emit(True, "Comparison complete", results)
                
        except Exception as e:
            self.finished.emit(False, str(e), {})


# ================ FORECASTING TAB ================

class ForecastingTab(QWidget):
    """
    forecasting tab
    """
    
    forecast_complete = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self._worker = None
        self._comparison_results = {}
        
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
        
        # ---------- FORECAST SETTINGS ----------
        settings_group = QGroupBox("Forecast Settings")
        settings_layout = QVBoxLayout(settings_group)
        
        # periods
        periods_layout = QHBoxLayout()
        periods_layout.addWidget(QLabel("Periods:"))
        self.spin_periods = QSpinBox()
        self.spin_periods.setRange(1, 365)
        self.spin_periods.setValue(AutoTSConfig.DEFAULT_FORECAST_DAYS)
        periods_layout.addWidget(self.spin_periods)
        settings_layout.addLayout(periods_layout)
        
        # granularity
        gran_layout = QHBoxLayout()
        gran_layout.addWidget(QLabel("Granularity:"))
        self.combo_granularity = QComboBox()
        self.combo_granularity.addItems(DataConfig.GROUP_OPTIONS)
        gran_layout.addWidget(self.combo_granularity)
        settings_layout.addLayout(gran_layout)
        
        # speed
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        self.combo_speed = QComboBox()
        self.combo_speed.addItems(['Superfast', 'Fast', 'Balanced', 'Accurate'])
        self.combo_speed.setCurrentIndex(1)
        speed_layout.addWidget(self.combo_speed)
        settings_layout.addLayout(speed_layout)
        
        # run forecast button
        self.btn_run_forecast = QPushButton("Run Forecast")
        self.btn_run_forecast.setMinimumHeight(40)
        self.btn_run_forecast.setEnabled(False)
        settings_layout.addWidget(self.btn_run_forecast)
        
        # cancel button
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setProperty("secondary", True)
        self.btn_cancel.setVisible(False)
        settings_layout.addWidget(self.btn_cancel)
        
        # progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        settings_layout.addWidget(self.progress_bar)
        
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: gray; font-size: 11px;")
        self.lbl_status.setWordWrap(True)
        settings_layout.addWidget(self.lbl_status)
        
        layout.addWidget(settings_group)
        
        # ---------- MODEL SECTION ----------
        model_group = QGroupBox("Model")
        model_layout = QVBoxLayout(model_group)
        
        # load model
        self.btn_load_model = QPushButton("Load Model")
        model_layout.addWidget(self.btn_load_model)
        
        # save model
        self.btn_save_model = QPushButton("Save Model")
        self.btn_save_model.setEnabled(False)
        model_layout.addWidget(self.btn_save_model)
        
        # model info
        self.lbl_model_info = QLabel("No model loaded")
        self.lbl_model_info.setStyleSheet("color: gray;")
        self.lbl_model_info.setWordWrap(True)
        model_layout.addWidget(self.lbl_model_info)
        
        # compare models
        self.btn_compare_models = QPushButton("Compare Models")
        self.btn_compare_models.setProperty("secondary", True)
        self.btn_compare_models.setEnabled(False)
        model_layout.addWidget(self.btn_compare_models)
        
        layout.addWidget(model_group)
        
        # ---------- METRICS SECTION ----------
        metrics_group = QGroupBox("Evaluation Metrics")
        metrics_layout = QVBoxLayout(metrics_group)
        
        # metrics table
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(2)
        self.metrics_table.setHorizontalHeaderLabels(['Metric', 'Value'])
        self.metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.metrics_table.setMaximumHeight(150)
        metrics_layout.addWidget(self.metrics_table)
        
        layout.addWidget(metrics_group)
        
        # ---------- VISUALIZATION ----------
        viz_group = QGroupBox("Visualization")
        viz_layout = QVBoxLayout(viz_group)
        
        # sku filter
        sku_layout = QHBoxLayout()
        sku_layout.addWidget(QLabel("SKU:"))
        self.combo_sku_filter = QComboBox()
        self.combo_sku_filter.addItem("All SKUs")
        sku_layout.addWidget(self.combo_sku_filter)
        viz_layout.addLayout(sku_layout)
        
        # refresh chart button
        self.btn_refresh_chart = QPushButton("Refresh Chart")
        self.btn_refresh_chart.setProperty("secondary", True)
        self.btn_refresh_chart.setEnabled(False)
        viz_layout.addWidget(self.btn_refresh_chart)
        
        # show summary button
        self.btn_show_summary = QPushButton("Show Summary")
        self.btn_show_summary.setProperty("secondary", True)
        self.btn_show_summary.setEnabled(False)
        viz_layout.addWidget(self.btn_show_summary)
        
        layout.addWidget(viz_group)
        
        # ---------- EXPORT SECTION ----------
        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout(export_group)
        
        # format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        self.combo_export_format = QComboBox()
        self.combo_export_format.addItems(['CSV', 'Excel', 'JSON'])
        format_layout.addWidget(self.combo_export_format)
        export_layout.addLayout(format_layout)
        
        # export button
        self.btn_export = QPushButton("Export Forecast")
        self.btn_export.setEnabled(False)
        export_layout.addWidget(self.btn_export)
        
        # bookmark button
        self.btn_bookmark = QPushButton("Bookmark Forecast")
        self.btn_bookmark.setProperty("secondary", True)
        self.btn_bookmark.setEnabled(False)
        export_layout.addWidget(self.btn_bookmark)
        
        layout.addWidget(export_group)
        
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
        
        # placeholder
        placeholder = self._create_placeholder()
        self.stack.addWidget(placeholder)
        
        # forecast chart
        chart_page = self._create_chart_page()
        self.stack.addWidget(chart_page)
        
        # comparison chart
        comparison_page = self._create_comparison_page()
        self.stack.addWidget(comparison_page)
        
        layout.addWidget(self.stack)
        
        return panel
    
    def _create_placeholder(self) -> QWidget:
        """
        create placeholder widget
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl = QLabel("Run forecast to see results")
        lbl.setStyleSheet("font-size: 18px; color: gray;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)
        
        return widget
    
    def _create_chart_page(self) -> QWidget:
        """
        create forecast chart page
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # scroll area for chart
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.chart_label = QLabel()
        self.chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidget(self.chart_label)
        
        layout.addWidget(scroll)
        
        return widget
    
    def _create_comparison_page(self) -> QWidget:
        """
        create model comparison page
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # comparison table
        self.comparison_table = QTableWidget()
        self.comparison_table.setColumnCount(5)
        self.comparison_table.setHorizontalHeaderLabels(['Model', 'MAE', 'RMSE', 'MAPE', 'Best Model'])
        self.comparison_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.comparison_table)
        
        # comparison chart
        self.comparison_chart_label = QLabel()
        self.comparison_chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.comparison_chart_label)
        
        return widget
    
    # ================ SIGNALS ================
    
    def _connect_signals(self):
        """
        connect widget signals
        """
        self.btn_run_forecast.clicked.connect(self._on_run_forecast)
        self.btn_cancel.clicked.connect(self._on_cancel)
        
        self.btn_load_model.clicked.connect(self._on_load_model)
        self.btn_save_model.clicked.connect(self._on_save_model)
        self.btn_compare_models.clicked.connect(self._on_compare_models)
        
        self.combo_sku_filter.currentIndexChanged.connect(self._on_sku_filter_changed)
        self.btn_refresh_chart.clicked.connect(self._on_refresh_chart)
        self.btn_show_summary.clicked.connect(self._on_show_summary)
        
        self.btn_export.clicked.connect(self._on_export)
        self.btn_bookmark.clicked.connect(self._on_bookmark)
    
    # ================ SLOTS ================
    
    def _on_run_forecast(self):
        """
        run forecast
        """
        if STATE.clean_data is None:
            return
        
        # get settings
        periods = self.spin_periods.value()
        granularity = self.combo_granularity.currentText()
        speed = self.combo_speed.currentText()
        
        # update state
        STATE.forecast_days = periods
        STATE.forecast_granularity = granularity
        STATE.forecast_speed = speed
        
        # disable button and show progress
        self.btn_run_forecast.setEnabled(False)
        self.btn_cancel.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Starting forecast...")
        
        # start worker
        self._worker = ForecastWorker(periods, granularity, speed)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.finished.connect(self._on_forecast_finished)
        self._worker.start()
    
    def _on_cancel(self):
        """
        cancel forecast
        """
        FORECASTER.cancel()
        self.lbl_status.setText("Cancelling...")
    
    def _on_worker_progress(self, value: int, message: str):
        """
        handle worker progress
        """
        self.progress_bar.setValue(value)
        self.lbl_status.setText(message)
    
    def _on_forecast_finished(self, success: bool, message: str):
        """
        handle forecast complete
        """
        self.btn_run_forecast.setEnabled(True)
        self.btn_cancel.setVisible(False)
        self.progress_bar.setVisible(False)
        self.lbl_status.setText(message)
        
        if success:
            self._update_results_display()
            self._enable_controls(True)
            
            if self.main_window:
                self.main_window.set_status(message)
            
            self.forecast_complete.emit()
        else:
            if self.main_window:
                self.main_window.set_status(message, True)
    
    def _on_load_model(self):
        """
        load saved model
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Model",
            str(Paths.MODELS_DIR),
            "Model Files (*.pkl)"
        )
        
        if file_path:
            success, message = FORECASTER.load_model(Path(file_path))
            
            if success:
                self.lbl_model_info.setText(f"Loaded: {Path(file_path).name}")
                self.btn_save_model.setEnabled(True)
                
                if self.main_window:
                    self.main_window.set_status(message)
            else:
                if self.main_window:
                    self.main_window.set_status(message, True)
    
    def _on_save_model(self):
        """
        save trained model
        """
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Model",
            str(Paths.MODELS_DIR / "model.pkl"),
            "Model Files (*.pkl)"
        )
        
        if file_path:
            path = FORECASTER.save_model(Path(file_path))
            
            if path:
                if self.main_window:
                    self.main_window.set_status(f"Model saved: {path.name}")
    
    def _on_compare_models(self):
        """
        compare different models
        """
        if STATE.clean_data is None:
            return
        
        periods = self.spin_periods.value()
        
        self.btn_compare_models.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.lbl_status.setText("Comparing models...")
        
        self._worker = CompareWorker(periods)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.finished.connect(self._on_compare_finished)
        self._worker.start()
    
    def _on_compare_finished(self, success: bool, message: str, results: dict):
        """
        handle comparison complete
        """
        self.btn_compare_models.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.lbl_status.setText(message)
        
        if success:
            self._comparison_results = results
            self._display_comparison_results()
            
            if self.main_window:
                self.main_window.set_status(message)
    
    def _on_sku_filter_changed(self, index: int):
        """
        handle sku filter change
        """
        self._on_refresh_chart()
    
    def _on_refresh_chart(self):
        """
        refresh forecast chart
        """
        if STATE.forecast_data is None:
            return
        
        sku_filter = self.combo_sku_filter.currentText()
        if sku_filter == "All SKUs":
            sku_filter = None
        
        # get historical data
        df_pivot = prepare_for_autots(STATE.clean_data, use_features=False).set_index('Date')
        
        dark_mode = self.main_window.get_dark_mode() if self.main_window else True
        
        img_base64, _ = generate_forecast_chart(
            df_pivot,
            STATE.forecast_data,
            STATE.upper_forecast,
            STATE.lower_forecast,
            STATE.forecast_granularity,
            sku_filter,
            dark_mode=dark_mode
        )
        
        if img_base64:
            self._display_chart(img_base64)
    
    def _on_show_summary(self):
        """
        show summary chart
        """
        if STATE.forecast_data is None:
            return
        
        dark_mode = self.main_window.get_dark_mode() if self.main_window else True
        
        img_base64, _ = generate_summary_chart(
            STATE.forecast_data,
            STATE.forecast_granularity,
            dark_mode=dark_mode
        )
        
        if img_base64:
            self._display_chart(img_base64)
    
    def _on_export(self):
        """
        export forecast results
        """
        success, message = export_results()
        
        if self.main_window:
            self.main_window.set_status(message, not success)
    
    def _on_bookmark(self):
        """
        bookmark forecast
        """
        if STATE.forecast_data is None:
            return
        
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        BOOKMARKS.bookmark_forecast(
            name=f"Forecast {timestamp}",
            forecast_id=timestamp
        )
        
        if self.main_window:
            self.main_window.set_status("Forecast bookmarked")
    
    # ================ DISPLAY ================
    
    def _update_results_display(self):
        """
        update results display after forecast
        """
        # update sku filter
        self.combo_sku_filter.clear()
        self.combo_sku_filter.addItem("All SKUs")
        
        if STATE.forecast_data is not None:
            for sku in STATE.forecast_data.columns:
                self.combo_sku_filter.addItem(str(sku))
        
        # update metrics
        self._update_metrics_table()
        
        # update model info
        metrics = FORECASTER.get_metrics()
        if 'best_model' in metrics:
            best = metrics['best_model'].get('name', 'Unknown')
            self.lbl_model_info.setText(f"Best Model: {best}")
        
        # refresh chart
        self._on_refresh_chart()
        self.stack.setCurrentIndex(1)
    
    def _update_metrics_table(self):
        """
        update metrics table
        """
        metrics = FORECASTER.get_metrics()
        overall = metrics.get('_overall', {}) if '_overall' in metrics else {}
        
        if not overall and 'best_model' in metrics:
            # try to get from summary
            summary = FORECASTER.get_forecast_summary()
            overall = summary.get('metrics', {}).get('_overall', {})
        
        self.metrics_table.setRowCount(4)
        
        metric_names = ['MAE', 'RMSE', 'MAPE', 'SMAPE']
        
        for row, name in enumerate(metric_names):
            self.metrics_table.setItem(row, 0, QTableWidgetItem(name))
            
            value = overall.get(name)
            if value is not None:
                self.metrics_table.setItem(row, 1, QTableWidgetItem(f"{value:.4f}"))
            else:
                self.metrics_table.setItem(row, 1, QTableWidgetItem("--"))
    
    def _display_comparison_results(self):
        """
        display model comparison results
        """
        if not self._comparison_results:
            return
        
        # populate table
        self.comparison_table.setRowCount(len(self._comparison_results))
        
        row = 0
        for model_name, result in self._comparison_results.items():
            if model_name == 'consensus':
                continue
            
            self.comparison_table.setItem(row, 0, QTableWidgetItem(model_name))
            
            metrics = result.get('metrics', {})
            self.comparison_table.setItem(row, 1, QTableWidgetItem(f"{metrics.get('MAE', 0):.4f}"))
            self.comparison_table.setItem(row, 2, QTableWidgetItem(f"{metrics.get('RMSE', 0):.4f}"))
            self.comparison_table.setItem(row, 3, QTableWidgetItem(f"{metrics.get('MAPE', 0):.2f}%"))
            self.comparison_table.setItem(row, 4, QTableWidgetItem(result.get('best_model', '--')))
            
            row += 1
        
        # generate comparison chart
        dark_mode = self.main_window.get_dark_mode() if self.main_window else True
        
        metrics_for_chart = {
            k: v.get('metrics', {}) for k, v in self._comparison_results.items()
            if k != 'consensus' and 'metrics' in v
        }
        
        img_base64 = generate_model_comparison_chart(metrics_for_chart, dark_mode=dark_mode)
        
        if img_base64:
            try:
                img_data = base64.b64decode(img_base64)
                img = QImage()
                img.loadFromData(img_data)
                pixmap = QPixmap.fromImage(img)
                self.comparison_chart_label.setPixmap(pixmap)
            except Exception as e:
                print(f"chart display error: {e}")
        
        self.stack.setCurrentIndex(2)
    
    def _display_chart(self, img_base64: str):
        """
        display chart from base64
        """
        try:
            img_data = base64.b64decode(img_base64)
            img = QImage()
            img.loadFromData(img_data)
            pixmap = QPixmap.fromImage(img)
            
            self.chart_label.setPixmap(pixmap)
            self.stack.setCurrentIndex(1)
            
        except Exception as e:
            print(f"chart display error: {e}")
    
    def _enable_controls(self, enabled: bool):
        """
        enable/disable controls
        """
        self.btn_save_model.setEnabled(enabled)
        self.btn_refresh_chart.setEnabled(enabled)
        self.btn_show_summary.setEnabled(enabled)
        self.btn_export.setEnabled(enabled)
        self.btn_bookmark.setEnabled(enabled)
    
    # ================ PUBLIC ================
    
    def on_tab_activated(self):
        """
        called when tab is activated
        """
        has_data = STATE.clean_data is not None
        self.btn_run_forecast.setEnabled(has_data)
        self.btn_compare_models.setEnabled(has_data)
        
        if STATE.forecast_data is not None:
            self._update_results_display()
            self._enable_controls(True)
    
    def refresh(self):
        """
        refresh tab contents
        """
        if STATE.forecast_data is not None:
            self._on_refresh_chart()
            self._update_metrics_table()