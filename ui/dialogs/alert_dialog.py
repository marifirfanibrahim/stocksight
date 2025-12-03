"""
alert dialog
view and manage alerts
"""


# ================ IMPORTS ================

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton
)
from PyQt6.QtCore import Qt

from ui.widgets.alert_panel import AlertPanel


# ================ ALERT DIALOG ================

class AlertDialog(QDialog):
    """
    alert viewing dialog
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Alerts")
        self.setMinimumSize(500, 600)
        self.setModal(False)
        
        self._create_ui()
    
    def _create_ui(self):
        """
        create dialog ui
        """
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # alert panel
        self.alert_panel = AlertPanel()
        self.alert_panel.alert_clicked.connect(self._on_alert_clicked)
        layout.addWidget(self.alert_panel)
        
        # close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
    
    def _on_alert_clicked(self, alert_id: str):
        """
        handle alert click
        """
        pass
    
    def refresh(self):
        """
        refresh alerts
        """
        self.alert_panel.refresh()