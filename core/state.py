"""
application state management
global state object with pipeline tracking
"""


# ================ IMPORTS ================

import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from config import AutoTSConfig, PipelineConfig


# ================ ENUMS ================

class PipelineStage(Enum):
    """
    pipeline stage enumeration
    """
    IDLE = 'idle'
    DATA_QUALITY = 'data_quality'
    EXPLORATION = 'exploration'
    FEATURES = 'features'
    FORECASTING = 'forecasting'
    COMPLETE = 'complete'


class AlertSeverity(Enum):
    """
    alert severity levels
    """
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


# ================ DATA CLASSES ================

@dataclass
class CleaningState:
    """
    track cleaning operations for rollback
    """
    timestamp: datetime
    operation: str
    description: str
    data_snapshot: Any = None
    rows_affected: int = 0


@dataclass
class Bookmark:
    """
    bookmark for skus or anomaly sets
    """
    id: str
    name: str
    bookmark_type: str
    items: List[str]
    created_at: datetime
    notes: str = ""


@dataclass
class Alert:
    """
    system alert notification
    """
    id: str
    alert_type: str
    severity: AlertSeverity
    message: str
    created_at: datetime
    dismissed: bool = False
    source_tab: str = ""
    related_skus: List[str] = field(default_factory=list)


# ================ GLOBAL STATE ================

class AppState:
    """
    store application state
    hold dataframes, settings, pipeline status
    """
    
    def __init__(self):
        # ---------- LOCKS ----------
        self._lock = threading.RLock()
        
        # ---------- RAW DATA ----------
        self.raw_data = None
        self.clean_data = None
        self.original_data = None
        
        # ---------- SKU DATA ----------
        self.sku_list = []
        self.selected_skus = []
        
        # ---------- COLUMN MAPPING ----------
        self.column_mapping = {}
        self.additional_columns = []
        self.detected_date_format = '%Y-%m-%d'
        
        # ---------- PROFILING ----------
        self.profile_report = None
        self.profile_summary = {}
        self.data_quality_score = 0.0
        
        # ---------- CLEANING ----------
        self.cleaning_history: List[CleaningState] = []
        self.current_cleaning_index = -1
        
        # ---------- EXPLORATION ----------
        self.exploration_charts = {}
        self.seasonality_info = {}
        self.decomposition_results = {}
        
        # ---------- ANOMALIES ----------
        self.anomalies = {}
        self.flagged_anomalies = []
        self.anomaly_method = 'isolation_forest'
        
        # ---------- FEATURES ----------
        self.feature_data = None
        self.feature_importance = {}
        self.selected_features = []
        self.available_features = []
        self.feature_extraction_complete = False
        
        # ---------- FORECASTING ----------
        self.forecast_data = None
        self.upper_forecast = None
        self.lower_forecast = None
        self.forecast_days = AutoTSConfig.DEFAULT_FORECAST_DAYS
        self.forecast_granularity = 'Daily'
        self.forecast_speed = 'Fast'
        
        # ---------- MODELS ----------
        self.trained_models = {}
        self.model_metrics = {}
        self.selected_model = None
        self.loaded_model = None
        self.loaded_model_path = None
        
        # ---------- PIPELINE ----------
        self.pipeline_stage = PipelineStage.IDLE
        self.pipeline_progress = 0.0
        self.pipeline_message = ""
        
        # ---------- BOOKMARKS ----------
        self.bookmarks: List[Bookmark] = []
        
        # ---------- ALERTS ----------
        self.alerts: List[Alert] = []
        
        # ---------- PROCESSING FLAGS ----------
        self.is_processing = False
        self.cancel_flag = threading.Event()
        
        # ---------- SETTINGS ----------
        self.settings = {
            'dark_mode': True,
            'auto_advance': False,
            'auto_clean': False,
            'retrain_schedule': None,
            'api_endpoints': {}
        }
    
    # ================ THREAD SAFE OPERATIONS ================
    
    def set_data(self, raw_data, clean_data=None):
        """
        thread safe data setter
        """
        with self._lock:
            self.raw_data = raw_data
            self.clean_data = clean_data if clean_data is not None else raw_data.copy()
            self.original_data = raw_data.copy()
            
            if 'SKU' in self.clean_data.columns:
                self.sku_list = sorted(self.clean_data['SKU'].unique().tolist())
    
    def get_data(self):
        """
        thread safe data getter
        """
        with self._lock:
            return self.clean_data.copy() if self.clean_data is not None else None
    
    # ================ PIPELINE CONTROL ================
    
    def set_pipeline_stage(self, stage: PipelineStage, progress: float = 0.0, message: str = ""):
        """
        update pipeline stage
        """
        with self._lock:
            self.pipeline_stage = stage
            self.pipeline_progress = progress
            self.pipeline_message = message
    
    def get_pipeline_status(self):
        """
        get current pipeline status
        """
        with self._lock:
            return {
                'stage': self.pipeline_stage,
                'progress': self.pipeline_progress,
                'message': self.pipeline_message
            }
    
    def advance_pipeline(self):
        """
        advance to next pipeline stage
        """
        stage_order = [
            PipelineStage.IDLE,
            PipelineStage.DATA_QUALITY,
            PipelineStage.EXPLORATION,
            PipelineStage.FEATURES,
            PipelineStage.FORECASTING,
            PipelineStage.COMPLETE
        ]
        
        with self._lock:
            current_index = stage_order.index(self.pipeline_stage)
            if current_index < len(stage_order) - 1:
                self.pipeline_stage = stage_order[current_index + 1]
                self.pipeline_progress = 0.0
    
    # ================ CLEANING HISTORY ================
    
    def save_cleaning_state(self, operation: str, description: str):
        """
        save current state for rollback
        """
        with self._lock:
            # truncate future states if we branched
            if self.current_cleaning_index < len(self.cleaning_history) - 1:
                self.cleaning_history = self.cleaning_history[:self.current_cleaning_index + 1]
            
            state = CleaningState(
                timestamp=datetime.now(),
                operation=operation,
                description=description,
                data_snapshot=self.clean_data.copy() if self.clean_data is not None else None,
                rows_affected=len(self.clean_data) if self.clean_data is not None else 0
            )
            
            self.cleaning_history.append(state)
            self.current_cleaning_index = len(self.cleaning_history) - 1
            
            # limit history size
            from config import CleaningConfig
            if len(self.cleaning_history) > CleaningConfig.MAX_ROLLBACK_STATES:
                self.cleaning_history.pop(0)
                self.current_cleaning_index -= 1
    
    def rollback_cleaning(self, steps: int = 1):
        """
        rollback cleaning operations
        """
        with self._lock:
            target_index = max(0, self.current_cleaning_index - steps)
            
            if target_index < len(self.cleaning_history):
                state = self.cleaning_history[target_index]
                if state.data_snapshot is not None:
                    self.clean_data = state.data_snapshot.copy()
                    self.current_cleaning_index = target_index
                    return True
            
            return False
    
    def redo_cleaning(self, steps: int = 1):
        """
        redo cleaning operations
        """
        with self._lock:
            target_index = min(len(self.cleaning_history) - 1, self.current_cleaning_index + steps)
            
            if target_index < len(self.cleaning_history):
                state = self.cleaning_history[target_index]
                if state.data_snapshot is not None:
                    self.clean_data = state.data_snapshot.copy()
                    self.current_cleaning_index = target_index
                    return True
            
            return False
    
    # ================ BOOKMARKS ================
    
    def add_bookmark(self, name: str, bookmark_type: str, items: List[str], notes: str = ""):
        """
        add new bookmark
        """
        import uuid
        
        with self._lock:
            bookmark = Bookmark(
                id=str(uuid.uuid4()),
                name=name,
                bookmark_type=bookmark_type,
                items=items,
                created_at=datetime.now(),
                notes=notes
            )
            self.bookmarks.append(bookmark)
            return bookmark.id
    
    def remove_bookmark(self, bookmark_id: str):
        """
        remove bookmark by id
        """
        with self._lock:
            self.bookmarks = [b for b in self.bookmarks if b.id != bookmark_id]
    
    def get_bookmarks(self, bookmark_type: str = None):
        """
        get bookmarks optionally filtered by type
        """
        with self._lock:
            if bookmark_type:
                return [b for b in self.bookmarks if b.bookmark_type == bookmark_type]
            return self.bookmarks.copy()
    
    # ================ ALERTS ================
    
    def add_alert(self, alert_type: str, severity: AlertSeverity, message: str, 
                  source_tab: str = "", related_skus: List[str] = None):
        """
        add new alert
        """
        import uuid
        
        with self._lock:
            alert = Alert(
                id=str(uuid.uuid4()),
                alert_type=alert_type,
                severity=severity,
                message=message,
                created_at=datetime.now(),
                source_tab=source_tab,
                related_skus=related_skus or []
            )
            self.alerts.append(alert)
            
            # limit alerts
            from config import AlertConfig
            if len(self.alerts) > AlertConfig.MAX_ALERTS:
                # remove oldest dismissed first
                dismissed = [a for a in self.alerts if a.dismissed]
                if dismissed:
                    self.alerts.remove(dismissed[0])
                else:
                    self.alerts.pop(0)
            
            return alert.id
    
    def dismiss_alert(self, alert_id: str):
        """
        dismiss alert by id
        """
        with self._lock:
            for alert in self.alerts:
                if alert.id == alert_id:
                    alert.dismissed = True
                    break
    
    def get_alerts(self, include_dismissed: bool = False):
        """
        get alerts optionally including dismissed
        """
        with self._lock:
            if include_dismissed:
                return self.alerts.copy()
            return [a for a in self.alerts if not a.dismissed]
    
    def get_alert_count(self):
        """
        get count of active alerts
        """
        with self._lock:
            return len([a for a in self.alerts if not a.dismissed])
    
    # ================ SPEED CONFIG ================
    
    def get_speed_config(self):
        """
        get autots config based on speed setting
        """
        if self.forecast_speed == 'Superfast':
            return AutoTSConfig.SUPERFAST_MODE
        elif self.forecast_speed == 'Fast':
            return AutoTSConfig.FAST_MODE
        elif self.forecast_speed == 'Balanced':
            return AutoTSConfig.BALANCED_MODE
        elif self.forecast_speed == 'Accurate':
            return AutoTSConfig.ACCURATE_MODE
        else:
            return AutoTSConfig.FAST_MODE
    
    # ================ CANCELLATION ================
    
    def request_cancel(self):
        """
        request cancellation of current operation
        """
        self.cancel_flag.set()
    
    def reset_cancel(self):
        """
        reset cancellation flag
        """
        self.cancel_flag.clear()
    
    def is_cancelled(self):
        """
        check if cancellation requested
        """
        return self.cancel_flag.is_set()
    
    # ================ RESET ================
    
    def reset_all(self):
        """
        reset all state to initial values
        """
        with self._lock:
            self.__init__()
    
    def reset_forecast(self):
        """
        reset forecast related state
        """
        with self._lock:
            self.forecast_data = None
            self.upper_forecast = None
            self.lower_forecast = None
            self.trained_models = {}
            self.model_metrics = {}
            self.selected_model = None
    
    def reset_features(self):
        """
        reset feature related state
        """
        with self._lock:
            self.feature_data = None
            self.feature_importance = {}
            self.selected_features = []
            self.available_features = []
            self.feature_extraction_complete = False


# ================ SINGLETON INSTANCE ================

STATE = AppState()