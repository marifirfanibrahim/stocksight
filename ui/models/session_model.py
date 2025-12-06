"""
session model module
manages application session state
tracks workflow progress and data
"""

from PyQt5.QtCore import QObject, pyqtSignal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

import config


# ============================================================================
#                              DATA CLASSES
# ============================================================================

@dataclass
class SessionState:
    # current session state
    file_path: str = ""
    file_loaded: bool = False
    columns_mapped: bool = False
    data_cleaned: bool = False
    clusters_created: bool = False
    features_created: bool = False
    forecasts_generated: bool = False
    
    # data counts
    total_rows: int = 0
    total_skus: int = 0
    total_categories: int = 0
    
    # quality
    data_quality_score: float = 0.0
    
    # timing
    session_start: datetime = field(default_factory=datetime.now)
    last_action: datetime = field(default_factory=datetime.now)


# ============================================================================
#                            SESSION MODEL
# ============================================================================

class SessionModel(QObject):
    # manages session state and workflow
    
    # signals
    state_changed = pyqtSignal(str)  # emits changed property name
    data_loaded = pyqtSignal(dict)   # emits data summary
    workflow_updated = pyqtSignal(int)  # emits completed step
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent=None):
        # initialize session model
        super().__init__(parent)
        
        self.state = SessionState()
        self._data = None
        self._column_mapping = {}
        self._clusters = {}
        self._features = {}
        self._forecasts = {}
        self._anomalies = {}
        self._bookmarks = []
    
    # ---------- STATE MANAGEMENT ----------
    
    def reset(self) -> None:
        # reset session to initial state
        self.state = SessionState()
        self._data = None
        self._column_mapping = {}
        self._clusters = {}
        self._features = {}
        self._forecasts = {}
        self._anomalies = {}
        self._bookmarks = []
        self.state_changed.emit("reset")
    
    def update_state(self, **kwargs) -> None:
        # update state properties
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
                self.state_changed.emit(key)
        
        self.state.last_action = datetime.now()
    
    def get_workflow_step(self) -> int:
        # get current workflow step 0-4
        if not self.state.file_loaded:
            return 0
        if not self.state.columns_mapped:
            return 0
        if not self.state.data_cleaned:
            return 1
        if not self.state.clusters_created:
            return 1
        if not self.state.features_created:
            return 2
        if not self.state.forecasts_generated:
            return 3
        return 4
    
    def can_proceed_to_tab(self, tab_index: int) -> bool:
        # check if user can access tab
        current_step = self.get_workflow_step()
        
        if tab_index == 0:
            return True
        elif tab_index == 1:
            return self.state.data_cleaned
        elif tab_index == 2:
            return self.state.clusters_created
        elif tab_index == 3:
            return self.state.features_created
        
        return False
    
    # ---------- DATA MANAGEMENT ----------
    
    def set_data(self, data) -> None:
        # set loaded data
        self._data = data
        self.state.file_loaded = True
        
        if data is not None:
            self.state.total_rows = len(data)
    
    def get_data(self):
        # get loaded data
        return self._data
    
    def set_column_mapping(self, mapping: Dict[str, str]) -> None:
        # set column mapping
        self._column_mapping = mapping.copy()
        self.state.columns_mapped = True
        self.state_changed.emit("column_mapping")
    
    def get_column_mapping(self) -> Dict[str, str]:
        # get column mapping
        return self._column_mapping.copy()
    
    def set_clusters(self, clusters: Dict) -> None:
        # set clustering results
        self._clusters = clusters
        self.state.clusters_created = True
        self.state_changed.emit("clusters")
    
    def get_clusters(self) -> Dict:
        # get clustering results
        return self._clusters
    
    def set_features(self, features: Dict) -> None:
        # set feature engineering results
        self._features = features
        self.state.features_created = True
        self.state_changed.emit("features")
    
    def get_features(self) -> Dict:
        # get feature results
        return self._features
    
    def set_forecasts(self, forecasts: Dict) -> None:
        # set forecast results
        self._forecasts = forecasts
        self.state.forecasts_generated = True
        self.state_changed.emit("forecasts")
    
    def get_forecasts(self) -> Dict:
        # get forecast results
        return self._forecasts
    
    def set_anomalies(self, anomalies: Dict) -> None:
        # set anomaly detection results
        self._anomalies = anomalies
        self.state_changed.emit("anomalies")
    
    def get_anomalies(self) -> Dict:
        # get anomaly results
        return self._anomalies
    
    # ---------- BOOKMARKS ----------
    
    def add_bookmark(self, sku: str, note: str = "") -> None:
        # add sku to bookmarks
        bookmark = {
            "sku": sku,
            "note": note,
            "timestamp": datetime.now()
        }
        
        # avoid duplicates
        for b in self._bookmarks:
            if b["sku"] == sku:
                b["note"] = note
                return
        
        self._bookmarks.append(bookmark)
        self.state_changed.emit("bookmarks")
    
    def remove_bookmark(self, sku: str) -> None:
        # remove sku from bookmarks
        self._bookmarks = [b for b in self._bookmarks if b["sku"] != sku]
        self.state_changed.emit("bookmarks")
    
    def get_bookmarks(self) -> List[Dict]:
        # get all bookmarks
        return self._bookmarks.copy()
    
    def is_bookmarked(self, sku: str) -> bool:
        # check if sku is bookmarked
        return any(b["sku"] == sku for b in self._bookmarks)
    
    # ---------- SESSION INFO ----------
    
    def get_session_summary(self) -> Dict[str, Any]:
        # get summary of current session
        duration = datetime.now() - self.state.session_start
        
        return {
            "file": self.state.file_path,
            "rows": self.state.total_rows,
            "skus": self.state.total_skus,
            "categories": self.state.total_categories,
            "quality_score": self.state.data_quality_score,
            "workflow_step": self.get_workflow_step(),
            "forecasts_count": len(self._forecasts),
            "anomalies_count": sum(len(a) for a in self._anomalies.values()),
            "bookmarks_count": len(self._bookmarks),
            "duration_minutes": duration.total_seconds() / 60
        }
    
    def get_export_data(self) -> Dict[str, Any]:
        # get all data for export
        return {
            "session_summary": self.get_session_summary(),
            "column_mapping": self._column_mapping,
            "clusters": self._clusters,
            "forecasts": self._forecasts,
            "anomalies": self._anomalies,
            "bookmarks": self._bookmarks
        }