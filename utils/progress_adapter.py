"""
Progress adapter for mapping backend progress callbacks to UI ProgressDialog
Provides a simple function `make_progress_callback(dialog)` which returns a callable
that accepts `(percent, text)` and updates the dialog accordingly.
"""
from typing import Callable, Optional


def make_progress_callback(dialog) -> Callable[[float, Optional[str]], None]:
    """Return a callback that updates the given dialog.

    Usage:
        cb = make_progress_callback(progress_dialog)
        cb(50, "processing sku")
    """

    def _cb(percent: float, text: Optional[str] = None):
        try:
            # allow single-arg calls where percent may be a dict/tuple
            if isinstance(percent, (tuple, list)) and len(percent) >= 1:
                percent = percent[0]

            p = int(percent)
            if hasattr(dialog, "set_progress"):
                dialog.set_progress(p)
            if text and hasattr(dialog, "set_status"):
                dialog.set_status(str(text))
        except Exception:
            # be resilient — progress updates must not raise
            return

    return _cb
