"""
Progress dialog shim

This file intentionally re-exports the single canonical `ProgressDialog`
implementation from `ui.widgets.progress_dialog` so callers importing from
`ui.dialogs.progress_dialog` continue to work while avoiding duplicate
implementations.
"""

from ui.widgets.progress_dialog import ProgressDialog

__all__ = ["ProgressDialog"]