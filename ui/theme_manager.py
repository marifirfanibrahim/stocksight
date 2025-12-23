"""
Theme manager removed: theming is simplified and Preferences have been removed.
This module remains as a no-op compatibility shim.
"""

def apply_theme(name: str) -> None:
    return


def apply_text_size(size: int) -> None:
    return


def apply_compact_mode(enabled: bool) -> None:
    return


def apply_preferences(session_model) -> None:
    return
