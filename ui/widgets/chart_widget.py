"""
chart display widget
embed matplotlib charts in pyqt
"""


# ================ IMPORTS ================

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QSizePolicy, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QImage

import base64
from pathlib import Path


# ================ CHART WIDGET ================

class ChartWidget(QWidget):
    """
    widget for displaying charts with zoom and export
    """
    
    chart_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._pixmap = None
        self._zoom_level = 1.0
        self._min_zoom = 0.25
        self._max_zoom = 4.0
        
        self._create_ui()
        self._connect_signals()
    
    # ================ UI ================
    
    def _create_ui(self):
        """
        create widget ui
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # ---------- TOOLBAR ----------
        toolbar = QHBoxLayout()
        toolbar.setSpacing(5)
        
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedSize(30, 30)
        self.btn_zoom_in.setToolTip("Zoom In")
        toolbar.addWidget(self.btn_zoom_in)
        
        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_out.setFixedSize(30, 30)
        self.btn_zoom_out.setToolTip("Zoom Out")
        toolbar.addWidget(self.btn_zoom_out)
        
        self.btn_zoom_fit = QPushButton("Fit")
        self.btn_zoom_fit.setFixedSize(40, 30)
        self.btn_zoom_fit.setToolTip("Fit to Window")
        toolbar.addWidget(self.btn_zoom_fit)
        
        self.btn_zoom_100 = QPushButton("100%")
        self.btn_zoom_100.setFixedSize(50, 30)
        self.btn_zoom_100.setToolTip("Actual Size")
        toolbar.addWidget(self.btn_zoom_100)
        
        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setFixedWidth(50)
        toolbar.addWidget(self.lbl_zoom)
        
        toolbar.addStretch()
        
        self.btn_export = QPushButton("Export")
        self.btn_export.setToolTip("Export Chart")
        toolbar.addWidget(self.btn_export)
        
        layout.addLayout(toolbar)
        
        # ---------- SCROLL AREA ----------
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # chart label
        self.chart_label = QLabel()
        self.chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chart_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.chart_label.setScaledContents(False)
        
        self.scroll_area.setWidget(self.chart_label)
        layout.addWidget(self.scroll_area)
        
        # ---------- PLACEHOLDER ----------
        self._show_placeholder()
    
    def _connect_signals(self):
        """
        connect signals
        """
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        self.btn_zoom_fit.clicked.connect(self._zoom_fit)
        self.btn_zoom_100.clicked.connect(self._zoom_100)
        self.btn_export.clicked.connect(self._export_chart)
        
        self.chart_label.mousePressEvent = self._on_chart_clicked
    
    # ================ PUBLIC METHODS ================
    
    def set_chart(self, img_base64: str):
        """
        set chart from base64 encoded image
        """
        try:
            img_data = base64.b64decode(img_base64)
            img = QImage()
            img.loadFromData(img_data)
            
            self._pixmap = QPixmap.fromImage(img)
            self._update_display()
            
        except Exception as e:
            print(f"chart load error: {e}")
            self._show_placeholder(f"Error: {e}")
    
    def set_pixmap(self, pixmap: QPixmap):
        """
        set chart from pixmap
        """
        self._pixmap = pixmap
        self._update_display()
    
    def load_from_file(self, file_path: str) -> bool:
        """
        load chart from file
        """
        try:
            self._pixmap = QPixmap(file_path)
            
            if self._pixmap.isNull():
                self._show_placeholder("Failed to load image")
                return False
            
            self._update_display()
            return True
            
        except Exception as e:
            print(f"file load error: {e}")
            self._show_placeholder(f"Error: {e}")
            return False
    
    def clear(self):
        """
        clear chart display
        """
        self._pixmap = None
        self._zoom_level = 1.0
        self._show_placeholder()
    
    def get_pixmap(self) -> QPixmap:
        """
        get current pixmap
        """
        return self._pixmap
    
    # ================ ZOOM ================
    
    def _zoom_in(self):
        """
        zoom in
        """
        self._zoom_level = min(self._zoom_level * 1.25, self._max_zoom)
        self._update_display()
    
    def _zoom_out(self):
        """
        zoom out
        """
        self._zoom_level = max(self._zoom_level / 1.25, self._min_zoom)
        self._update_display()
    
    def _zoom_fit(self):
        """
        fit to window
        """
        if self._pixmap is None:
            return
        
        viewport_size = self.scroll_area.viewport().size()
        pixmap_size = self._pixmap.size()
        
        width_ratio = viewport_size.width() / pixmap_size.width()
        height_ratio = viewport_size.height() / pixmap_size.height()
        
        self._zoom_level = min(width_ratio, height_ratio, 1.0)
        self._update_display()
    
    def _zoom_100(self):
        """
        zoom to 100%
        """
        self._zoom_level = 1.0
        self._update_display()
    
    def set_zoom(self, level: float):
        """
        set zoom level
        """
        self._zoom_level = max(min(level, self._max_zoom), self._min_zoom)
        self._update_display()
    
    # ================ DISPLAY ================
    
    def _update_display(self):
        """
        update chart display with current zoom
        """
        if self._pixmap is None:
            return
        
        # calculate scaled size
        scaled_size = self._pixmap.size() * self._zoom_level
        
        # scale pixmap
        scaled_pixmap = self._pixmap.scaled(
            scaled_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.chart_label.setPixmap(scaled_pixmap)
        self.chart_label.resize(scaled_pixmap.size())
        
        # update zoom label
        self.lbl_zoom.setText(f"{int(self._zoom_level * 100)}%")
    
    def _show_placeholder(self, message: str = "No chart to display"):
        """
        show placeholder text
        """
        self.chart_label.clear()
        self.chart_label.setText(message)
        self.chart_label.setStyleSheet("color: gray; font-size: 14px;")
        self.lbl_zoom.setText("--")
    
    # ================ EXPORT ================
    
    def _export_chart(self):
        """
        export chart to file
        """
        if self._pixmap is None:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Chart",
            "chart.png",
            "PNG (*.png);;JPEG (*.jpg);;All Files (*)"
        )
        
        if file_path:
            self._pixmap.save(file_path)
    
    # ================ EVENTS ================
    
    def _on_chart_clicked(self, event):
        """
        handle chart click
        """
        self.chart_clicked.emit()
    
    def wheelEvent(self, event):
        """
        handle mouse wheel for zoom
        """
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            
            if delta > 0:
                self._zoom_in()
            else:
                self._zoom_out()
            
            event.accept()
        else:
            super().wheelEvent(event)