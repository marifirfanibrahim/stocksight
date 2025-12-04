"""
forecast tab module
tab 4 forecast factory
generates and exports forecasts
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QFrame, QSplitter,
    QTableView, QComboBox, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from typing import Optional, Dict, List

import config
from core.forecaster import Forecaster
from ui.widgets.virtual_data_table import VirtualDataTable
from ui.widgets.time_series_chart import TimeSeriesChart
from ui.models.forecast_model import ForecastTableModel
from ui.dialogs.forecast_settings_dialog import ForecastSettingsDialog
from ui.widgets.export_wizard import ExportWizard
from ui.widgets.progress_dialog import ProgressDialog
from utils.worker_threads import WorkerThread
from utils.export_formatter import ExportFormatter


# ============================================================================
#                            FORECAST TAB
# ============================================================================

class ForecastTab(QWidget):
    # forecast factory tab
    
    # signals
    forecasts_generated = pyqtSignal(dict)
    
    def __init__(self, session_model, parent=None):
        # initialize tab
        super().__init__(parent)
        
        self._session = session_model
        self._forecaster = Forecaster()
        self._exporter = ExportFormatter()
        self._processor = None
        self._worker = None
        self._current_sku = None
        self._current_frequency = "D"
        
        self._setup_ui()
        self._connect_signals()
    
    # ---------- UI SETUP ----------
    
    def _setup_ui(self) -> None:
        # setup user interface
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # header with actions
        header_layout = QHBoxLayout()
        
        header = QLabel("Forecast Factory")
        header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # strategy indicator
        self._strategy_label = QLabel("Strategy: Not Set")
        self._strategy_label.setStyleSheet("color: gray;")
        header_layout.addWidget(self._strategy_label)
        
        # configure button
        self._config_btn = QPushButton("⚙ Configure")
        self._config_btn.clicked.connect(self._show_settings)
        header_layout.addWidget(self._config_btn)
        
        # run forecast button
        self._run_btn = QPushButton("▶ Generate Forecasts")
        self._run_btn.setMinimumWidth(150)
        self._run_btn.clicked.connect(self._run_forecasts)
        header_layout.addWidget(self._run_btn)
        
        layout.addLayout(header_layout)
        
        # main splitter
        splitter = QSplitter(Qt.Vertical)
        
        # top section - results table
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # results header
        results_header = QHBoxLayout()
        
        results_label = QLabel("Forecast Results")
        results_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        results_header.addWidget(results_label)
        
        results_header.addStretch()
        
        # filter
        results_header.addWidget(QLabel("Show:"))
        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["All Items", "A-Items", "B-Items", "C-Items", "Problems Only", "Bookmarked"])
        self._filter_combo.currentIndexChanged.connect(self._apply_filter)
        results_header.addWidget(self._filter_combo)
        
        top_layout.addLayout(results_header)
        
        # results table
        self._results_table = QTableView()
        self._results_model = ForecastTableModel()
        self._results_table.setModel(self._results_model)
        self._results_table.setAlternatingRowColors(True)
        self._results_table.setSortingEnabled(True)
        self._results_table.setSelectionBehavior(QTableView.SelectRows)
        self._results_table.horizontalHeader().setStretchLastSection(True)
        self._results_table.clicked.connect(self._on_result_selected)
        
        top_layout.addWidget(self._results_table)
        
        splitter.addWidget(top_widget)
        
        # bottom section - chart and details
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # chart
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        
        chart_label = QLabel("Forecast Preview")
        chart_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        chart_layout.addWidget(chart_label)
        
        self._chart = TimeSeriesChart()
        chart_layout.addWidget(self._chart)
        
        bottom_layout.addWidget(chart_widget, stretch=2)
        
        # details panel
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 0, 0, 0)
        
        details_layout.addWidget(self._create_summary_group())
        details_layout.addWidget(self._create_metrics_group())
        details_layout.addWidget(self._create_export_group())
        
        bottom_layout.addWidget(details_widget, stretch=1)
        
        splitter.addWidget(bottom_widget)
        
        # set splitter sizes
        splitter.setSizes([400, 300])
        
        layout.addWidget(splitter)
        
        # status bar
        status_layout = QHBoxLayout()
        
        self._status_label = QLabel("Configure and run forecasts to see results")
        self._status_label.setStyleSheet("color: gray;")
        status_layout.addWidget(self._status_label)
        
        status_layout.addStretch()
        
        self._progress_label = QLabel("")
        status_layout.addWidget(self._progress_label)
        
        layout.addLayout(status_layout)
    
    def _create_summary_group(self) -> QGroupBox:
        # create summary group
        group = QGroupBox("Forecast Summary")
        layout = QVBoxLayout(group)
        
        self._summary_label = QLabel("No forecasts generated yet")
        self._summary_label.setWordWrap(True)
        self._summary_label.setStyleSheet("color: gray;")
        layout.addWidget(self._summary_label)
        
        return group
    
    def _create_metrics_group(self) -> QGroupBox:
        # create metrics group
        group = QGroupBox("Selected Item Metrics")
        layout = QVBoxLayout(group)
        
        self._metrics_label = QLabel("Select an item to view metrics")
        self._metrics_label.setWordWrap(True)
        self._metrics_label.setStyleSheet("color: gray;")
        layout.addWidget(self._metrics_label)
        
        return group
    
    def _create_export_group(self) -> QGroupBox:
        # create export group
        group = QGroupBox("Export")
        layout = QVBoxLayout(group)
        
        # quick export buttons
        self._export_csv_btn = QPushButton("📄 Export to CSV")
        self._export_csv_btn.setEnabled(False)
        self._export_csv_btn.clicked.connect(self._export_csv)
        layout.addWidget(self._export_csv_btn)
        
        self._export_excel_btn = QPushButton("📊 Export to Excel")
        self._export_excel_btn.setEnabled(False)
        self._export_excel_btn.clicked.connect(self._export_excel)
        layout.addWidget(self._export_excel_btn)
        
        self._export_ppt_btn = QPushButton("📽 Export to PowerPoint")
        self._export_ppt_btn.setEnabled(False)
        self._export_ppt_btn.clicked.connect(self._export_ppt)
        layout.addWidget(self._export_ppt_btn)
        
        # export wizard button
        self._export_wizard_btn = QPushButton("🧙 Export Wizard...")
        self._export_wizard_btn.setEnabled(False)
        self._export_wizard_btn.clicked.connect(self._show_export_wizard)
        layout.addWidget(self._export_wizard_btn)
        
        return group
    
    def _connect_signals(self) -> None:
        # connect widget signals
        pass
    
    # ---------- SETTINGS ----------
    
    def _show_settings(self) -> None:
        # show forecast settings dialog
        sku_count = self._session.state.total_skus or 0
        
        dialog = ForecastSettingsDialog(sku_count, self)
        dialog.settings_confirmed.connect(self._on_settings_confirmed)
        dialog.exec_()
    
    def _on_settings_confirmed(self, settings: Dict) -> None:
        # handle settings confirmed
        self._settings = settings
        self._current_frequency = settings.get("frequency", "D")
        
        strategy = settings.get("strategy", "balanced")
        strategy_info = config.FORECASTING.get(strategy, {})
        
        # frequency label
        freq_labels = {"D": "Daily", "W": "Weekly", "M": "Monthly"}
        freq_label = freq_labels.get(self._current_frequency, "Daily")
        
        self._strategy_label.setText(
            f"Strategy: {strategy_info.get('icon', '')} {strategy_info.get('name', strategy)} | {freq_label}"
        )
        self._strategy_label.setStyleSheet("color: #333;")
    
    # ---------- FORECASTING ----------
    
    def _run_forecasts(self) -> None:
        # run forecast generation
        if self._processor is None:
            QMessageBox.warning(self, "No Data", "Please load data first")
            return
        
        # get or show settings
        if not hasattr(self, "_settings"):
            self._show_settings()
            return
        
        settings = self._settings
        self._current_frequency = settings.get("frequency", "D")
        
        # show progress
        progress = ProgressDialog("Generating Forecasts", self)
        progress.set_status("Preparing forecast models...")
        progress.start()
        
        # get column names
        sku_col = self._processor.get_mapped_column("sku")
        date_col = self._processor.get_mapped_column("date")
        qty_col = self._processor.get_mapped_column("quantity")
        
        # get tier mapping
        tier_mapping = {}
        clusters = self._session.get_clusters()
        for sku, cluster in clusters.items():
            tier_mapping[sku] = cluster.volume_tier
        
        # get features
        features_data = self._session.get_features()
        feature_cols = features_data.get("selected_features", []) if features_data else None
        
        # run in background
        def do_forecasting(progress_callback=None):
            return self._forecaster.forecast_batch(
                self._processor.processed_data,
                sku_col, date_col, qty_col,
                strategy=settings.get("strategy", "balanced"),
                horizon=settings.get("horizon", 30),
                frequency=settings.get("frequency", "D"),
                tier_mapping=tier_mapping if settings.get("tier_processing", True) else None,
                features=feature_cols,
                progress_callback=progress_callback
            )
        
        self._worker = WorkerThread(do_forecasting)
        self._worker.progress_signal.connect(progress.set_progress)
        self._worker.progress_text_signal.connect(lambda t: progress.set_status(f"Forecasting: {t}"))
        self._worker.result_signal.connect(lambda r: self._on_forecasts_complete(r, progress))
        self._worker.error_signal.connect(lambda e: self._on_forecast_error(e, progress))
        self._worker.start()
    
    def _on_forecasts_complete(self, forecasts: Dict, progress: ProgressDialog) -> None:
        # handle forecasts complete
        progress.finish("Forecasts generated successfully")
        
        # update model
        self._results_model.set_forecasts(forecasts)
        
        # resize columns
        self._results_table.resizeColumnsToContents()
        
        # update session
        self._session.set_forecasts(forecasts)
        
        # update summary
        self._update_summary()
        
        # enable export
        self._enable_export(True)
        
        # emit signal
        self.forecasts_generated.emit(forecasts)
        
        self._status_label.setText(f"Generated forecasts for {len(forecasts):,} items")
    
    def _on_forecast_error(self, error: str, progress: ProgressDialog) -> None:
        # handle forecast error
        progress.finish(f"Error: {error}", auto_close=False)
        QMessageBox.critical(self, "Forecast Error", f"Failed to generate forecasts:\n{error}")
    
    def _update_summary(self) -> None:
        # update forecast summary
        summary = self._results_model.get_summary()
        
        if not summary:
            return
        
        total = summary.get("total_items", 0)
        total_forecast = summary.get("total_forecast", 0)
        avg_mape = summary.get("avg_mape", 0)
        
        status_dist = summary.get("status_distribution", {})
        good = status_dist.get("Good", 0)
        fair = status_dist.get("Fair", 0)
        review = status_dist.get("Review", 0)
        
        # frequency label
        freq_labels = {"D": "daily", "W": "weekly", "M": "monthly"}
        freq_label = freq_labels.get(self._current_frequency, "daily")
        
        summary_text = (
            f"<b>Total Items:</b> {total:,}<br>"
            f"<b>Total Forecast:</b> {total_forecast:,.0f} units<br>"
            f"<b>Frequency:</b> {freq_label.title()}<br>"
            f"<b>Average Accuracy:</b> {100-avg_mape:.1f}% (MAPE: {avg_mape:.1f}%)<br><br>"
            f"<b>Quality:</b><br>"
            f"✓ Good: {good} | ⚠ Fair: {fair} | ✗ Review: {review}"
        )
        
        self._summary_label.setText(summary_text)
        self._summary_label.setStyleSheet("color: #333;")
    
    # ---------- RESULT SELECTION ----------
    
    def _on_result_selected(self, index) -> None:
        # handle result row selection
        row = index.row()
        forecast = self._results_model.get_row_forecast(row)
        
        if forecast is None:
            return
        
        self._current_sku = forecast.sku
        
        # update chart
        self._update_chart(forecast)
        
        # update metrics
        self._update_metrics(forecast)
    
    def _update_chart(self, forecast) -> None:
        # update chart with forecast
        if self._processor is None:
            return
        
        # get historical data
        sku_data = self._processor.get_sku_data(forecast.sku)
        date_col = self._processor.get_mapped_column("date")
        qty_col = self._processor.get_mapped_column("quantity")
        
        # get frequency from forecast result
        frequency = getattr(forecast, 'frequency', self._current_frequency)
        
        if not sku_data.empty:
            # aggregate historical data to match forecast frequency
            hist_aggregated = self._forecaster.aggregate_to_frequency(
                sku_data, date_col, qty_col, frequency
            )
            hist_dates = hist_aggregated[date_col].tolist()
            hist_values = hist_aggregated[qty_col].tolist()
            self._chart.set_data(hist_dates, hist_values, label="Historical")
        
        # add forecast
        self._chart.set_forecast(
            forecast.dates,
            forecast.forecast,
            forecast.lower_bound,
            forecast.upper_bound
        )
        
        # update chart frequency for proper axis formatting
        self._chart.set_frequency(frequency)
    
    def _update_metrics(self, forecast) -> None:
        # update metrics display
        metrics = forecast.metrics
        
        mape = metrics.get("mape", 0)
        mae = metrics.get("mae", 0)
        rmse = metrics.get("rmse", 0)
        
        total = sum(forecast.forecast)
        avg_period = total / len(forecast.forecast) if forecast.forecast else 0
        
        # frequency label for period description
        frequency = getattr(forecast, 'frequency', self._current_frequency)
        period_labels = {"D": "Daily", "W": "Weekly", "M": "Monthly"}
        period_label = period_labels.get(frequency, "Period")
        
        metrics_text = (
            f"<b>Item:</b> {forecast.sku}<br>"
            f"<b>Model:</b> {forecast.model}<br><br>"
            f"<b>Forecast Total:</b> {total:,.0f} units<br>"
            f"<b>{period_label} Average:</b> {avg_period:,.1f} units<br>"
            f"<b>Periods:</b> {len(forecast.forecast)}<br><br>"
            f"<b>MAPE:</b> {mape:.1f}%<br>"
            f"<b>MAE:</b> {mae:.2f}<br>"
            f"<b>RMSE:</b> {rmse:.2f}"
        )
        
        self._metrics_label.setText(metrics_text)
        self._metrics_label.setStyleSheet("color: #333;")
    
    # ---------- FILTERING ----------
    
    def _apply_filter(self) -> None:
        # apply result filter
        filter_text = self._filter_combo.currentText()
        
        # get forecasts
        forecasts = self._session.get_forecasts()
        if not forecasts:
            return
        
        # filter based on selection
        if filter_text == "All Items":
            filtered = forecasts
        elif filter_text == "A-Items":
            clusters = self._session.get_clusters()
            filtered = {k: v for k, v in forecasts.items() 
                       if clusters.get(k) and clusters[k].volume_tier == "A"}
        elif filter_text == "B-Items":
            clusters = self._session.get_clusters()
            filtered = {k: v for k, v in forecasts.items() 
                       if clusters.get(k) and clusters[k].volume_tier == "B"}
        elif filter_text == "C-Items":
            clusters = self._session.get_clusters()
            filtered = {k: v for k, v in forecasts.items() 
                       if clusters.get(k) and clusters[k].volume_tier == "C"}
        elif filter_text == "Problems Only":
            filtered = {k: v for k, v in forecasts.items() 
                       if v.metrics.get("mape", 0) > 30}
        elif filter_text == "Bookmarked":
            bookmarks = [b["sku"] for b in self._session.get_bookmarks()]
            filtered = {k: v for k, v in forecasts.items() if k in bookmarks}
        else:
            filtered = forecasts
        
        self._results_model.set_forecasts(filtered)
        self._status_label.setText(f"Showing {len(filtered):,} of {len(forecasts):,} items")
    
    # ---------- EXPORT ----------
    
    def _enable_export(self, enabled: bool) -> None:
        # enable or disable export buttons
        self._export_csv_btn.setEnabled(enabled)
        self._export_excel_btn.setEnabled(enabled)
        self._export_ppt_btn.setEnabled(enabled)
        self._export_wizard_btn.setEnabled(enabled)
    
    def _export_csv(self) -> None:
        # export to csv
        forecasts = self._session.get_forecasts()
        if not forecasts:
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", 
            self._exporter.get_export_filename("forecast", "csv"),
            "CSV Files (*.csv)"
        )
        
        if path:
            df = self._exporter.format_forecast_csv(forecasts)
            success, message = self._exporter.export_csv(df, path)
            
            if success:
                QMessageBox.information(self, "Export Complete", f"Exported to:\n{path}")
            else:
                QMessageBox.warning(self, "Export Failed", message)
    
    def _export_excel(self) -> None:
        # export to excel
        forecasts = self._session.get_forecasts()
        if not forecasts:
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Excel",
            self._exporter.get_export_filename("forecast", "excel"),
            "Excel Files (*.xlsx)"
        )
        
        if path:
            summary = self._results_model.get_summary()
            summary_df = self._forecaster.get_forecast_summary()
            
            success, message = self._exporter.create_forecast_workbook(
                forecasts, summary_df, path
            )
            
            if success:
                QMessageBox.information(self, "Export Complete", f"Exported to:\n{path}")
            else:
                QMessageBox.warning(self, "Export Failed", message)
    
    def _export_ppt(self) -> None:
        # export to powerpoint
        forecasts = self._session.get_forecasts()
        if not forecasts:
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PowerPoint",
            self._exporter.get_export_filename("forecast", "ppt"),
            "PowerPoint Files (*.pptx)"
        )
        
        if path:
            cluster_summary = []
            clusters = self._session.get_clusters()
            
            success, message = self._exporter.create_executive_ppt(
                forecasts, cluster_summary, path
            )
            
            if success:
                QMessageBox.information(self, "Export Complete", f"Exported to:\n{path}")
            else:
                QMessageBox.warning(self, "Export Failed", message)
    
    def _show_export_wizard(self) -> None:
        # show export wizard
        wizard = ExportWizard(self)
        wizard.set_available_data(["forecasts", "summary", "metrics", "clusters"])
        wizard.export_requested.connect(self._on_export_wizard_complete)
        wizard.exec_()
    
    def _on_export_wizard_complete(self, export_config: Dict) -> None:
        # handle export wizard completion
        forecasts = self._session.get_forecasts()
        if not forecasts:
            return
        
        file_path = export_config.get("file_path", "")
        format_type = export_config.get("format", "csv")
        
        if format_type == "csv":
            df = self._exporter.format_forecast_csv(forecasts)
            success, message = self._exporter.export_csv(df, file_path)
        elif format_type == "excel":
            summary_df = self._forecaster.get_forecast_summary()
            success, message = self._exporter.create_forecast_workbook(
                forecasts, summary_df, file_path
            )
        elif format_type == "ppt":
            success, message = self._exporter.create_executive_ppt(
                forecasts, [], file_path
            )
        else:
            success, message = False, "Unsupported format"
        
        if success:
            QMessageBox.information(self, "Export Complete", f"Exported to:\n{file_path}")
        else:
            QMessageBox.warning(self, "Export Failed", message)
    
    # ---------- PUBLIC METHODS ----------
    
    def set_processor(self, processor) -> None:
        # set data processor
        self._processor = processor
    
    def refresh(self) -> None:
        # refresh tab
        forecasts = self._session.get_forecasts()
        if forecasts:
            self._results_model.set_forecasts(forecasts)
            self._update_summary()
            self._enable_export(True)