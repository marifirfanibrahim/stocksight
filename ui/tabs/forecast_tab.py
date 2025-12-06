"""
forecast tab module
tab 4 forecast factory
generates and exports forecasts
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QFrame, QSplitter,
    QTableView, QTableWidget, QTableWidgetItem,
    QComboBox, QMessageBox, QFileDialog, QHeaderView,
    QAbstractItemView, QScrollArea
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
from ui.dialogs.help_dialog import ForecastHelpDialog
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
        self._comparison_results = None
        self._current_forecast_result = None
        
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
        
        # help button
        self._help_btn = QPushButton("❓ What do these terms mean?")
        self._help_btn.setMaximumWidth(200)
        self._help_btn.clicked.connect(self._show_help)
        header_layout.addWidget(self._help_btn)
        
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
        
        # main horizontal splitter - left (results/chart) and right (details)
        main_splitter = QSplitter(Qt.Horizontal)
        
        # left side - results table and chart
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # results section
        left_layout.addWidget(self._create_results_section(), stretch=1)
        
        # chart section
        left_layout.addWidget(self._create_chart_section(), stretch=1)
        
        main_splitter.addWidget(left_widget)
        
        # right side - summary and details
        right_widget = QWidget()
        right_widget.setMinimumWidth(320)
        right_widget.setMaximumWidth(400)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # scroll area for right panel
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(5, 5, 5, 5)
        scroll_layout.setSpacing(10)
        
        scroll_layout.addWidget(self._create_summary_group())
        scroll_layout.addWidget(self._create_metrics_group())
        scroll_layout.addWidget(self._create_forecast_values_group())
        scroll_layout.addWidget(self._create_comparison_group())
        scroll_layout.addWidget(self._create_export_group())
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        right_layout.addWidget(scroll)
        
        main_splitter.addWidget(right_widget)
        
        # set splitter sizes
        main_splitter.setSizes([700, 350])
        
        layout.addWidget(main_splitter)
        
        # status bar
        status_layout = QHBoxLayout()
        
        self._status_label = QLabel("Configure and run forecasts to see results")
        self._status_label.setStyleSheet("color: gray;")
        status_layout.addWidget(self._status_label)
        
        status_layout.addStretch()
        
        self._progress_label = QLabel("")
        status_layout.addWidget(self._progress_label)
        
        layout.addLayout(status_layout)
    
    def _create_results_section(self) -> QGroupBox:
        # create results section
        group = QGroupBox("Forecast Results")
        layout = QVBoxLayout(group)
        
        # results header with filters
        results_header = QHBoxLayout()
        
        # item filter
        results_header.addWidget(QLabel("Items:"))
        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["All Items", "A-Items", "B-Items", "C-Items", "Bookmarked"])
        self._filter_combo.currentIndexChanged.connect(self._apply_filter)
        results_header.addWidget(self._filter_combo)
        
        results_header.addSpacing(20)
        
        # quality filter
        results_header.addWidget(QLabel("Quality:"))
        self._quality_filter = QComboBox()
        self._quality_filter.addItems(["All Quality", "Good Only", "Fair Only", "Review Needed"])
        self._quality_filter.currentIndexChanged.connect(self._apply_filter)
        results_header.addWidget(self._quality_filter)
        
        results_header.addStretch()
        
        layout.addLayout(results_header)
        
        # results table
        self._results_table = QTableView()
        self._results_model = ForecastTableModel()
        self._results_table.setModel(self._results_model)
        self._results_table.setAlternatingRowColors(True)
        self._results_table.setSortingEnabled(True)
        self._results_table.setSelectionBehavior(QTableView.SelectRows)
        self._results_table.horizontalHeader().setStretchLastSection(True)
        self._results_table.clicked.connect(self._on_result_selected)
        
        layout.addWidget(self._results_table)
        
        return group
    
    def _create_chart_section(self) -> QGroupBox:
        # create chart section
        group = QGroupBox("Forecast Preview")
        layout = QVBoxLayout(group)
        
        self._chart = TimeSeriesChart()
        layout.addWidget(self._chart)
        
        return group
    
    def _create_summary_group(self) -> QGroupBox:
        # create summary group
        group = QGroupBox("Forecast Summary")
        layout = QVBoxLayout(group)
        
        self._summary_label = QLabel("No forecasts generated yet")
        self._summary_label.setWordWrap(True)
        self._summary_label.setStyleSheet("color: gray;")
        self._summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self._summary_label)
        
        return group
    
    def _create_metrics_group(self) -> QGroupBox:
        # create metrics group
        group = QGroupBox("Selected Item Metrics")
        layout = QVBoxLayout(group)
        
        self._metrics_label = QLabel("Select an item to view metrics")
        self._metrics_label.setWordWrap(True)
        self._metrics_label.setStyleSheet("color: gray;")
        self._metrics_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self._metrics_label)
        
        return group
    
    def _create_forecast_values_group(self) -> QGroupBox:
        # create forecast values group
        group = QGroupBox("Forecasted Values")
        layout = QVBoxLayout(group)
        
        # date filter
        date_filter_layout = QHBoxLayout()
        date_filter_layout.addWidget(QLabel("Show:"))
        
        self._date_filter = QComboBox()
        self._date_filter.addItems(["First 10", "Last 10", "All Dates"])
        self._date_filter.currentIndexChanged.connect(self._update_forecast_values_display)
        date_filter_layout.addWidget(self._date_filter)
        
        date_filter_layout.addStretch()
        layout.addLayout(date_filter_layout)
        
        # values table
        self._values_table = QTableWidget()
        self._values_table.setColumnCount(3)
        self._values_table.setHorizontalHeaderLabels(["Date", "Forecast", "Range"])
        self._values_table.setAlternatingRowColors(True)
        self._values_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._values_table.horizontalHeader().setStretchLastSection(True)
        self._values_table.setMaximumHeight(200)
        layout.addWidget(self._values_table)
        
        self._values_info_label = QLabel("")
        self._values_info_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self._values_info_label)
        
        return group
    
    def _create_comparison_group(self) -> QGroupBox:
        # create model comparison group
        group = QGroupBox("Model Comparison")
        layout = QVBoxLayout(group)
        
        self._comparison_label = QLabel("Enable comparison in settings to see results")
        self._comparison_label.setWordWrap(True)
        self._comparison_label.setStyleSheet("color: gray;")
        self._comparison_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self._comparison_label)
        
        self._export_comparison_btn = QPushButton("📊 Export Comparison Report")
        self._export_comparison_btn.setEnabled(False)
        self._export_comparison_btn.clicked.connect(self._export_comparison)
        layout.addWidget(self._export_comparison_btn)
        
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
    
    # ---------- HELP ----------
    
    def _show_help(self) -> None:
        # show forecast terminology help dialog
        dialog = ForecastHelpDialog(self)
        dialog.exec_()
    
    # ---------- SETTINGS ----------
    
    def _show_settings(self) -> None:
        # show forecast settings dialog
        sku_count = self._session.state.total_skus or 0
        
        # get cluster info for advanced strategy
        clusters = self._session.get_clusters()
        a_item_count = sum(1 for c in clusters.values() if c.volume_tier == "A") if clusters else 0
        
        dialog = ForecastSettingsDialog(sku_count, a_item_count, self)
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
        
        # show item scope for advanced
        scope_text = ""
        if strategy == "advanced":
            scope_text = " (A-items only)"
        
        self._strategy_label.setText(
            f"Strategy: {strategy_info.get('icon', '')} {strategy_info.get('name', strategy)}{scope_text} | {freq_label}"
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
        generate_comparison = settings.get("model_comparison", False)
        strategy = settings.get("strategy", "balanced")
        
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
        
        # for advanced strategy, filter to A-items only
        data_to_forecast = self._processor.processed_data
        if strategy == "advanced":
            a_items = [sku for sku, tier in tier_mapping.items() if tier == "A"]
            if a_items:
                data_to_forecast = self._processor.processed_data[
                    self._processor.processed_data[sku_col].isin(a_items)
                ]
                progress.set_status(f"Forecasting {len(a_items)} A-items with advanced models...")
        
        # get features
        features_data = self._session.get_features()
        feature_cols = features_data.get("selected_features", []) if features_data else None
        
        # run in background
        def do_forecasting(progress_callback=None):
            # generate main forecasts
            forecasts = self._forecaster.forecast_batch(
                data_to_forecast,
                sku_col, date_col, qty_col,
                strategy=strategy,
                horizon=settings.get("horizon", 30),
                frequency=settings.get("frequency", "D"),
                tier_mapping=tier_mapping if settings.get("tier_processing", True) else None,
                features=feature_cols,
                progress_callback=progress_callback
            )
            
            # generate comparison if enabled
            comparison = None
            if generate_comparison:
                comparison = self._forecaster.compare_models(
                    data_to_forecast,
                    sku_col, date_col, qty_col,
                    horizon=settings.get("horizon", 30),
                    frequency=settings.get("frequency", "D"),
                    sample_size=min(50, len(data_to_forecast[sku_col].unique()))
                )
            
            return forecasts, comparison
        
        self._worker = WorkerThread(do_forecasting)
        self._worker.progress_signal.connect(progress.set_progress)
        self._worker.progress_text_signal.connect(lambda t: progress.set_status(f"Forecasting: {t}"))
        self._worker.result_signal.connect(lambda r: self._on_forecasts_complete(r, progress))
        self._worker.error_signal.connect(lambda e: self._on_forecast_error(e, progress))
        self._worker.start()
    
    def _on_forecasts_complete(self, result: tuple, progress: ProgressDialog) -> None:
        # handle forecasts complete
        forecasts, comparison = result
        
        progress.finish("Forecasts generated successfully")
        
        # store comparison results
        self._comparison_results = comparison
        
        # update model
        self._results_model.set_forecasts(forecasts)
        
        # resize columns
        self._results_table.resizeColumnsToContents()
        
        # update session
        self._session.set_forecasts(forecasts)
        
        # update summary
        self._update_summary()
        
        # update comparison display
        self._update_comparison_display()
        
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
    
    def _update_comparison_display(self) -> None:
        # update comparison section
        if self._comparison_results is None:
            self._comparison_label.setText("Enable comparison in settings to see results")
            self._comparison_label.setStyleSheet("color: gray;")
            self._export_comparison_btn.setEnabled(False)
            return
        
        # format comparison results
        comparison = self._comparison_results
        
        if not comparison:
            self._comparison_label.setText("No comparison data available")
            return
        
        # build display text
        lines = ["<b>Model Performance Summary:</b><br>"]
        
        model_stats = comparison.get("model_stats", {})
        for model, stats in sorted(model_stats.items(), key=lambda x: x[1].get("avg_mape", 100)):
            avg_mape = stats.get("avg_mape", 0)
            win_rate = stats.get("win_rate", 0) * 100
            lines.append(f"• {model}: MAPE {avg_mape:.1f}%, wins {win_rate:.0f}%")
        
        best_model = comparison.get("best_overall", "N/A")
        lines.append(f"<br><b>Best Overall:</b> {best_model}")
        
        self._comparison_label.setText("<br>".join(lines))
        self._comparison_label.setStyleSheet("color: #333;")
        self._export_comparison_btn.setEnabled(True)
    
    # ---------- RESULT SELECTION ----------
    
    def _on_result_selected(self, index) -> None:
        # handle result row selection
        row = index.row()
        forecast = self._results_model.get_row_forecast(row)
        
        if forecast is None:
            return
        
        self._current_sku = forecast.sku
        self._current_forecast_result = forecast
        
        # update chart
        self._update_chart(forecast)
        
        # update metrics
        self._update_metrics(forecast)
        
        # update forecast values display
        self._update_forecast_values_display()
    
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
    
    def _update_forecast_values_display(self) -> None:
        # update forecast values table
        if self._current_forecast_result is None:
            self._values_table.setRowCount(0)
            self._values_info_label.setText("")
            return
        
        forecast = self._current_forecast_result
        dates = forecast.dates
        values = forecast.forecast
        lower = forecast.lower_bound
        upper = forecast.upper_bound
        
        total_periods = len(dates)
        
        # apply date filter
        filter_text = self._date_filter.currentText()
        
        if filter_text == "First 10":
            display_dates = dates[:10]
            display_values = values[:10]
            display_lower = lower[:10] if lower else [0] * len(display_values)
            display_upper = upper[:10] if upper else [0] * len(display_values)
        elif filter_text == "Last 10":
            display_dates = dates[-10:]
            display_values = values[-10:]
            display_lower = lower[-10:] if lower else [0] * len(display_values)
            display_upper = upper[-10:] if upper else [0] * len(display_values)
        else:  # all dates
            display_dates = dates
            display_values = values
            display_lower = lower if lower else [0] * len(display_values)
            display_upper = upper if upper else [0] * len(display_values)
        
        # populate table
        self._values_table.setRowCount(len(display_dates))
        
        for i, (date, val, low, high) in enumerate(zip(display_dates, display_values, display_lower, display_upper)):
            # date - remove timestamp if present
            date_str = str(date).split(" ")[0] if " " in str(date) else str(date)
            date_item = QTableWidgetItem(date_str)
            self._values_table.setItem(i, 0, date_item)
            
            # forecast value
            val_item = QTableWidgetItem(f"{val:,.0f}")
            val_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._values_table.setItem(i, 1, val_item)
            
            # range
            range_item = QTableWidgetItem(f"{low:,.0f} - {high:,.0f}")
            range_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._values_table.setItem(i, 2, range_item)
        
        # resize columns
        self._values_table.resizeColumnsToContents()
        
        # update info label
        if total_periods > 10 and filter_text != "All Dates":
            self._values_info_label.setText(f"Showing {len(display_dates)} of {total_periods} periods. Select 'All Dates' to see all.")
        else:
            self._values_info_label.setText(f"Showing all {total_periods} periods")
    
    # ---------- FILTERING ----------
    
    def _apply_filter(self) -> None:
        # apply result filters
        item_filter = self._filter_combo.currentText()
        quality_filter = self._quality_filter.currentText()
        
        # get forecasts
        forecasts = self._session.get_forecasts()
        if not forecasts:
            return
        
        filtered = forecasts.copy()
        
        # apply item filter
        if item_filter == "A-Items":
            clusters = self._session.get_clusters()
            filtered = {k: v for k, v in filtered.items() 
                       if clusters.get(k) and clusters[k].volume_tier == "A"}
        elif item_filter == "B-Items":
            clusters = self._session.get_clusters()
            filtered = {k: v for k, v in filtered.items() 
                       if clusters.get(k) and clusters[k].volume_tier == "B"}
        elif item_filter == "C-Items":
            clusters = self._session.get_clusters()
            filtered = {k: v for k, v in filtered.items() 
                       if clusters.get(k) and clusters[k].volume_tier == "C"}
        elif item_filter == "Bookmarked":
            bookmarks = [b["sku"] for b in self._session.get_bookmarks()]
            filtered = {k: v for k, v in filtered.items() if k in bookmarks}
        
        # apply quality filter
        if quality_filter == "Good Only":
            filtered = {k: v for k, v in filtered.items() 
                       if v.metrics.get("mape", 100) < 15}
        elif quality_filter == "Fair Only":
            filtered = {k: v for k, v in filtered.items() 
                       if 15 <= v.metrics.get("mape", 100) < 30}
        elif quality_filter == "Review Needed":
            filtered = {k: v for k, v in filtered.items() 
                       if v.metrics.get("mape", 0) >= 30}
        
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
    
    def _export_comparison(self) -> None:
        # export model comparison report
        if self._comparison_results is None:
            QMessageBox.warning(self, "No Data", "No comparison data to export")
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Comparison Report",
            self._exporter.get_export_filename("model_comparison", "excel"),
            "Excel Files (*.xlsx)"
        )
        
        if path:
            success, message = self._exporter.export_comparison_report(
                self._comparison_results, path
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