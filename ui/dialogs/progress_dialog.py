"""
progress dialog widget
shows progress for long running operations
supports cancellation
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QTextEdit, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
from typing import Optional
from datetime import datetime, timedelta

import config


# ============================================================================
#                          PROGRESS DIALOG
# ============================================================================

class ProgressDialog(QDialog):
    # dialog for showing operation progress
    
    # signals
    cancelled = pyqtSignal()
    
    def __init__(self, title: str = "Processing", parent=None):
        # initialize dialog
        super().__init__(parent)
        
        self._start_time = None
        self._is_cancelled = False
        self._auto_close = True
        
        self._setup_ui(title)
    
    # ---------- UI SETUP ----------
    
    def _setup_ui(self, title: str) -> None:
        # setup user interface
        self.setWindowTitle(title)
        self.setMinimumWidth(450)
        self.setMinimumHeight(200)
        self.setModal(True)
        
        # remove close button and help button
        self.setWindowFlags(
            self.windowFlags() 
            & ~Qt.WindowCloseButtonHint 
            & ~Qt.WindowContextHelpButtonHint
        )
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # title label
        self._title_label = QLabel(title)
        self._title_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout.addWidget(self._title_label)
        
        # status label
        self._status_label = QLabel("Initializing...")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)
        
        # progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        layout.addWidget(self._progress_bar)
        
        # time info
        time_layout = QHBoxLayout()
        
        self._elapsed_label = QLabel("Elapsed: 0:00")
        time_layout.addWidget(self._elapsed_label)
        
        time_layout.addStretch()
        
        self._remaining_label = QLabel("Remaining: --:--")
        time_layout.addWidget(self._remaining_label)
        
        layout.addLayout(time_layout)
        
        # details section
        self._details_frame = QFrame()
        self._details_frame.setFrameStyle(QFrame.StyledPanel)
        self._details_frame.setVisible(False)
        
        details_layout = QVBoxLayout(self._details_frame)
        
        self._details_text = QTextEdit()
        self._details_text.setReadOnly(True)
        self._details_text.setMaximumHeight(100)
        self._details_text.setFont(QFont("Consolas", 9))
        details_layout.addWidget(self._details_text)
        
        layout.addWidget(self._details_frame)
        
        # buttons
        button_layout = QHBoxLayout()
        
        self._details_btn = QPushButton("Show Details")
        self._details_btn.setCheckable(True)
        self._details_btn.clicked.connect(self._toggle_details)
        button_layout.addWidget(self._details_btn)
        
        button_layout.addStretch()
        
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self._on_cancel)
        button_layout.addWidget(self._cancel_btn)
        
        layout.addLayout(button_layout)
        
        # timer for elapsed time
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_time)
    
    # ---------- PUBLIC METHODS ----------
    
    def start(self) -> None:
        # start progress tracking
        self._start_time = datetime.now()
        self._is_cancelled = False
        self._timer.start(1000)
        self.show()
    
    def set_progress(self, value: int) -> None:
        # set progress value 0-100
        self._progress_bar.setValue(min(100, max(0, value)))
        self._update_remaining_time(value)
    
    def set_status(self, text: str) -> None:
        # set status text
        self._status_label.setText(text)
    
    def set_title(self, title: str) -> None:
        # set dialog title
        self._title_label.setText(title)
        self.setWindowTitle(title)
    
    def add_detail(self, text: str) -> None:
        # add detail line
        self._details_text.append(text)
        # auto scroll to bottom
        scrollbar = self._details_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def set_indeterminate(self, indeterminate: bool) -> None:
        # set indeterminate mode
        if indeterminate:
            self._progress_bar.setMaximum(0)
        else:
            self._progress_bar.setMaximum(100)
    
    def finish(self, message: str = "Complete", auto_close: bool = True) -> None:
        # finish progress
        self._timer.stop()
        self._progress_bar.setValue(100)
        self._status_label.setText(message)
        self._cancel_btn.setText("Close")
        self._remaining_label.setText("Remaining: 0:00")
        
        if auto_close and self._auto_close:
            QTimer.singleShot(1500, self.accept)
    
    def set_auto_close(self, auto_close: bool) -> None:
        # set auto close behavior
        self._auto_close = auto_close
    
    def is_cancelled(self) -> bool:
        # check if cancelled
        return self._is_cancelled
    
    # ---------- PRIVATE METHODS ----------
    
    def _toggle_details(self) -> None:
        # toggle details visibility
        visible = self._details_btn.isChecked()
        self._details_frame.setVisible(visible)
        self._details_btn.setText("Hide Details" if visible else "Show Details")
        
        # adjust dialog size
        if visible:
            self.setMinimumHeight(350)
        else:
            self.setMinimumHeight(200)
    
    def _on_cancel(self) -> None:
        # handle cancel button
        if self._progress_bar.value() >= 100:
            self.accept()
        else:
            self._is_cancelled = True
            self._status_label.setText("Cancelling...")
            self._cancel_btn.setEnabled(False)
            self.cancelled.emit()
    
    def _update_time(self) -> None:
        # update elapsed time display
        if self._start_time is None:
            return
        
        elapsed = datetime.now() - self._start_time
        minutes = int(elapsed.total_seconds() // 60)
        seconds = int(elapsed.total_seconds() % 60)
        self._elapsed_label.setText(f"Elapsed: {minutes}:{seconds:02d}")
    
    def _update_remaining_time(self, progress: int) -> None:
        # estimate remaining time
        if self._start_time is None or progress <= 0:
            return
        
        elapsed = (datetime.now() - self._start_time).total_seconds()
        
        if progress >= 100:
            self._remaining_label.setText("Remaining: 0:00")
            return
        
        # estimate total time
        total_estimated = elapsed / (progress / 100)
        remaining = total_estimated - elapsed
        
        if remaining > 0:
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            self._remaining_label.setText(f"Remaining: ~{minutes}:{seconds:02d}")
    
    # ---------- OVERRIDES ----------
    
    def closeEvent(self, event) -> None:
        # handle close event
        if self._progress_bar.value() < 100 and not self._is_cancelled:
            event.ignore()
        else:
            event.accept()
    
    def reject(self) -> None:
        # handle escape key
        if self._progress_bar.value() >= 100:
            super().reject()