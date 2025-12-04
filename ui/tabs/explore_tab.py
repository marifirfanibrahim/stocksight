"""
explore tab module
tab 2 pattern discovery
handles sku browsing clustering and anomaly detection
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QFrame, QSplitter,
    QTabWidget, QMessageBox, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from typing import Optional, Dict, List

import config
from core.rule_clustering import RuleClustering
from core.anomaly_detector import AnomalyDetector
from ui.widgets.sku_navigator import SKUNavigator
from ui.widgets.time_series_chart import TimeSeriesChart
from ui.widgets.heatmap_widget import HeatmapWidget
from ui.dialogs.clustering_config_dialog import ClusteringConfigDialog
from ui.dialogs.anomaly_review_dialog import AnomalyReviewDialog
from utils.worker_threads import WorkerThread, SimpleWorker
from ui.widgets.progress_dialog import ProgressDialog


# ============================================================================
#                             EXPLORE TAB
# ============================================================================

class ExploreTab(QWidget):
    # pattern discovery tab
    
    # signals
    clusters_created = pyqtSignal(dict)
    proceed_requested = pyqtSignal()
    navigate_to_data = pyqtSignal(str)  # sku to correct
    
    def __init__(self, session_model, parent=None):
        # initialize tab
        super().__init__(parent)
        
        self._session = session_model
        self._clustering = RuleClustering()
        self._anomaly_detector = AnomalyDetector()
        self._processor = None
        self._worker = None
        self._current_sku = None
        
        self._setup_ui()
        self._connect_signals()
    
    # ---------- UI SETUP ----------
    
    def _setup_ui(self) -> None:
        # setup user interface
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # header with actions
        header_layout = QHBoxLayout()
        
        header = QLabel("Pattern Discovery")
        header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # clustering config button
        self._cluster_config_btn = QPushButton("⚙ Clustering Settings")
        self._cluster_config_btn.clicked.connect(self._show_clustering_config)
        header_layout.addWidget(self._cluster_config_btn)
        
        # run clustering button
        self._run_clustering_btn = QPushButton("▶ Run Clustering")
        self._run_clustering_btn.clicked.connect(self._run_clustering)
        header_layout.addWidget(self._run_clustering_btn)
        
        # detect anomalies button
        self._detect_anomalies_btn = QPushButton("🔍 Detect Anomalies")
        self._detect_anomalies_btn.clicked.connect(self._detect_anomalies)
        header_layout.addWidget(self._detect_anomalies_btn)
        
        layout.addLayout(header_layout)
        
        # main splitter - three pane view
        main_splitter = QSplitter(Qt.Horizontal)
        
        # left pane - navigator
        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        nav_label = QLabel("Item Navigator")
        nav_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        left_layout.addWidget(nav_label)
        
        self._navigator = SKUNavigator()
        left_layout.addWidget(self._navigator)
        
        main_splitter.addWidget(left_pane)
        
        # center pane - visualizations
        center_pane = QWidget()
        center_layout = QVBoxLayout(center_pane)
        center_layout.setContentsMargins(0, 0, 0, 0)
        
        # visualization tabs
        self._viz_tabs = QTabWidget()
        
        # time series tab
        ts_widget = QWidget()
        ts_layout = QVBoxLayout(ts_widget)
        ts_layout.setContentsMargins(5, 5, 5, 5)
        
        self._chart = TimeSeriesChart()
        ts_layout.addWidget(self._chart)
        
        self._viz_tabs.addTab(ts_widget, "Time Series")
        
        # heatmap tab
        heatmap_widget = QWidget()
        heatmap_layout = QVBoxLayout(heatmap_widget)
        heatmap_layout.setContentsMargins(5, 5, 5, 5)
        
        self._heatmap = HeatmapWidget()
        self._heatmap.set_title("Cluster Distribution")
        heatmap_layout.addWidget(self._heatmap)
        
        self._viz_tabs.addTab(heatmap_widget, "Cluster Map")
        
        # sparklines tab
        sparklines_widget = QWidget()
        sparklines_layout = QVBoxLayout(sparklines_widget)
        sparklines_layout.setContentsMargins(5, 5, 5, 5)
        
        self._sparklines_label = QLabel("Select items in navigator to view sparklines")
        self._sparklines_label.setAlignment(Qt.AlignCenter)
        self._sparklines_label.setStyleSheet("color: gray;")
        sparklines_layout.addWidget(self._sparklines_label)
        
        self._viz_tabs.addTab(sparklines_widget, "Sparklines")
        
        center_layout.addWidget(self._viz_tabs)
        
        main_splitter.addWidget(center_pane)
        
        # right pane - details
        right_pane = QWidget()
        right_pane.setMinimumWidth(280)
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        details_label = QLabel("Item Details")
        details_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        right_layout.addWidget(details_label)
        
        # details content
        self._details_frame = QFrame()
        self._details_frame.setFrameStyle(QFrame.StyledPanel)
        self._details_frame.setMinimumWidth(260)
        details_content = QVBoxLayout(self._details_frame)
        
        self._sku_label = QLabel("Select an item to view details")
        self._sku_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self._sku_label.setWordWrap(True)
        details_content.addWidget(self._sku_label)
        
        self._details_text = QLabel("")
        self._details_text.setWordWrap(True)
        self._details_text.setStyleSheet("color: #333;")
        details_content.addWidget(self._details_text)
        
        details_content.addStretch()
        
        # action buttons
        self._bookmark_btn = QPushButton("★ Bookmark")
        self._bookmark_btn.setCheckable(True)
        self._bookmark_btn.setEnabled(False)
        self._bookmark_btn.clicked.connect(self._toggle_bookmark)
        details_content.addWidget(self._bookmark_btn)
        
        self._flag_btn = QPushButton("⚠ Flag for Correction")
        self._flag_btn.setEnabled(False)
        self._flag_btn.setMinimumWidth(180)
        self._flag_btn.clicked.connect(self._flag_for_correction)
        details_content.addWidget(self._flag_btn)
        
        right_layout.addWidget(self._details_frame)
        
        # cluster summary
        right_layout.addWidget(self._create_cluster_summary())
        
        # anomaly summary
        right_layout.addWidget(self._create_anomaly_summary())
        
        main_splitter.addWidget(right_pane)
        
        # set splitter sizes - wider right pane
        main_splitter.setSizes([220, 480, 300])
        
        layout.addWidget(main_splitter)
        
        # bottom bar with proceed button
        bottom_layout = QHBoxLayout()
        
        self._status_label = QLabel("Load data and run clustering to discover patterns")
        self._status_label.setStyleSheet("color: gray;")
        bottom_layout.addWidget(self._status_label)
        
        bottom_layout.addStretch()
        
        self._proceed_btn = QPushButton("Proceed to Feature Engineering →")
        self._proceed_btn.setEnabled(False)
        self._proceed_btn.setMinimumHeight(40)
        self._proceed_btn.setStyleSheet(f"background-color: {config.UI_COLORS['primary']}; color: white; font-weight: bold;")
        self._proceed_btn.clicked.connect(self.proceed_requested.emit)
        bottom_layout.addWidget(self._proceed_btn)
        
        layout.addLayout(bottom_layout)
    
    def _create_cluster_summary(self) -> QGroupBox:
        # create cluster summary group
        group = QGroupBox("Cluster Summary")
        layout = QVBoxLayout(group)
        
        self._cluster_summary_label = QLabel("Run clustering to see summary")
        self._cluster_summary_label.setWordWrap(True)
        self._cluster_summary_label.setStyleSheet("color: gray;")
        layout.addWidget(self._cluster_summary_label)
        
        return group
    
    def _create_anomaly_summary(self) -> QGroupBox:
        # create anomaly summary group
        group = QGroupBox("Anomalies")
        layout = QVBoxLayout(group)
        
        self._anomaly_summary_label = QLabel("Run detection to find anomalies")
        self._anomaly_summary_label.setWordWrap(True)
        self._anomaly_summary_label.setStyleSheet("color: gray;")
        layout.addWidget(self._anomaly_summary_label)
        
        self._review_anomalies_btn = QPushButton("Review Anomalies")
        self._review_anomalies_btn.setEnabled(False)
        self._review_anomalies_btn.clicked.connect(self._show_anomaly_review)
        layout.addWidget(self._review_anomalies_btn)
        
        return group
    
    def _connect_signals(self) -> None:
        # connect widget signals
        self._navigator.sku_selected.connect(self._on_sku_selected)
        self._navigator.sku_double_clicked.connect(self._on_sku_double_clicked)
        self._navigator.bookmark_toggled.connect(self._on_bookmark_toggled)
        self._heatmap.cell_clicked.connect(self._on_heatmap_cell_clicked)
    
    # ---------- DATA LOADING ----------
    
    def set_processor(self, processor) -> None:
        # set data processor
        self._processor = processor
        self._refresh_navigator()
    
    def _refresh_navigator(self) -> None:
        # refresh navigator with current data
        if self._processor is None:
            return
        
        skus = self._processor.sku_list
        
        # create sku data dict
        sku_data = {}
        classification = self._processor.classify_skus()
        
        for tier, tier_skus in classification.items():
            for sku in tier_skus:
                sku_data[sku] = {"tier": tier}
        
        self._navigator.set_skus(skus, sku_data)
        
        # set categories
        cat_col = self._processor.get_mapped_column("category")
        if cat_col:
            df = self._processor.processed_data
            categories = {}
            for cat in df[cat_col].unique():
                sku_col = self._processor.get_mapped_column("sku")
                cat_skus = df[df[cat_col] == cat][sku_col].unique().tolist()
                categories[cat] = cat_skus
            self._navigator.set_categories(categories)
        
        self._status_label.setText(f"Loaded {len(skus):,} items - run clustering to discover patterns")
    
    # ---------- CLUSTERING ----------
    
    def _show_clustering_config(self) -> None:
        # show clustering configuration dialog
        dialog = ClusteringConfigDialog(self._clustering.config, self)
        dialog.config_changed.connect(self._on_clustering_config_changed)
        dialog.exec_()
    
    def _on_clustering_config_changed(self, new_config: Dict) -> None:
        # handle clustering config change
        self._clustering.config = new_config
        self._clustering.use_percentiles = new_config.get("use_percentiles", True)
    
    def _run_clustering(self) -> None:
        # run clustering on data
        if self._processor is None:
            QMessageBox.warning(self, "No Data", "Please load data first")
            return
        
        # show progress
        progress = ProgressDialog("Running Clustering", self)
        progress.set_status("Analyzing item patterns...")
        progress.set_indeterminate(True)
        progress.start()
        
        # get column names
        sku_col = self._processor.get_mapped_column("sku")
        date_col = self._processor.get_mapped_column("date")
        qty_col = self._processor.get_mapped_column("quantity")
        
        # store references for the worker
        data = self._processor.processed_data.copy()
        clustering = self._clustering
        
        # use SimpleWorker to avoid progress_callback injection
        self._worker = SimpleWorker(
            clustering.cluster_skus,
            data, sku_col, date_col, qty_col
        )
        self._worker.result_signal.connect(lambda r: self._on_clustering_complete(r, progress))
        self._worker.error_signal.connect(lambda e: self._on_clustering_error(e, progress))
        self._worker.start()
    
    def _on_clustering_complete(self, clusters: Dict, progress: ProgressDialog) -> None:
        # handle clustering complete
        progress.finish("Clustering complete")
        
        # update navigator with clusters
        self._navigator.set_clusters(clusters)
        
        # update heatmap
        self._heatmap.set_cluster_matrix(self._clustering.cluster_summary)
        
        # update summary
        summary = self._clustering.get_cluster_summary()
        summary_text = self._format_cluster_summary(summary)
        self._cluster_summary_label.setText(summary_text)
        self._cluster_summary_label.setStyleSheet("color: #333;")
        
        # update session
        self._session.set_clusters(clusters)
        
        # emit signal
        self.clusters_created.emit(clusters)
        
        # enable proceed
        self._proceed_btn.setEnabled(True)
        
        self._status_label.setText(f"Clustered {len(clusters):,} items into {len(summary)} groups")
    
    def _on_clustering_error(self, error: str, progress: ProgressDialog) -> None:
        # handle clustering error
        progress.finish(f"Error: {error}", auto_close=False)
        QMessageBox.critical(self, "Clustering Error", f"Failed to cluster:\n{error}")
    
    def _format_cluster_summary(self, summary: List[Dict]) -> str:
        # format cluster summary for display
        lines = []
        for s in summary[:6]:  # show top 6
            cluster = s["cluster"]
            count = s["item_count"]
            pct = s["pct_of_items"]
            lines.append(f"• {cluster}: {count:,} ({pct:.0f}%)")
        
        if len(summary) > 6:
            lines.append(f"... and {len(summary) - 6} more")
        
        return "\n".join(lines)
    
    # ---------- ANOMALY DETECTION ----------
    
    def _detect_anomalies(self) -> None:
        # detect anomalies in data
        if self._processor is None:
            QMessageBox.warning(self, "No Data", "Please load data first")
            return
        
        # show progress
        progress = ProgressDialog("Detecting Anomalies", self)
        progress.set_status("Scanning for unusual values...")
        progress.start()
        
        # get column names
        sku_col = self._processor.get_mapped_column("sku")
        date_col = self._processor.get_mapped_column("date")
        qty_col = self._processor.get_mapped_column("quantity")
        
        # store references
        data = self._processor.processed_data.copy()
        detector = self._anomaly_detector
        
        # run detection in background with progress callback
        def do_detection(progress_callback=None):
            return detector.detect_batch(
                data, sku_col, date_col, qty_col,
                progress_callback=progress_callback
            )
        
        self._worker = WorkerThread(do_detection)
        self._worker.progress_signal.connect(progress.set_progress)
        self._worker.result_signal.connect(lambda r: self._on_detection_complete(r, progress))
        self._worker.error_signal.connect(lambda e: self._on_detection_error(e, progress))
        self._worker.start()
    
    def _on_detection_complete(self, anomalies: Dict, progress: ProgressDialog) -> None:
        # handle detection complete
        progress.finish("Detection complete")
        
        # update session
        self._session.set_anomalies(anomalies)
        
        # update summary
        summary = self._anomaly_detector.get_summary()
        total = summary.get("total_anomalies", 0)
        skus_affected = summary.get("skus_with_anomalies", 0)
        
        if total > 0:
            by_type = summary.get("by_type", {})
            type_text = ", ".join([f"{v} {k}s" for k, v in by_type.items()])
            
            self._anomaly_summary_label.setText(
                f"Found {total:,} anomalies\n"
                f"in {skus_affected:,} items\n\n"
                f"{type_text}"
            )
            self._anomaly_summary_label.setStyleSheet("color: #c00;")
            self._review_anomalies_btn.setEnabled(True)
        else:
            self._anomaly_summary_label.setText("No anomalies detected ✓")
            self._anomaly_summary_label.setStyleSheet("color: green;")
            self._review_anomalies_btn.setEnabled(False)
        
        self._status_label.setText(f"Found {total:,} anomalies in {skus_affected:,} items")
    
    def _on_detection_error(self, error: str, progress: ProgressDialog) -> None:
        # handle detection error
        progress.finish(f"Error: {error}", auto_close=False)
        QMessageBox.critical(self, "Detection Error", f"Failed to detect anomalies:\n{error}")
    
    def _show_anomaly_review(self) -> None:
        # show anomaly review dialog
        playlist = self._anomaly_detector.get_anomaly_playlist(min_severity=0.3)
        
        if not playlist:
            QMessageBox.information(self, "No Anomalies", "No significant anomalies to review")
            return
        
        dialog = AnomalyReviewDialog(playlist, self)
        dialog.anomalies_actioned.connect(self._on_anomalies_actioned)
        dialog.navigate_to_sku.connect(self._navigate_to_sku)
        dialog.flag_for_correction.connect(self._on_flag_for_correction)
        dialog.exec_()

    def _on_flag_for_correction(self, sku: str) -> None:
        # handle flag for correction from anomaly dialog
        self.navigate_to_data.emit(sku)
    
    def _on_anomalies_actioned(self, actions: List) -> None:
        # handle anomaly actions
        # process actions
        flagged = [a for a, action in actions if action == "Flag"]
        
        if flagged:
            QMessageBox.information(
                self, 
                "Anomalies Flagged",
                f"{len(flagged)} anomalies flagged for correction.\n"
                "Switch to Data tab to review and fix."
            )
    
    def _navigate_to_sku(self, sku: str) -> None:
        # navigate to sku in chart
        self._navigator.select_sku(sku)
        self._on_sku_selected(sku)
    
    # ---------- SKU SELECTION ----------
    
    def _on_sku_selected(self, sku: str) -> None:
        # handle sku selection
        self._current_sku = sku
        
        # update details
        self._update_sku_details(sku)
        
        # update chart
        self._update_sku_chart(sku)
        
        # enable action buttons
        self._bookmark_btn.setEnabled(True)
        self._flag_btn.setEnabled(True)
        
        # check bookmark status
        self._bookmark_btn.setChecked(self._session.is_bookmarked(sku))
    
    def _on_sku_double_clicked(self, sku: str) -> None:
        # handle sku double click - jump to forecast
        self._on_sku_selected(sku)
        # could emit signal to switch to forecast tab
    
    def _update_sku_details(self, sku: str) -> None:
        # update sku details panel
        self._sku_label.setText(sku)
        
        details_parts = []
        
        # get cluster info
        cluster = self._clustering.get_cluster_for_sku(sku)
        if cluster:
            details_parts.append(f"<b>Cluster:</b> {cluster.cluster_label}")
            details_parts.append(f"<b>Volume Tier:</b> {config.CLUSTER_LABELS['volume'].get(cluster.volume_tier, cluster.volume_tier)}")
            details_parts.append(f"<b>Pattern:</b> {config.CLUSTER_LABELS['pattern'].get(cluster.pattern_type, cluster.pattern_type)}")
            details_parts.append(f"<b>Total Volume:</b> {cluster.total_volume:,.0f}")
            details_parts.append(f"<b>Variability (CV):</b> {cluster.cv:.2f}")
        
        # get anomaly info
        anomalies = self._session.get_anomalies().get(sku, [])
        if anomalies:
            details_parts.append(f"<b>Anomalies:</b> {len(anomalies)} detected")
        
        self._details_text.setText("<br>".join(details_parts))
    
    def _update_sku_chart(self, sku: str) -> None:
        # update chart with sku data
        if self._processor is None:
            return
        
        sku_data = self._processor.get_sku_data(sku)
        
        if sku_data.empty:
            self._chart.clear()
            return
        
        date_col = self._processor.get_mapped_column("date")
        qty_col = self._processor.get_mapped_column("quantity")
        
        dates = sku_data[date_col].tolist()
        values = sku_data[qty_col].tolist()
        
        self._chart.set_data(dates, values, label=sku)
        
        # add anomalies if detected
        anomalies = self._session.get_anomalies().get(sku, [])
        if anomalies:
            anomaly_data = [
                {"date": a.date, "value": a.value, "type": a.anomaly_type}
                for a in anomalies
            ]
            self._chart.set_anomalies(anomaly_data)
    
    # ---------- ACTIONS ----------
    
    def _toggle_bookmark(self) -> None:
        # toggle bookmark for current sku
        if self._current_sku is None:
            return
        
        if self._bookmark_btn.isChecked():
            self._session.add_bookmark(self._current_sku)
            self._navigator.add_bookmark(self._current_sku)
        else:
            self._session.remove_bookmark(self._current_sku)
            self._navigator.remove_bookmark(self._current_sku)
    
    def _on_bookmark_toggled(self, sku: str, bookmarked: bool) -> None:
        # handle bookmark toggle from navigator
        if bookmarked:
            self._session.add_bookmark(sku)
        else:
            self._session.remove_bookmark(sku)
        
        # update button if current sku
        if sku == self._current_sku:
            self._bookmark_btn.setChecked(bookmarked)
    
    def _flag_for_correction(self) -> None:
        # flag current sku for data correction
        if self._current_sku is None:
            return
        
        self.navigate_to_data.emit(self._current_sku)
        QMessageBox.information(
            self,
            "Flagged for Correction",
            f"Item '{self._current_sku}' has been flagged.\n"
            "Switch to Data tab to review and correct."
        )
    
    def _on_heatmap_cell_clicked(self, row_label: str, col_label: str) -> None:
        # handle heatmap cell click
        # filter navigator to show items in this cluster
        # map labels back to keys
        tier_map = {v: k for k, v in config.CLUSTER_LABELS["volume"].items()}
        pattern_map = {v: k for k, v in config.CLUSTER_LABELS["pattern"].items()}
        
        tier = tier_map.get(row_label, row_label)
        pattern = pattern_map.get(col_label, col_label)
        
        skus = self._clustering.get_skus_by_cluster(tier, pattern)
        
        if skus:
            self._status_label.setText(f"Showing {len(skus):,} items in {row_label} - {col_label}")
            # could filter navigator here
    
    # ---------- PUBLIC METHODS ----------
    
    def get_clustering(self) -> RuleClustering:
        # get clustering instance
        return self._clustering
    
    def refresh(self) -> None:
        # refresh tab data
        if self._processor:
            self._refresh_navigator()