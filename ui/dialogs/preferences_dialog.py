"""
Preferences dialog
Allows users to choose Theme, High Contrast, Text Size, and Compact mode
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QCheckBox
)
from PyQt5.QtCore import Qt
import config
from ui.models.session_model import SessionModel
import ui.theme_manager as theme_manager


class PreferencesDialog(QDialog):
    def __init__(self, session: SessionModel, parent=None):
        super().__init__(parent)
        self._session = session
        self.setWindowTitle("Preferences")
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Theme selection
        layout.addWidget(QLabel("Theme:"))
        self._theme_combo = QComboBox()
        self._theme_combo.addItem("Light", "light")
        self._theme_combo.addItem("Dark", "dark")
        self._theme_combo.addItem("System", "system")
        cur_theme = self._session.get_preference("theme", config.DEFAULT_THEME)
        idx = self._theme_combo.findData(cur_theme)
        if idx >= 0:
            self._theme_combo.setCurrentIndex(idx)
        layout.addWidget(self._theme_combo)

        # Text size
        layout.addWidget(QLabel("Text size:"))
        self._text_combo = QComboBox()
        for s in config.UI_SETTINGS.get("text_size_options", [11, 12, 13, 14]):
            self._text_combo.addItem(str(s), s)
        cur_size = self._session.get_preference("text_size", config.UI_SETTINGS.get("default_text_size", 12))
        idx = self._text_combo.findData(int(cur_size))
        if idx >= 0:
            self._text_combo.setCurrentIndex(idx)
        layout.addWidget(self._text_combo)

        # High contrast
        self._hc_check = QCheckBox("High contrast theme")
        self._hc_check.setChecked(bool(self._session.get_preference("high_contrast", False)))
        layout.addWidget(self._hc_check)

        # Compact mode
        self._compact_check = QCheckBox("Compact mode (reduced spacing)")
        self._compact_check.setChecked(bool(self._session.get_preference("compact_mode", False)))
        layout.addWidget(self._compact_check)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok = QPushButton("OK")
        ok.clicked.connect(self._on_ok)
        btn_layout.addWidget(ok)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        btn_layout.addWidget(cancel)
        layout.addLayout(btn_layout)

    def _on_ok(self):
        theme = self._theme_combo.currentData()
        size = int(self._text_combo.currentData())
        hc = bool(self._hc_check.isChecked())
        compact = bool(self._compact_check.isChecked())

        try:
            self._session.set_preference("theme", theme)
            self._session.set_preference("text_size", size)
            self._session.set_preference("high_contrast", hc)
            self._session.set_preference("compact_mode", compact)
        except Exception:
            pass

        # apply immediately
        try:
            theme_manager.apply_preferences(self._session)
        except Exception:
            pass

        self.accept()
