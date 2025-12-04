"""
heatmap widget module
displays cluster and pattern heatmaps
visualizes sku distribution
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QHBoxLayout
from PyQt5.QtCore import pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import Dict, List, Optional

import config


# ============================================================================
#                           HEATMAP WIDGET
# ============================================================================

class HeatmapWidget(QWidget):
    # heatmap visualization widget
    
    # signals
    cell_clicked = pyqtSignal(str, str)  # row label, column label
    
    def __init__(self, parent=None):
        # initialize widget
        super().__init__(parent)
        
        self._data = None
        self._row_labels = []
        self._col_labels = []
        self._setup_ui()
    
    # ---------- UI SETUP ----------
    
    def _setup_ui(self) -> None:
        # setup user interface
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # header
        header = QHBoxLayout()
        self._title_label = QLabel("Cluster Distribution")
        self._title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header.addWidget(self._title_label)
        
        header.addStretch()
        
        # color scheme selector
        self._color_scheme = QComboBox()
        self._color_scheme.addItems(["Blues", "Greens", "YlOrRd", "viridis"])
        self._color_scheme.currentIndexChanged.connect(self._redraw)
        header.addWidget(QLabel("Colors:"))
        header.addWidget(self._color_scheme)
        
        layout.addLayout(header)
        
        # matplotlib figure
        self._figure = Figure(figsize=(8, 5), dpi=100)
        self._canvas = FigureCanvas(self._figure)
        
        # connect click event
        self._canvas.mpl_connect("button_press_event", self._on_click)
        
        layout.addWidget(self._canvas)
        
        # summary label
        self._summary_label = QLabel("")
        self._summary_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self._summary_label)
    
    # ---------- DATA MANAGEMENT ----------
    
    def set_data(self, data: np.ndarray, row_labels: List[str], col_labels: List[str]) -> None:
        # set heatmap data
        self._data = data
        self._row_labels = row_labels
        self._col_labels = col_labels
        self._redraw()
    
    def set_dataframe(self, df: pd.DataFrame) -> None:
        # set data from dataframe
        self._data = df.values
        self._row_labels = list(df.index)
        self._col_labels = list(df.columns)
        self._redraw()
    
    def set_cluster_matrix(self, cluster_data: Dict) -> None:
        # set data from cluster summary
        # expects dict with volume_tier and pattern counts
        tiers = ["A", "B", "C"]
        patterns = ["seasonal", "erratic", "variable", "steady"]
        
        matrix = np.zeros((len(tiers), len(patterns)))
        
        for (tier, pattern), info in cluster_data.items():
            if tier in tiers and pattern in patterns:
                row_idx = tiers.index(tier)
                col_idx = patterns.index(pattern)
                matrix[row_idx, col_idx] = info.get("sku_count", 0)
        
        # format labels
        tier_labels = [config.CLUSTER_LABELS["volume"].get(t, t) for t in tiers]
        pattern_labels = [config.CLUSTER_LABELS["pattern"].get(p, p) for p in patterns]
        
        self._data = matrix
        self._row_labels = tier_labels
        self._col_labels = pattern_labels
        self._redraw()
    
    def set_title(self, title: str) -> None:
        # set widget title
        self._title_label.setText(title)
    
    def clear(self) -> None:
        # clear heatmap
        self._data = None
        self._row_labels = []
        self._col_labels = []
        self._figure.clear()
        self._canvas.draw()
    
    # ---------- DRAWING ----------
    
    def _redraw(self) -> None:
        # redraw heatmap - clear entire figure and recreate
        self._figure.clear()
        
        if self._data is None or len(self._data) == 0:
            self._canvas.draw()
            return
        
        # create new axes
        self._ax = self._figure.add_subplot(111)
        
        # get colormap
        cmap = self._color_scheme.currentText()
        
        # create heatmap
        im = self._ax.imshow(self._data, cmap=cmap, aspect="auto")
        
        # set ticks and labels
        self._ax.set_xticks(np.arange(len(self._col_labels)))
        self._ax.set_yticks(np.arange(len(self._row_labels)))
        self._ax.set_xticklabels(self._col_labels)
        self._ax.set_yticklabels(self._row_labels)
        
        # rotate x labels
        plt.setp(self._ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
        
        # add value annotations
        for i in range(len(self._row_labels)):
            for j in range(len(self._col_labels)):
                value = self._data[i, j]
                
                # determine text color based on background
                threshold = (self._data.max() + self._data.min()) / 2
                text_color = "white" if value > threshold else "black"
                
                # format value
                if value == int(value):
                    text = f"{int(value)}"
                else:
                    text = f"{value:.1f}"
                
                self._ax.text(j, i, text, ha="center", va="center", color=text_color, fontsize=10)
        
        # add colorbar
        self._figure.colorbar(im, ax=self._ax, shrink=0.8)
        
        # tight layout
        self._figure.tight_layout()
        self._canvas.draw()
        
        # update summary
        self._update_summary()
    
    def _update_summary(self) -> None:
        # update summary label
        if self._data is None:
            self._summary_label.setText("")
            return
        
        total = self._data.sum()
        max_val = self._data.max()
        max_idx = np.unravel_index(self._data.argmax(), self._data.shape)
        
        if len(self._row_labels) > max_idx[0] and len(self._col_labels) > max_idx[1]:
            max_cell = f"{self._row_labels[max_idx[0]]} - {self._col_labels[max_idx[1]]}"
            self._summary_label.setText(f"Total: {total:.0f} | Largest: {max_cell} ({max_val:.0f})")
        else:
            self._summary_label.setText(f"Total: {total:.0f}")
    
    # ---------- INTERACTION ----------
    
    def _on_click(self, event) -> None:
        # handle click on heatmap cell
        if not hasattr(self, '_ax') or event.inaxes != self._ax:
            return
        
        if self._data is None:
            return
        
        # get cell coordinates
        col = int(round(event.xdata))
        row = int(round(event.ydata))
        
        # validate bounds
        if 0 <= row < len(self._row_labels) and 0 <= col < len(self._col_labels):
            row_label = self._row_labels[row]
            col_label = self._col_labels[col]
            self.cell_clicked.emit(row_label, col_label)
    
    # ---------- EXPORT ----------
    
    def save_figure(self, file_path: str, dpi: int = 150) -> bool:
        # save figure to file
        try:
            self._figure.savefig(file_path, dpi=dpi, bbox_inches="tight")
            return True
        except Exception:
            return False
    
    def get_figure(self) -> Figure:
        # get matplotlib figure
        return self._figure