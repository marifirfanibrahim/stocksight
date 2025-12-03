"""
alert and notification system
manage alerts across application
"""


# ================ IMPORTS ================

import json
import threading
from typing import Callable, Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from core.state import STATE, Alert, AlertSeverity
from config import Paths, AlertConfig


# ================ ALERT MANAGER ================

class AlertManager:
    """
    centralized alert management
    """
    
    def __init__(self):
        # ---------- CALLBACKS ----------
        self._callbacks: List[Callable] = []
        
        # ---------- LOCK ----------
        self._lock = threading.RLock()
        
        # ---------- LOAD PERSISTED ALERTS ----------
        self._load_alerts()
    
    # ================ ALERT CREATION ================
    
    def create_alert(
        self,
        alert_type: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.MEDIUM,
        source_tab: str = "",
        related_skus: List[str] = None
    ) -> str:
        """
        create new alert and notify listeners
        """
        with self._lock:
            alert_id = STATE.add_alert(
                alert_type=alert_type,
                severity=severity,
                message=message,
                source_tab=source_tab,
                related_skus=related_skus
            )
            
            self._notify_callbacks('created', alert_id)
            self._save_alerts()
            
            return alert_id
    
    def create_anomaly_alert(self, sku: str, anomaly_count: int, source_tab: str = "exploration"):
        """
        create alert for detected anomalies
        """
        severity = AlertSeverity.LOW
        if anomaly_count > 10:
            severity = AlertSeverity.MEDIUM
        if anomaly_count > 50:
            severity = AlertSeverity.HIGH
        
        return self.create_alert(
            alert_type='anomaly',
            message=f"Detected {anomaly_count} anomalies in SKU: {sku}",
            severity=severity,
            source_tab=source_tab,
            related_skus=[sku]
        )
    
    def create_data_quality_alert(self, issue: str, affected_rows: int):
        """
        create alert for data quality issues
        """
        severity = AlertSeverity.MEDIUM
        if affected_rows > 1000:
            severity = AlertSeverity.HIGH
        
        return self.create_alert(
            alert_type='data_quality',
            message=f"Data quality issue: {issue} ({affected_rows} rows affected)",
            severity=severity,
            source_tab='data_quality'
        )
    
    def create_model_drift_alert(self, model_name: str, drift_score: float):
        """
        create alert for model drift
        """
        severity = AlertSeverity.MEDIUM
        if drift_score > 0.3:
            severity = AlertSeverity.HIGH
        if drift_score > 0.5:
            severity = AlertSeverity.CRITICAL
        
        return self.create_alert(
            alert_type='model_drift',
            message=f"Model drift detected in {model_name}: {drift_score:.2%}",
            severity=severity,
            source_tab='forecasting'
        )
    
    def create_info_alert(self, message: str, source_tab: str = ""):
        """
        create informational alert
        """
        return self.create_alert(
            alert_type='info',
            message=message,
            severity=AlertSeverity.LOW,
            source_tab=source_tab
        )
    
    # ================ ALERT MANAGEMENT ================
    
    def dismiss(self, alert_id: str):
        """
        dismiss alert by id
        """
        with self._lock:
            STATE.dismiss_alert(alert_id)
            self._notify_callbacks('dismissed', alert_id)
            self._save_alerts()
    
    def dismiss_all(self):
        """
        dismiss all alerts
        """
        with self._lock:
            for alert in STATE.alerts:
                alert.dismissed = True
            self._notify_callbacks('dismissed_all', None)
            self._save_alerts()
    
    def dismiss_by_type(self, alert_type: str):
        """
        dismiss all alerts of specific type
        """
        with self._lock:
            for alert in STATE.alerts:
                if alert.alert_type == alert_type:
                    alert.dismissed = True
            self._notify_callbacks('dismissed_type', alert_type)
            self._save_alerts()
    
    def delete_old_alerts(self, days: int = None):
        """
        delete alerts older than specified days
        """
        if days is None:
            days = AlertConfig.AUTO_DISMISS_DAYS
        
        cutoff = datetime.now() - timedelta(days=days)
        
        with self._lock:
            STATE.alerts = [a for a in STATE.alerts if a.created_at > cutoff or not a.dismissed]
            self._save_alerts()
    
    # ================ QUERIES ================
    
    def get_all(self, include_dismissed: bool = False) -> List[Alert]:
        """
        get all alerts
        """
        return STATE.get_alerts(include_dismissed)
    
    def get_by_type(self, alert_type: str, include_dismissed: bool = False) -> List[Alert]:
        """
        get alerts by type
        """
        alerts = STATE.get_alerts(include_dismissed)
        return [a for a in alerts if a.alert_type == alert_type]
    
    def get_by_severity(self, severity: AlertSeverity, include_dismissed: bool = False) -> List[Alert]:
        """
        get alerts by severity
        """
        alerts = STATE.get_alerts(include_dismissed)
        return [a for a in alerts if a.severity == severity]
    
    def get_by_sku(self, sku: str, include_dismissed: bool = False) -> List[Alert]:
        """
        get alerts related to specific sku
        """
        alerts = STATE.get_alerts(include_dismissed)
        return [a for a in alerts if sku in a.related_skus]
    
    def get_count(self) -> int:
        """
        get count of active alerts
        """
        return STATE.get_alert_count()
    
    def get_count_by_severity(self) -> Dict[AlertSeverity, int]:
        """
        get alert counts grouped by severity
        """
        alerts = STATE.get_alerts(include_dismissed=False)
        counts = {s: 0 for s in AlertSeverity}
        
        for alert in alerts:
            counts[alert.severity] += 1
        
        return counts
    
    # ================ CALLBACKS ================
    
    def add_callback(self, callback: Callable):
        """
        add callback for alert changes
        callback receives action type and alert_id
        """
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """
        remove callback
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self, action: str, alert_id: Optional[str]):
        """
        notify all callbacks
        """
        for callback in self._callbacks:
            try:
                callback(action, alert_id)
            except Exception as e:
                print(f"alert callback error: {e}")
    
    # ================ PERSISTENCE ================
    
    def _save_alerts(self):
        """
        save alerts to file
        """
        try:
            alerts_data = []
            
            for alert in STATE.alerts:
                alerts_data.append({
                    'id': alert.id,
                    'alert_type': alert.alert_type,
                    'severity': alert.severity.value,
                    'message': alert.message,
                    'created_at': alert.created_at.isoformat(),
                    'dismissed': alert.dismissed,
                    'source_tab': alert.source_tab,
                    'related_skus': alert.related_skus
                })
            
            Paths.DATA_DIR.mkdir(parents=True, exist_ok=True)
            
            with open(Paths.ALERTS_FILE, 'w') as f:
                json.dump(alerts_data, f, indent=2)
                
        except Exception as e:
            print(f"error saving alerts: {e}")
    
    def _load_alerts(self):
        """
        load alerts from file
        """
        try:
            if not Paths.ALERTS_FILE.exists():
                return
            
            with open(Paths.ALERTS_FILE, 'r') as f:
                alerts_data = json.load(f)
            
            STATE.alerts = []
            
            for data in alerts_data:
                alert = Alert(
                    id=data['id'],
                    alert_type=data['alert_type'],
                    severity=AlertSeverity(data['severity']),
                    message=data['message'],
                    created_at=datetime.fromisoformat(data['created_at']),
                    dismissed=data.get('dismissed', False),
                    source_tab=data.get('source_tab', ''),
                    related_skus=data.get('related_skus', [])
                )
                STATE.alerts.append(alert)
                
        except Exception as e:
            print(f"error loading alerts: {e}")


# ================ SINGLETON INSTANCE ================

ALERTS = AlertManager()