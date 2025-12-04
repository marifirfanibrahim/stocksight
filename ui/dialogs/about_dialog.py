"""
about dialog module
displays application information
shows version credits and links
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap

import config


# ============================================================================
#                           ABOUT DIALOG
# ============================================================================

class AboutDialog(QDialog):
    # about dialog showing application info
    
    def __init__(self, parent=None):
        # initialize dialog
        super().__init__(parent)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        # setup user interface
        self.setWindowTitle(f"About {config.APP_NAME}")
        self.setFixedSize(450, 350)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
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
        tagline.setStyleSheet("color: gray;")
        layout.addWidget(tagline)
        
        # version
        version_label = QLabel(f"Version {config.APP_VERSION}")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        # separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #ddd;")
        layout.addWidget(line)
        
        # description
        desc = QLabel(
            "StockSight helps Business Analysts create demand forecasts "
            "for thousands of SKUs without needing data science expertise.\n\n"
            "Features:\n"
            "• Smart column detection\n"
            "• Rule-based item clustering\n"
            "• Multiple forecasting strategies\n"
            "• Professional export formats"
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignLeft)
        layout.addWidget(desc)
        
        layout.addStretch()
        
        # separator
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("color: #ddd;")
        layout.addWidget(line2)
        
        # copyright
        copyright_label = QLabel(f"© 2025 {config.APP_AUTHOR}")
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(copyright_label)
        
        # close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)