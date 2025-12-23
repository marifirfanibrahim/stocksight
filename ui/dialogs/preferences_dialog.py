"""
Preferences dialog
Allows users to choose Theme and Compact mode
"""
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton


class PreferencesDialog(QDialog):
    """Preferences were removed — keep a small dialog to inform users.

    This dialog is intentionally minimal and only informs that Preferences
    are no longer available in the UI.
    """
    def __init__(self, session=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Preferences have been removed. Use the application defaults."))
        btn = QPushButton("OK")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
