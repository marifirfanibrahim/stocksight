"""
alert panel widget
display system alerts and notifications
"""


# ================ IMPORTS ================

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QAction

from typing import List, Optional
from datetime import datetime

from core.state import Alert, AlertSeverity
from core.alerts import ALERTS


# ================ ALERT ITEM ================

class AlertItem(QFrame):
    """
    single alert display item
    """
    
    dismissed = pyqtSignal(str)
    clicked = pyqtSignal(str)
    
    SEVERITY_COLORS = {
        AlertSeverity.LOW: '#4caf50',
        AlertSeverity.MEDIUM: '#ff9800',
        AlertSeverity.HIGH: '#f44336',
        AlertSeverity.CRITICAL: '#9c27b0'
    }
    
    SEVERITY_ICONS = {
        AlertSeverity.LOW: 'ℹ',
        AlertSeverity.MEDIUM: '⚠',
        AlertSeverity.HIGH: '⛔',
        AlertSeverity.CRITICAL: '🔴'
    }
    
    def __init__(self, alert: Alert, parent=None):
        super().__init__(parent)
        
        self._alert = alert
        self._create_ui()
    
    def _create_ui(self):
        """
        create item ui
        """
        color = self.SEVERITY_COLORS.get(self._alert.severity, '#808080')
        icon = self.SEVERITY_ICONS.get(self._alert.severity, 'ℹ')
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #252525;
                border-left: 4px solid {color};
                border-radius: 4px;
                padding: 8px;
            }}
            QFrame:hover {{
                background-color: #2d2d2d;
            }}
        """)
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        
        # icon
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet(f"font-size: 16px; color: {color};")
        layout.addWidget(lbl_icon)
        
        # content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)
        
        # message
        self.lbl_message = QLabel(self._alert.message)
        self.lbl_message.setWordWrap(True)
        content_layout.addWidget(self.lbl_message)
        
        # meta
        meta_parts = []
        
        if self._alert.source_tab:
            meta_parts.append(self._alert.source_tab)
        
        time_str = self._alert.created_at.strftime('%H:%M')
        meta_parts.append(time_str)
        
        lbl_meta = QLabel(' • '.join(meta_parts))
        lbl_meta.setStyleSheet("color: gray; font-size: 10px;")
        content_layout.addWidget(lbl_meta)
        
        layout.addLayout(content_layout, 1)
        
        # dismiss button
        btn_dismiss = QPushButton("×")
        btn_dismiss.setFixedSize(20, 20)
        btn_dismiss.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: gray;
                font-size: 16px;
            }
            QPushButton:hover {
                color: white;
            }
        """)
        btn_dismiss.clicked.connect(lambda: self.dismissed.emit(self._alert.id))
        layout.addWidget(btn_dismiss)
    
    def mousePressEvent(self, event):
        """
        handle click
        """
        self.clicked.emit(self._alert.id)
        super().mousePressEvent(event)
    
    def get_alert(self) -> Alert:
        """
        get alert object
        """
        return self._alert


# ================ ALERT PANEL ================

class AlertPanel(QWidget):
    """
    panel displaying all alerts
    """
    
    alert_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._alert_items = {}
        
        self._create_ui()
        self._connect_signals()
        self._refresh()
    
    def _create_ui(self):
        """
        create panel ui
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # ---------- HEADER ----------
        header_layout = QHBoxLayout()
        
        lbl_title = QLabel("Alerts")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        lbl_title.setFont(font)
        header_layout.addWidget(lbl_title)
        
        header_layout.addStretch()
        
        self.lbl_count = QLabel("0 alerts")
        self.lbl_count.setStyleSheet("color: gray;")
        header_layout.addWidget(self.lbl_count)
        
        self.btn_dismiss_all = QPushButton("Dismiss All")
        self.btn_dismiss_all.setProperty("secondary", True)
        self.btn_dismiss_all.clicked.connect(self._dismiss_all)
        header_layout.addWidget(self.btn_dismiss_all)
        
        layout.addLayout(header_layout)
        
        # ---------- FILTER ----------
        filter_layout = QHBoxLayout()
        
        self.btn_filter_all = QPushButton("All")
        self.btn_filter_all.setCheckable(True)
        self.btn_filter_all.setChecked(True)
        self.btn_filter_all.clicked.connect(lambda: self._set_filter(None))
        filter_layout.addWidget(self.btn_filter_all)
        
        self.btn_filter_high = QPushButton("High Priority")
        self.btn_filter_high.setCheckable(True)
        self.btn_filter_high.clicked.connect(
            lambda: self._set_filter([AlertSeverity.HIGH, AlertSeverity.CRITICAL])
        )
        filter_layout.addWidget(self.btn_filter_high)
        
        self.btn_filter_anomaly = QPushButton("Anomalies")
        self.btn_filter_anomaly.setCheckable(True)
        self.btn_filter_anomaly.clicked.connect(lambda: self._set_filter_type('anomaly'))
        filter_layout.addWidget(self.btn_filter_anomaly)
        
        filter_layout.addStretch()
        
        layout.addLayout(filter_layout)
        
        # ---------- ALERT LIST ----------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        self.alerts_layout = QVBoxLayout(scroll_content)
        self.alerts_layout.setContentsMargins(0, 0, 0, 0)
        self.alerts_layout.setSpacing(5)
        self.alerts_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # ---------- PLACEHOLDER ----------
        self.placeholder = QLabel("No alerts")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("color: gray; padding: 20px;")
    
    def _connect_signals(self):
        """
        connect signals
        """
        ALERTS.add_callback(self._on_alert_change)
    
    # ================ PUBLIC METHODS ================
    
    def refresh(self):
        """
        refresh alert list
        """
        self._refresh()
    
    def add_alert(self, alert: Alert):
        """
        add single alert
        """
        if alert.id in self._alert_items:
            return
        
        item = AlertItem(alert)
        item.dismissed.connect(self._on_alert_dismissed)
        item.clicked.connect(self.alert_clicked.emit)
        
        self._alert_items[alert.id] = item
        
        # insert at top
        self.alerts_layout.insertWidget(0, item)
        
        self._update_count()
    
    def remove_alert(self, alert_id: str):
        """
        remove alert by id
        """
        if alert_id in self._alert_items:
            item = self._alert_items.pop(alert_id)
            item.deleteLater()
        
        self._update_count()
    
    def clear(self):
        """
        clear all alerts
        """
        for item in self._alert_items.values():
            item.deleteLater()
        
        self._alert_items = {}
        self._update_count()
    
    # ================ SLOTS ================
    
    def _on_alert_change(self, action: str, alert_id: str):
        """
        handle alert system change
        """
        if action == 'created':
            alerts = ALERTS.get_all()
            for alert in alerts:
                if alert.id == alert_id:
                    self.add_alert(alert)
                    break
        elif action in ['dismissed', 'deleted']:
            self.remove_alert(alert_id)
        elif action in ['dismissed_all', 'cleared']:
            self._refresh()
    
    def _on_alert_dismissed(self, alert_id: str):
        """
        handle alert dismiss
        """
        ALERTS.dismiss(alert_id)
    
    def _dismiss_all(self):
        """
        dismiss all alerts
        """
        ALERTS.dismiss_all()
        self._refresh()
    
    def _set_filter(self, severities: List[AlertSeverity] = None):
        """
        set severity filter
        """
        # update button states
        self.btn_filter_all.setChecked(severities is None)
        self.btn_filter_high.setChecked(severities is not None)
        self.btn_filter_anomaly.setChecked(False)
        
        self._refresh(severity_filter=severities)
    
    def _set_filter_type(self, alert_type: str):
        """
        set type filter
        """
        # update button states
        self.btn_filter_all.setChecked(False)
        self.btn_filter_high.setChecked(False)
        self.btn_filter_anomaly.setChecked(True)
        
        self._refresh(type_filter=alert_type)
    
    # ================ HELPERS ================
    
    def _refresh(
        self,
        severity_filter: List[AlertSeverity] = None,
        type_filter: str = None
    ):
        """
        refresh alert list
        """
        # clear existing
        self.clear()
        
        # get alerts
        alerts = ALERTS.get_all()
        
        # apply filters
        if severity_filter:
            alerts = [a for a in alerts if a.severity in severity_filter]
        
        if type_filter:
            alerts = [a for a in alerts if a.alert_type == type_filter]
        
        # sort by date descending
        alerts.sort(key=lambda a: a.created_at, reverse=True)
        
        # add items
        for alert in alerts:
            self.add_alert(alert)
        
        # show placeholder if empty
        if not alerts:
            self.alerts_layout.insertWidget(0, self.placeholder)
        else:
            self.placeholder.setParent(None)
        
        self._update_count()
    
    def _update_count(self):
        """
        update count label
        """
        count = len(self._alert_items)
        self.lbl_count.setText(f"{count} alert{'s' if count != 1 else ''}")
        
        # update dismiss button
        self.btn_dismiss_all.setEnabled(count > 0)