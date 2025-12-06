"""
help dialog module
displays help information for terminology
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QWidget, QFrame,
    QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import config


# ============================================================================
#                           HELP DIALOG
# ============================================================================

class ClusterHelpDialog(QDialog):
    # dialog explaining cluster terminology
    
    def __init__(self, parent=None):
        # initialize dialog
        super().__init__(parent)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        # setup user interface
        self.setWindowTitle("Cluster Terminology Help")
        self.setMinimumWidth(550)
        self.setMinimumHeight(500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # header
        header = QLabel("Understanding Cluster Types")
        header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(header)
        
        # scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)
        
        # volume tiers section
        scroll_layout.addWidget(self._create_section(
            "📊 Volume Tiers (ABC Classification)",
            [
                ("A - High Volume", 
                 "Top 20% of items by sales volume. These are your most important items "
                 "that typically account for 80% of total sales. They deserve the most "
                 "attention and detailed forecasting.",
                 "#4CAF50"),
                ("B - Medium Volume",
                 "Next 30% of items by sales volume. These items have moderate sales and "
                 "should be monitored regularly but don't need as much individual attention as A-items.",
                 "#FF9800"),
                ("C - Low Volume",
                 "Bottom 50% of items by sales volume. These items have lower sales and "
                 "can often be forecasted in bulk with simpler methods.",
                 "#F44336")
            ]
        ))
        
        # pattern types section
        scroll_layout.addWidget(self._create_section(
            "📈 Pattern Types",
            [
                ("Steady",
                 "Items with consistent, predictable demand. Coefficient of Variation (CV) < 0.3. "
                 "These items are easy to forecast and maintain stable inventory levels.",
                 "#4CAF50"),
                ("Variable",
                 "Items with moderate demand fluctuations. CV between 0.3 and 0.8. "
                 "These items need regular monitoring and may require safety stock adjustments.",
                 "#2196F3"),
                ("Erratic",
                 "Items with highly unpredictable demand. CV > 0.8. "
                 "These items are difficult to forecast and may need special handling, "
                 "such as make-to-order or higher safety stock.",
                 "#FF9800"),
                ("Seasonal",
                 "Items with strong seasonal patterns. Q4 concentration > 60%. "
                 "These items show significant demand spikes during certain periods "
                 "(like holidays) and need seasonal forecasting approaches.",
                 "#9C27B0")
            ]
        ))
        
        # metrics section
        scroll_layout.addWidget(self._create_section(
            "📏 Key Metrics",
            [
                ("CV (Coefficient of Variation)",
                 "Standard deviation divided by mean. Measures relative variability. "
                 "Lower CV means more stable demand.",
                 "#607D8B"),
                ("Q4 Concentration",
                 "Percentage of annual sales occurring in Q4 (Oct-Dec). "
                 "High concentration indicates holiday seasonality.",
                 "#607D8B"),
                ("MAPE (Mean Absolute Percentage Error)",
                 "Average forecast error as a percentage. Lower is better. "
                 "Under 10% is excellent, 10-20% is good, over 30% needs review.",
                 "#607D8B")
            ]
        ))
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_section(self, title: str, items: list) -> QGroupBox:
        # create help section
        from PyQt5.QtWidgets import QGroupBox
        
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        
        for name, description, color in items:
            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(4)
            
            # name with color indicator
            name_label = QLabel(f"● {name}")
            name_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
            name_label.setStyleSheet(f"color: {color};")
            item_layout.addWidget(name_label)
            
            # description
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #555; margin-left: 15px;")
            item_layout.addWidget(desc_label)
            
            layout.addWidget(item_widget)
        
        return group