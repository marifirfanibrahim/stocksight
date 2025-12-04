"""
welcome dialog module
shows welcome screen with workflow summary
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QWidget, QScrollArea
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import config


# ============================================================================
#                          WELCOME DIALOG
# ============================================================================

class WelcomeDialog(QDialog):
    # welcome dialog showing workflow summary
    
    def __init__(self, parent=None):
        # initialize dialog
        super().__init__(parent)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        # setup user interface
        self.setWindowTitle(f"Welcome to {config.APP_NAME}")
        self.setMinimumSize(560, 520)
        self.setMaximumSize(700, 650)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(35, 25, 35, 25)
        
        # app name
        name_label = QLabel(config.APP_NAME)
        name_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet(f"color: {config.UI_COLORS['primary']};")
        layout.addWidget(name_label)
        
        # tagline
        tagline = QLabel("Demand Forecasting for Business Analysts")
        tagline.setFont(QFont("Segoe UI", 11))
        tagline.setAlignment(Qt.AlignCenter)
        tagline.setStyleSheet("color: #666;")
        layout.addWidget(tagline)
        
        # separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #ddd;")
        layout.addWidget(line)
        
        # workflow header
        workflow_header = QLabel("How It Works")
        workflow_header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout.addWidget(workflow_header)
        
        # scroll area for steps
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(8)
        
        # workflow steps
        steps = [
            (
                "1", 
                "Data Health", 
                "Upload your data file (CSV, Excel, or Parquet). "
                "We'll auto-detect columns and check data quality."
            ),
            (
                "2", 
                "Pattern Discovery", 
                "Explore your items grouped by volume and sales patterns. "
                "Review any anomalies detected."
            ),
            (
                "3", 
                "Feature Engineering", 
                "Create smart features that help predict demand. "
                "Defaults work for most cases."
            ),
            (
                "4", 
                "Forecast Factory", 
                "Generate forecasts at daily, weekly, or monthly level. "
                "Export to CSV, Excel, or PowerPoint."
            )
        ]
        
        for num, title, desc in steps:
            step_widget = self._create_step_widget(num, title, desc)
            scroll_layout.addWidget(step_widget)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, stretch=1)
        
        # time estimate
        time_label = QLabel("⏱ Complete workflow in under 30 minutes for 10,000+ items")
        time_label.setAlignment(Qt.AlignCenter)
        time_label.setWordWrap(True)
        time_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(time_label)
        
        # separator
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("background-color: #ddd;")
        layout.addWidget(line2)
        
        # start button
        start_btn = QPushButton("Let's Start")
        start_btn.setMinimumHeight(45)
        start_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {config.UI_COLORS['primary']};
                color: white;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #3A9CC0;
            }}
        """)
        start_btn.clicked.connect(self.accept)
        layout.addWidget(start_btn)
    
    def _create_step_widget(self, num: str, title: str, desc: str) -> QWidget:
        # create single step widget
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(12)
        
        # step number circle
        num_label = QLabel(num)
        num_label.setFixedSize(28, 28)
        num_label.setAlignment(Qt.AlignCenter)
        num_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        num_label.setStyleSheet(f"""
            QLabel {{
                background-color: {config.UI_COLORS['primary']};
                color: white;
                border-radius: 14px;
            }}
        """)
        layout.addWidget(num_label, alignment=Qt.AlignTop)
        
        # text container
        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        text_layout.addWidget(title_label)
        
        desc_label = QLabel(desc)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #555; font-size: 9pt;")
        desc_label.setMinimumWidth(350)
        text_layout.addWidget(desc_label)
        
        layout.addLayout(text_layout, stretch=1)
        
        return widget