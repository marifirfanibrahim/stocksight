"""
Central theme manager for StockSight.
Provides functions to apply theme, high-contrast, text size and compact mode.
"""
from typing import Optional
from PyQt5.QtWidgets import QApplication
import config


_HC_QSS = """
QWidget { background-color: #000000; color: #FFFFFF; }
QPushButton { background-color: #222222; color: #FFFFFF; border: 1px solid #FFFFFF; }
QTableWidget { background-color: #000000; color: #FFFFFF; gridline-color: #444444; }
"""


def _load_qss(path) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except Exception:
        return None


def apply_theme(name: str) -> None:
    """Apply a named theme. Supported: 'light', 'dark', 'system'.

    This will attempt to load a corresponding qss file from `config.STYLES_DIR`.
    If none exists, it will clear the stylesheet for 'light' or leave unchanged.
    """
    app = QApplication.instance()
    if not app:
        return

    name = (name or "").lower()
    if name == "dark":
        path = config.STYLES_DIR / "dark.qss"
        qss = _load_qss(path)
        if qss:
            app.setStyleSheet(qss)
        else:
            # fallback: try main.qss and hope it supports dark
            path2 = config.STYLES_DIR / "main.qss"
            qss2 = _load_qss(path2)
            if qss2:
                app.setStyleSheet(qss2)
    elif name == "light" or name == "system" or not name:
        # clear stylesheet to use native look (or main qss if provided)
        path = config.STYLES_DIR / "main.qss"
        qss = _load_qss(path)
        if qss:
            app.setStyleSheet(qss)
        else:
            app.setStyleSheet("")
    else:
        # unknown, clear
        app.setStyleSheet("")


def apply_high_contrast(enabled: bool) -> None:
    app = QApplication.instance()
    if not app:
        return
    if enabled:
        app.setStyleSheet(_HC_QSS)
    else:
        # re-apply currently selected theme if present
        apply_theme(config.DEFAULT_THEME)


def apply_text_size(size: int) -> None:
    app = QApplication.instance()
    if not app:
        return
    try:
        font = app.font()
        font.setPointSize(max(8, int(size)))
        app.setFont(font)
    except Exception:
        pass


def apply_compact_mode(enabled: bool) -> None:
    app = QApplication.instance()
    if not app:
        return
    if enabled:
        # small compact stylesheet to reduce paddings and margins
        compact_qss = """
        QWidget { padding: 2px; margin: 0px; }
        QPushButton { padding: 4px 6px; }
        QGroupBox { margin-top: 6px; }
        """
        app.setStyleSheet((app.styleSheet() or "") + compact_qss)
    else:
        # re-apply base theme
        apply_theme(config.DEFAULT_THEME)


def apply_preferences(session_model) -> None:
    try:
        if session_model is None:
            return
        theme = session_model.get_preference("theme", config.DEFAULT_THEME)
        text_size = session_model.get_preference("text_size", config.UI_SETTINGS.get("default_text_size", 12))
        high_contrast = session_model.get_preference("high_contrast", False)
        compact = session_model.get_preference("compact_mode", False)

        apply_theme(theme)
        apply_text_size(int(text_size) if text_size is not None else config.UI_SETTINGS.get("default_text_size", 12))
        if high_contrast:
            apply_high_contrast(True)
        if compact:
            apply_compact_mode(True)
    except Exception:
        pass
