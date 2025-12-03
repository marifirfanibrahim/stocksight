"""
progress panel widget
display operation progress with details
"""


# ================ IMPORTS ================

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QFrame, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from typing import Optional
from datetime import datetime, timedelta


# ================ PROGRESS PANEL ================

class ProgressPanel(QWidget):
    """
    progress display panel with timer and log
    """
    
    cancel_requested = pyqtSignal()
    
    def __init__(self, parent=None, show_log: bool = True):
        super().__init__(parent)
        
        self._show_log = show_log
        self._start_time = None
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_elapsed)
        
        self._create_ui()
    
    def _create_ui(self):
        """
        create widget ui
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # ---------- HEADER ----------
        header_frame = QFrame()
        header_frame.setProperty("card", True)
        header_layout = QVBoxLayout(header_frame)
        
        # title row
        title_row = QHBoxLayout()
        
        self.lbl_title = QLabel("Processing...")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.lbl_title.setFont(font)
        title_row.addWidget(self.lbl_title)
        
        title_row.addStretch()
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setProperty("secondary", True)
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        title_row.addWidget(self.btn_cancel)
        
        header_layout.addLayout(title_row)
        
        # progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        header_layout.addWidget(self.progress_bar)
        
        # status row
        status_row = QHBoxLayout()
        
        self.lbl_status = QLabel("Starting...")
        self.lbl_status.setStyleSheet("color: gray;")
        status_row.addWidget(self.lbl_status)
        
        status_row.addStretch()
        
        self.lbl_elapsed = QLabel("00:00")
        self.lbl_elapsed.setStyleSheet("color: gray; font-family: monospace;")
        status_row.addWidget(self.lbl_elapsed)
        
        header_layout.addLayout(status_row)
        
        layout.addWidget(header_frame)
        
        # ---------- LOG ----------
        if self._show_log:
            self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            self.log_text.setMaximumHeight(150)
            self.log_text.setStyleSheet("""
                QTextEdit {
                    font-family: monospace;
                    font-size: 10px;
                    background-color: #1a1a1a;
                    border: 1px solid #3d3d3d;
                    border-radius: 4px;
                }
            """)
            layout.addWidget(self.log_text)
    
    # ================ PUBLIC METHODS ================
    
    def start(self, title: str = "Processing..."):
        """
        start progress tracking
        """
        self._start_time = datetime.now()
        self._timer.start(1000)
        
        self.lbl_title.setText(title)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Starting...")
        self.lbl_elapsed.setText("00:00")
        
        if self._show_log:
            self.log_text.clear()
            self.log(f"Started: {self._start_time.strftime('%H:%M:%S')}")
        
        self.setVisible(True)
    
    def stop(self, success: bool = True, message: str = ""):
        """
        stop progress tracking
        """
        self._timer.stop()
        
        elapsed = self._get_elapsed()
        
        if success:
            self.progress_bar.setValue(100)
            self.lbl_status.setText(message or "Complete")
            self.log(f"Completed in {elapsed}")
        else:
            self.lbl_status.setText(message or "Failed")
            self.lbl_status.setStyleSheet("color: #f44336;")
            self.log(f"Failed: {message}")
    
    def update_progress(self, value: int, message: str = ""):
        """
        update progress value and message
        """
        self.progress_bar.setValue(value)
        
        if message:
            self.lbl_status.setText(message)
            self.log(message)
    
    def set_indeterminate(self, indeterminate: bool = True):
        """
        set indeterminate mode
        """
        if indeterminate:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
    
    def log(self, message: str):
        """
        add message to log
        """
        if self._show_log:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.append(f"[{timestamp}] {message}")
            
            # scroll to bottom
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def reset(self):
        """
        reset panel
        """
        self._timer.stop()
        self._start_time = None
        
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("")
        self.lbl_status.setStyleSheet("color: gray;")
        self.lbl_elapsed.setText("00:00")
        
        if self._show_log:
            self.log_text.clear()
    
    def hide_cancel(self):
        """
        hide cancel button
        """
        self.btn_cancel.setVisible(False)
    
    def show_cancel(self):
        """
        show cancel button
        """
        self.btn_cancel.setVisible(True)
    
    # ================ HELPERS ================
    
    def _update_elapsed(self):
        """
        update elapsed time display
        """
        self.lbl_elapsed.setText(self._get_elapsed())
    
    def _get_elapsed(self) -> str:
        """
        get formatted elapsed time
        """
        if self._start_time is None:
            return "00:00"
        
        elapsed = datetime.now() - self._start_time
        minutes = int(elapsed.total_seconds() // 60)
        seconds = int(elapsed.total_seconds() % 60)
        
        return f"{minutes:02d}:{seconds:02d}"


# ================ MINI PROGRESS ================

class MiniProgress(QWidget):
    """
    compact progress indicator
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(100)
        self.progress_bar.setMaximumHeight(16)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.lbl_status)
        
        self.setVisible(False)
    
    def start(self, message: str = ""):
        """
        start progress
        """
        self.progress_bar.setRange(0, 0)
        self.lbl_status.setText(message)
        self.setVisible(True)
    
    def update(self, value: int, message: str = ""):
        """
        update progress
        """
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(value)
        if message:
            self.lbl_status.setText(message)
    
    def stop(self):
        """
        stop and hide
        """
        self.setVisible(False)