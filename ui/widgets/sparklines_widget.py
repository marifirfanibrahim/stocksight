"""
sparklines widget module
displays multiple small time series charts
compact visualization for comparing skus
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QGridLayout, QPushButton,
    QComboBox, QSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPainter, QPen, QColor, QPainterPath
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

import config


# ============================================================================
#                          SPARKLINE ITEM
# ============================================================================

class SparklineItem(QWidget):
    # single sparkline with label
    
    # signals
    clicked = pyqtSignal(str)
    
    def __init__(self, sku: str, values: List[float], parent=None):
        # initialize sparkline item
        super().__init__(parent)
        
        self._sku = sku
        self._values = values
        self._selected = False
        self._hover = False
        
        self.setFixedHeight(50)
        self.setMinimumWidth(200)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        # setup user interface
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(10)
        
        # sku label
        self._label = QLabel(self._sku)
        self._label.setFixedWidth(100)
        self._label.setStyleSheet("font-weight: bold;")
        self._label.setToolTip(self._sku)
        layout.addWidget(self._label)
        
        # sparkline canvas
        self._canvas = SparklineCanvas(self._values)
        layout.addWidget(self._canvas, stretch=1)
        
        # stats
        if self._values:
            mean_val = np.mean(self._values)
            stats_text = f"{mean_val:,.0f}"
        else:
            stats_text = "--"
        
        self._stats_label = QLabel(stats_text)
        self._stats_label.setFixedWidth(60)
        self._stats_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._stats_label.setStyleSheet("color: #666;")
        layout.addWidget(self._stats_label)
    
    def set_selected(self, selected: bool) -> None:
        # set selected state
        self._selected = selected
        self._update_style()
    
    def _update_style(self) -> None:
        # update widget style
        if self._selected:
            self.setStyleSheet(f"background-color: {config.UI_COLORS['primary']}20; border-radius: 4px;")
        elif self._hover:
            self.setStyleSheet("background-color: #f0f0f0; border-radius: 4px;")
        else:
            self.setStyleSheet("")
    
    def enterEvent(self, event) -> None:
        # handle mouse enter
        self._hover = True
        self._update_style()
    
    def leaveEvent(self, event) -> None:
        # handle mouse leave
        self._hover = False
        self._update_style()
    
    def mousePressEvent(self, event) -> None:
        # handle mouse press
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._sku)
    
    def get_sku(self) -> str:
        # get sku
        return self._sku


# ============================================================================
#                         SPARKLINE CANVAS
# ============================================================================

class SparklineCanvas(QWidget):
    # canvas for drawing sparkline
    
    def __init__(self, values: List[float], parent=None):
        # initialize canvas
        super().__init__(parent)
        
        self._values = values
        self._color = QColor(config.UI_COLORS["primary"])
        self._fill_color = QColor(config.UI_COLORS["primary"])
        self._fill_color.setAlpha(50)
        
        self.setMinimumHeight(30)
        self.setMinimumWidth(80)
    
    def set_values(self, values: List[float]) -> None:
        # set values and redraw
        self._values = values
        self.update()
    
    def set_color(self, color: str) -> None:
        # set line color
        self._color = QColor(color)
        self._fill_color = QColor(color)
        self._fill_color.setAlpha(50)
        self.update()
    
    def paintEvent(self, event) -> None:
        # paint sparkline
        if not self._values or len(self._values) < 2:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # get dimensions
        width = self.width()
        height = self.height()
        padding = 2
        
        # calculate scaling
        min_val = min(self._values)
        max_val = max(self._values)
        val_range = max_val - min_val if max_val != min_val else 1
        
        # calculate points
        points = []
        for i, val in enumerate(self._values):
            x = padding + (i / (len(self._values) - 1)) * (width - 2 * padding)
            y = height - padding - ((val - min_val) / val_range) * (height - 2 * padding)
            points.append((x, y))
        
        # draw filled area
        path = QPainterPath()
        path.moveTo(points[0][0], height - padding)
        for x, y in points:
            path.lineTo(x, y)
        path.lineTo(points[-1][0], height - padding)
        path.closeSubpath()
        
        painter.fillPath(path, self._fill_color)
        
        # draw line
        pen = QPen(self._color)
        pen.setWidth(2)
        painter.setPen(pen)
        
        for i in range(len(points) - 1):
            painter.drawLine(
                int(points[i][0]), int(points[i][1]),
                int(points[i+1][0]), int(points[i+1][1])
            )
        
        # draw end point
        if points:
            last_x, last_y = points[-1]
            painter.setBrush(self._color)
            painter.drawEllipse(int(last_x) - 3, int(last_y) - 3, 6, 6)


# ============================================================================
#                         SPARKLINES WIDGET
# ============================================================================

class SparklinesWidget(QWidget):
    # widget displaying multiple sparklines
    
    # signals
    sku_selected = pyqtSignal(str)
    sku_double_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None):
        # initialize widget
        super().__init__(parent)
        
        self._sparklines = {}
        self._selected_sku = None
        self._data = {}
        
        self._setup_ui()
    
    # ---------- UI SETUP ----------
    
    def _setup_ui(self) -> None:
        # setup user interface
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # header
        header = QHBoxLayout()
        
        header.addWidget(QLabel("Sparklines"))
        
        header.addStretch()
        
        # sort options
        header.addWidget(QLabel("Sort:"))
        self._sort_combo = QComboBox()
        self._sort_combo.addItems(["By Name", "By Volume (High)", "By Volume (Low)", "By Trend"])
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        header.addWidget(self._sort_combo)
        
        # max items
        header.addWidget(QLabel("Show:"))
        self._max_items_spin = QSpinBox()
        self._max_items_spin.setRange(5, 100)
        self._max_items_spin.setValue(20)
        self._max_items_spin.setSuffix(" items")
        self._max_items_spin.valueChanged.connect(self._refresh_display)
        header.addWidget(self._max_items_spin)
        
        layout.addLayout(header)
        
        # scroll area for sparklines
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(2)
        self._container_layout.addStretch()
        
        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll)
        
        # placeholder
        self._placeholder = QLabel("Select items in navigator or run clustering to view sparklines")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet("color: gray; padding: 20px;")
        layout.addWidget(self._placeholder)
        
        self._scroll.setVisible(False)
    
    # ---------- DATA MANAGEMENT ----------
    
    def set_data(self, data: Dict[str, List[float]]) -> None:
        # set sparkline data
        self._data = data
        self._refresh_display()
    
    def set_data_from_dataframe(self, 
                                 df: pd.DataFrame, 
                                 sku_col: str, 
                                 date_col: str, 
                                 value_col: str,
                                 skus: Optional[List[str]] = None) -> None:
        # set data from dataframe
        data = {}
        
        # filter skus if provided
        if skus:
            df = df[df[sku_col].isin(skus)]
        
        # group by sku and get values
        for sku, group in df.groupby(sku_col):
            sorted_group = group.sort_values(date_col)
            values = sorted_group[value_col].tolist()
            data[sku] = values
        
        self.set_data(data)
    
    def clear(self) -> None:
        # clear all sparklines
        self._data = {}
        self._clear_sparklines()
        self._placeholder.setVisible(True)
        self._scroll.setVisible(False)
    
    def _clear_sparklines(self) -> None:
        # remove all sparkline widgets
        for sku, item in self._sparklines.items():
            item.setParent(None)
            item.deleteLater()
        self._sparklines = {}
    
    # ---------- DISPLAY ----------
    
    def _refresh_display(self) -> None:
        # refresh sparkline display
        self._clear_sparklines()
        
        if not self._data:
            self._placeholder.setVisible(True)
            self._scroll.setVisible(False)
            return
        
        self._placeholder.setVisible(False)
        self._scroll.setVisible(True)
        
        # sort data
        sorted_skus = self._get_sorted_skus()
        
        # limit items
        max_items = self._max_items_spin.value()
        display_skus = sorted_skus[:max_items]
        
        # create sparklines
        for sku in display_skus:
            values = self._data.get(sku, [])
            item = SparklineItem(sku, values)
            item.clicked.connect(self._on_sparkline_clicked)
            
            # insert before stretch
            self._container_layout.insertWidget(self._container_layout.count() - 1, item)
            self._sparklines[sku] = item
        
        # update selection
        if self._selected_sku and self._selected_sku in self._sparklines:
            self._sparklines[self._selected_sku].set_selected(True)
    
    def _get_sorted_skus(self) -> List[str]:
        # get skus sorted by current option
        sort_option = self._sort_combo.currentText()
        
        if sort_option == "By Name":
            return sorted(self._data.keys())
        
        elif sort_option == "By Volume (High)":
            return sorted(self._data.keys(), key=lambda s: sum(self._data[s]), reverse=True)
        
        elif sort_option == "By Volume (Low)":
            return sorted(self._data.keys(), key=lambda s: sum(self._data[s]))
        
        elif sort_option == "By Trend":
            # sort by trend direction
            def get_trend(sku):
                values = self._data[sku]
                if len(values) < 2:
                    return 0
                first_half = np.mean(values[:len(values)//2])
                second_half = np.mean(values[len(values)//2:])
                return second_half - first_half
            
            return sorted(self._data.keys(), key=get_trend, reverse=True)
        
        return list(self._data.keys())
    
    # ---------- SELECTION ----------
    
    def select_sku(self, sku: str) -> None:
        # select sku
        # deselect previous
        if self._selected_sku and self._selected_sku in self._sparklines:
            self._sparklines[self._selected_sku].set_selected(False)
        
        # select new
        self._selected_sku = sku
        if sku in self._sparklines:
            self._sparklines[sku].set_selected(True)
            # scroll to item
            self._scroll.ensureWidgetVisible(self._sparklines[sku])
    
    def get_selected_sku(self) -> Optional[str]:
        # get selected sku
        return self._selected_sku
    
    # ---------- EVENTS ----------
    
    def _on_sparkline_clicked(self, sku: str) -> None:
        # handle sparkline click
        self.select_sku(sku)
        self.sku_selected.emit(sku)
    
    def _on_sort_changed(self) -> None:
        # handle sort change
        self._refresh_display()
    
    # ---------- STYLING ----------
    
    def set_sparkline_color(self, sku: str, color: str) -> None:
        # set color for specific sparkline
        if sku in self._sparklines:
            self._sparklines[sku]._canvas.set_color(color)
    
    def set_colors_by_tier(self, tier_mapping: Dict[str, str]) -> None:
        # set colors based on tier
        tier_colors = {
            "A": "#81C784",  # green
            "B": "#FFD54F",  # yellow
            "C": "#E57373"   # red
        }
        
        for sku, tier in tier_mapping.items():
            color = tier_colors.get(tier, config.UI_COLORS["primary"])
            self.set_sparkline_color(sku, color)