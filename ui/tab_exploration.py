"""
exploration tab with autoviz
time series plots, seasonality, anomaly detection
"""


# ================ IMPORTS ================

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QComboBox, QSpinBox,
    QGroupBox, QScrollArea, QFrame, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QListWidget, QListWidgetItem,
    QCheckBox, QSlider, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QPixmap, QImage

import base64
from io import BytesIO

from config import ExplorationConfig
from core.state import STATE
from core.exploration import EXPLORER
from core.bookmarks import BOOKMARKS, BookmarkType
from core.alerts import ALERTS


# ================ WORKER THREAD ================

class ExplorationWorker(QThread):
    """
    background worker for exploration
    """
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, task='autoviz', sku=None):
        super().__init__()
        self.task = task
        self.sku = sku
    
    def run(self):
        """
        run exploration task
        """
        def progress_callback(value, message):
            self.progress.emit(value, message)
        
        try:
            if self.task == 'autoviz':
                success = EXPLORER.run_autoviz(progress_callback=progress_callback)
            elif self.task == 'anomaly':
                if self.sku:
                    EXPLORER.detect_sku_anomalies(sku=self.sku)
                else:
                    EXPLORER.detect_all_anomalies(progress_callback=progress_callback)
                success = True
            elif self.task == 'decompose':
                EXPLORER.decompose_seasonality(sku=self.sku)
                success = True
            else:
                success = False
            
            if success:
                self.finished.emit(True, f"{self.task} complete")
            else:
                self.finished.emit(False, f"{self.task} failed")
                
        except Exception as e:
            self.finished.emit(False, str(e))


# ================ EXPLORATION TAB ================

class ExplorationTab(QWidget):
    """
    data exploration and visualization tab
    """
    
    anomaly_flagged = pyqtSignal(str, list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self._worker = None
        self._current_sku = None
        
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
        
        # ---------- SKU SEARCH ----------
        search_group = QGroupBox("SKU Selection")
        search_layout = QVBoxLayout(search_group)
        
        # search bar
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search SKUs...")
        search_layout.addWidget(self.txt_search)
        
        # sku list
        self.list_skus = QListWidget()
        self.list_skus.setMaximumHeight(200)
        search_layout.addWidget(self.list_skus)
        
        # bookmark button
        self.btn_bookmark_sku = QPushButton("Bookmark Selected")
        self.btn_bookmark_sku.setProperty("secondary", True)
        self.btn_bookmark_sku.setEnabled(False)
        search_layout.addWidget(self.btn_bookmark_sku)
        
        layout.addWidget(search_group)
        
        # ---------- VISUALIZATION ----------
        viz_group = QGroupBox("Visualization")
        viz_layout = QVBoxLayout(viz_group)
        
        # overlay options
        viz_layout.addWidget(QLabel("Overlays:"))
        self.chk_overlay_price = QCheckBox("Price")
        self.chk_overlay_promo = QCheckBox("Promotion")
        viz_layout.addWidget(self.chk_overlay_price)
        viz_layout.addWidget(self.chk_overlay_promo)
        
        # generate plot button
        self.btn_generate_plot = QPushButton("Generate Time Series")
        self.btn_generate_plot.setEnabled(False)
        viz_layout.addWidget(self.btn_generate_plot)
        
        # run autoviz
        self.btn_autoviz = QPushButton("Run AutoViz")
        self.btn_autoviz.setEnabled(False)
        viz_layout.addWidget(self.btn_autoviz)
        
        layout.addWidget(viz_group)
        
        # ---------- SEASONALITY ----------
        season_group = QGroupBox("Seasonality")
        season_layout = QVBoxLayout(season_group)
        
        # period selection
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("Period:"))
        self.spin_period = QSpinBox()
        self.spin_period.setRange(2, 365)
        self.spin_period.setValue(7)
        period_layout.addWidget(self.spin_period)
        season_layout.addLayout(period_layout)
        
        # decompose button
        self.btn_decompose = QPushButton("Decompose")
        self.btn_decompose.setEnabled(False)
        season_layout.addWidget(self.btn_decompose)
        
        layout.addWidget(season_group)
        
        # ---------- ANOMALY DETECTION ----------
        anomaly_group = QGroupBox("Anomaly Detection")
        anomaly_layout = QVBoxLayout(anomaly_group)
        
        # method selection
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("Method:"))
        self.combo_anomaly_method = QComboBox()
        self.combo_anomaly_method.addItems([
            'Isolation Forest',
            'Local Outlier Factor',
            'Z-Score',
            'IQR'
        ])
        method_layout.addWidget(self.combo_anomaly_method)
        anomaly_layout.addLayout(method_layout)
        
        # contamination slider
        contam_layout = QHBoxLayout()
        contam_layout.addWidget(QLabel("Sensitivity:"))
        self.slider_contamination = QSlider(Qt.Orientation.Horizontal)
        self.slider_contamination.setRange(1, 20)
        self.slider_contamination.setValue(5)
        contam_layout.addWidget(self.slider_contamination)
        self.lbl_contamination = QLabel("5%")
        contam_layout.addWidget(self.lbl_contamination)
        anomaly_layout.addLayout(contam_layout)
        
        # detect button
        self.btn_detect_anomalies = QPushButton("Detect Anomalies")
        self.btn_detect_anomalies.setEnabled(False)
        anomaly_layout.addWidget(self.btn_detect_anomalies)
        
        # detect all button
        self.btn_detect_all = QPushButton("Detect All SKUs")
        self.btn_detect_all.setProperty("secondary", True)
        self.btn_detect_all.setEnabled(False)
        anomaly_layout.addWidget(self.btn_detect_all)
        
        layout.addWidget(anomaly_group)
        
        # ---------- ANOMALY RESULTS ----------
        results_group = QGroupBox("Anomaly Results")
        results_layout = QVBoxLayout(results_group)
        
        self.lbl_anomaly_count = QLabel("No anomalies detected")
        self.lbl_anomaly_count.setStyleSheet("color: gray;")
        results_layout.addWidget(self.lbl_anomaly_count)
        
        # anomaly list
        self.list_anomalies = QListWidget()
        self.list_anomalies.setMaximumHeight(150)
        results_layout.addWidget(self.list_anomalies)
        
        # action buttons
        action_layout = QHBoxLayout()
        self.btn_flag_anomalies = QPushButton("Flag for Review")
        self.btn_flag_anomalies.setProperty("secondary", True)
        self.btn_flag_anomalies.setEnabled(False)
        action_layout.addWidget(self.btn_flag_anomalies)
        
        self.btn_bookmark_anomalies = QPushButton("Bookmark")
        self.btn_bookmark_anomalies.setProperty("secondary", True)
        self.btn_bookmark_anomalies.setEnabled(False)
        action_layout.addWidget(self.btn_bookmark_anomalies)
        results_layout.addLayout(action_layout)
        
        layout.addWidget(results_group)
        
        # ---------- PROGRESS ----------
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.lbl_status)
        
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
        
        # chart view
        chart_page = self._create_chart_page()
        self.stack.addWidget(chart_page)
        
        layout.addWidget(self.stack)
        
        return panel
    
    def _create_placeholder(self) -> QWidget:
        """
        create placeholder widget
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl = QLabel("Select a SKU and generate visualization")
        lbl.setStyleSheet("font-size: 18px; color: gray;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)
        
        return widget
    
    def _create_chart_page(self) -> QWidget:
        """
        create chart display page
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
    
    # ================ SIGNALS ================
    
    def _connect_signals(self):
        """
        connect widget signals
        """
        self.txt_search.textChanged.connect(self._on_search_changed)
        self.list_skus.currentRowChanged.connect(self._on_sku_selected)
        self.btn_bookmark_sku.clicked.connect(self._on_bookmark_sku)
        
        self.btn_generate_plot.clicked.connect(self._on_generate_plot)
        self.btn_autoviz.clicked.connect(self._on_run_autoviz)
        self.btn_decompose.clicked.connect(self._on_decompose)
        
        self.slider_contamination.valueChanged.connect(self._on_contamination_changed)
        self.btn_detect_anomalies.clicked.connect(self._on_detect_anomalies)
        self.btn_detect_all.clicked.connect(self._on_detect_all)
        
        self.list_anomalies.itemClicked.connect(self._on_anomaly_clicked)
        self.btn_flag_anomalies.clicked.connect(self._on_flag_anomalies)
        self.btn_bookmark_anomalies.clicked.connect(self._on_bookmark_anomalies)
    
    # ================ SLOTS ================
    
    def _on_search_changed(self, text: str):
        """
        filter sku list
        """
        self._populate_sku_list(text)
    
    def _on_sku_selected(self, row: int):
        """
        handle sku selection
        """
        if row < 0:
            self._current_sku = None
            self.btn_bookmark_sku.setEnabled(False)
            return
        
        item = self.list_skus.item(row)
        if item:
            self._current_sku = item.text()
            self.btn_bookmark_sku.setEnabled(True)
            self._update_anomaly_display()
    
    def _on_bookmark_sku(self):
        """
        bookmark selected sku
        """
        if self._current_sku:
            BOOKMARKS.bookmark_sku(self._current_sku)
            if self.main_window:
                self.main_window.set_status(f"Bookmarked: {self._current_sku}")
    
    def _on_generate_plot(self):
        """
        generate time series plot
        """
        if STATE.clean_data is None:
            return
        
        # get overlay columns
        overlays = []
        if self.chk_overlay_price.isChecked() and 'Price' in STATE.clean_data.columns:
            overlays.append('Price')
        if self.chk_overlay_promo.isChecked() and 'Promotion' in STATE.clean_data.columns:
            overlays.append('Promotion')
        
        # get anomalies for sku
        anomalies = STATE.anomalies.get(self._current_sku, {}) if self._current_sku else {}
        
        # generate plot
        img_base64 = EXPLORER.generate_time_series_plot(
            sku=self._current_sku,
            overlays=overlays if overlays else None,
            show_anomalies=True
        )
        
        if img_base64:
            self._display_chart(img_base64)
    
    def _on_run_autoviz(self):
        """
        run autoviz exploration
        """
        if STATE.clean_data is None:
            return
        
        self._start_worker('autoviz')
    
    def _on_decompose(self):
        """
        run seasonal decomposition
        """
        if STATE.clean_data is None:
            return
        
        period = self.spin_period.value()
        
        # run decomposition
        result = EXPLORER.decompose_seasonality(
            sku=self._current_sku,
            period=period
        )
        
        if 'error' not in result:
            # generate and display plot
            img_base64 = EXPLORER.generate_decomposition_plot(sku=self._current_sku)
            if img_base64:
                self._display_chart(img_base64)
        else:
            if self.main_window:
                self.main_window.set_status(f"Decomposition error: {result['error']}", True)
    
    def _on_contamination_changed(self, value: int):
        """
        update contamination label
        """
        self.lbl_contamination.setText(f"{value}%")
    
    def _on_detect_anomalies(self):
        """
        detect anomalies for selected sku
        """
        if STATE.clean_data is None or not self._current_sku:
            return
        
        method = self._get_anomaly_method()
        contamination = self.slider_contamination.value() / 100
        
        result = EXPLORER.detect_sku_anomalies(
            sku=self._current_sku,
            method=method,
            contamination=contamination
        )
        
        self._update_anomaly_display()
        
        # regenerate plot with anomalies
        self._on_generate_plot()
    
    def _on_detect_all(self):
        """
        detect anomalies for all skus
        """
        if STATE.clean_data is None:
            return
        
        self._start_worker('anomaly')
    
    def _on_anomaly_clicked(self, item: QListWidgetItem):
        """
        handle anomaly item click
        """
        self.btn_flag_anomalies.setEnabled(True)
        self.btn_bookmark_anomalies.setEnabled(True)
    
    def _on_flag_anomalies(self):
        """
        flag anomalies for review
        """
        if not self._current_sku:
            return
        
        anomalies = STATE.anomalies.get(self._current_sku, {})
        indices = anomalies.get('indices', [])
        
        if indices:
            EXPLORER.flag_anomalies(self._current_sku, indices)
            self.anomaly_flagged.emit(self._current_sku, indices)
            
            if self.main_window:
                self.main_window.set_status(f"Flagged {len(indices)} anomalies for review")
    
    def _on_bookmark_anomalies(self):
        """
        bookmark anomaly set
        """
        if not self._current_sku:
            return
        
        anomalies = STATE.anomalies.get(self._current_sku, {})
        indices = anomalies.get('indices', [])
        
        if indices:
            BOOKMARKS.bookmark_anomalies(
                name=f"Anomalies: {self._current_sku}",
                anomaly_ids=[f"{self._current_sku}_{i}" for i in indices]
            )
            
            if self.main_window:
                self.main_window.set_status("Anomaly set bookmarked")
    
    # ================ WORKER ================
    
    def _start_worker(self, task: str):
        """
        start background worker
        """
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText(f"Running {task}...")
        
        self._worker = ExplorationWorker(task=task, sku=self._current_sku)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()
    
    def _on_worker_progress(self, value: int, message: str):
        """
        handle worker progress
        """
        self.progress_bar.setValue(value)
        self.lbl_status.setText(message)
    
    def _on_worker_finished(self, success: bool, message: str):
        """
        handle worker complete
        """
        self.progress_bar.setVisible(False)
        self.lbl_status.setText(message)
        
        if success:
            if self.main_window:
                self.main_window.set_status(message)
            
            # update displays
            self._update_anomaly_display()
        else:
            if self.main_window:
                self.main_window.set_status(message, True)
    
    # ================ DISPLAY ================
    
    def _populate_sku_list(self, filter_text: str = ""):
        """
        populate sku list
        """
        self.list_skus.clear()
        
        if not STATE.sku_list:
            return
        
        filter_lower = filter_text.lower()
        
        for sku in STATE.sku_list:
            if filter_lower in str(sku).lower():
                self.list_skus.addItem(str(sku))
    
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
    
    def _update_anomaly_display(self):
        """
        update anomaly results display
        """
        self.list_anomalies.clear()
        
        if not self._current_sku:
            self.lbl_anomaly_count.setText("Select a SKU")
            return
        
        anomalies = STATE.anomalies.get(self._current_sku, {})
        count = anomalies.get('count', 0)
        
        if count == 0:
            self.lbl_anomaly_count.setText("No anomalies detected")
            self.lbl_anomaly_count.setStyleSheet("color: #4caf50;")
        else:
            self.lbl_anomaly_count.setText(f"{count} anomalies detected")
            self.lbl_anomaly_count.setStyleSheet("color: #ff9800;")
            
            # populate list
            dates = anomalies.get('dates', [])
            values = anomalies.get('values', [])
            
            for i, (date, value) in enumerate(zip(dates[:20], values[:20])):
                item = QListWidgetItem(f"{date}: {value:.2f}")
                self.list_anomalies.addItem(item)
            
            if count > 20:
                self.list_anomalies.addItem(f"... and {count - 20} more")
    
    def _get_anomaly_method(self) -> str:
        """
        get selected anomaly method
        """
        text = self.combo_anomaly_method.currentText()
        mapping = {
            'Isolation Forest': 'isolation_forest',
            'Local Outlier Factor': 'local_outlier_factor',
            'Z-Score': 'zscore',
            'IQR': 'iqr'
        }
        return mapping.get(text, 'isolation_forest')
    
    # ================ PUBLIC ================
    
    def on_tab_activated(self):
        """
        called when tab is activated
        """
        self._populate_sku_list()
        
        # enable buttons if data loaded
        has_data = STATE.clean_data is not None
        self.btn_generate_plot.setEnabled(has_data)
        self.btn_autoviz.setEnabled(has_data)
        self.btn_decompose.setEnabled(has_data)
        self.btn_detect_anomalies.setEnabled(has_data)
        self.btn_detect_all.setEnabled(has_data)
    
    def refresh(self):
        """
        refresh tab contents
        """
        self._populate_sku_list()
        self._update_anomaly_display()