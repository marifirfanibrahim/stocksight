"""
pipeline orchestration and status management
coordinate workflow between tabs
"""


# ================ IMPORTS ================

import threading
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from core.state import STATE, PipelineStage, AlertSeverity


# ================ PIPELINE STATUS ================

@dataclass
class StageStatus:
    """
    status of individual pipeline stage
    """
    stage: PipelineStage
    is_complete: bool = False
    is_active: bool = False
    progress: float = 0.0
    message: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class PipelineManager:
    """
    manage pipeline execution and status
    """
    
    def __init__(self):
        # ---------- STAGE STATUS ----------
        self._stages: Dict[PipelineStage, StageStatus] = {}
        self._initialize_stages()
        
        # ---------- CALLBACKS ----------
        self._progress_callbacks: List[Callable] = []
        self._stage_callbacks: List[Callable] = []
        self._error_callbacks: List[Callable] = []
        
        # ---------- LOCK ----------
        self._lock = threading.RLock()
    
    def _initialize_stages(self):
        """
        initialize all stage statuses
        """
        for stage in PipelineStage:
            if stage not in [PipelineStage.IDLE, PipelineStage.COMPLETE]:
                self._stages[stage] = StageStatus(stage=stage)
    
    # ================ STAGE MANAGEMENT ================
    
    def start_stage(self, stage: PipelineStage, message: str = ""):
        """
        mark stage as started
        """
        with self._lock:
            if stage in self._stages:
                self._stages[stage].is_active = True
                self._stages[stage].is_complete = False
                self._stages[stage].progress = 0.0
                self._stages[stage].message = message
                self._stages[stage].started_at = datetime.now()
                self._stages[stage].error = None
                
                STATE.set_pipeline_stage(stage, 0.0, message)
                self._notify_stage_change(stage)
    
    def update_progress(self, stage: PipelineStage, progress: float, message: str = ""):
        """
        update stage progress
        """
        with self._lock:
            if stage in self._stages:
                self._stages[stage].progress = min(max(progress, 0.0), 100.0)
                if message:
                    self._stages[stage].message = message
                
                STATE.set_pipeline_stage(stage, progress, message)
                self._notify_progress(stage, progress, message)
    
    def complete_stage(self, stage: PipelineStage, message: str = "Complete"):
        """
        mark stage as complete
        """
        with self._lock:
            if stage in self._stages:
                self._stages[stage].is_active = False
                self._stages[stage].is_complete = True
                self._stages[stage].progress = 100.0
                self._stages[stage].message = message
                self._stages[stage].completed_at = datetime.now()
                
                STATE.set_pipeline_stage(stage, 100.0, message)
                self._notify_stage_change(stage)
    
    def fail_stage(self, stage: PipelineStage, error: str):
        """
        mark stage as failed
        """
        with self._lock:
            if stage in self._stages:
                self._stages[stage].is_active = False
                self._stages[stage].is_complete = False
                self._stages[stage].error = error
                self._stages[stage].message = f"Error: {error}"
                
                STATE.add_alert(
                    alert_type='pipeline_error',
                    severity=AlertSeverity.HIGH,
                    message=f"Pipeline failed at {stage.value}: {error}",
                    source_tab=stage.value
                )
                
                self._notify_error(stage, error)
    
    def reset_stage(self, stage: PipelineStage):
        """
        reset stage to initial state
        """
        with self._lock:
            if stage in self._stages:
                self._stages[stage] = StageStatus(stage=stage)
    
    def reset_all(self):
        """
        reset all stages
        """
        with self._lock:
            self._initialize_stages()
            STATE.set_pipeline_stage(PipelineStage.IDLE, 0.0, "")
    
    # ================ STATUS QUERIES ================
    
    def get_stage_status(self, stage: PipelineStage) -> Optional[StageStatus]:
        """
        get status of specific stage
        """
        with self._lock:
            return self._stages.get(stage)
    
    def get_all_status(self) -> Dict[PipelineStage, StageStatus]:
        """
        get status of all stages
        """
        with self._lock:
            return self._stages.copy()
    
    def get_current_stage(self) -> PipelineStage:
        """
        get currently active stage
        """
        with self._lock:
            for stage, status in self._stages.items():
                if status.is_active:
                    return stage
            return PipelineStage.IDLE
    
    def get_completed_stages(self) -> List[PipelineStage]:
        """
        get list of completed stages
        """
        with self._lock:
            return [stage for stage, status in self._stages.items() if status.is_complete]
    
    def is_stage_available(self, stage: PipelineStage) -> bool:
        """
        check if stage can be started
        """
        # data quality always available if data loaded
        if stage == PipelineStage.DATA_QUALITY:
            return STATE.raw_data is not None
        
        # exploration requires clean data
        if stage == PipelineStage.EXPLORATION:
            return STATE.clean_data is not None
        
        # features requires exploration or clean data
        if stage == PipelineStage.FEATURES:
            return STATE.clean_data is not None
        
        # forecasting requires data
        if stage == PipelineStage.FORECASTING:
            return STATE.clean_data is not None
        
        return False
    
    def get_overall_progress(self) -> float:
        """
        get overall pipeline progress percentage
        """
        with self._lock:
            total_stages = len(self._stages)
            if total_stages == 0:
                return 0.0
            
            completed = sum(1 for s in self._stages.values() if s.is_complete)
            active_progress = sum(s.progress for s in self._stages.values() if s.is_active) / 100.0
            
            return ((completed + active_progress) / total_stages) * 100.0
    
    # ================ CALLBACKS ================
    
    def add_progress_callback(self, callback: Callable):
        """
        add callback for progress updates
        """
        self._progress_callbacks.append(callback)
    
    def add_stage_callback(self, callback: Callable):
        """
        add callback for stage changes
        """
        self._stage_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable):
        """
        add callback for errors
        """
        self._error_callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """
        remove callback from all lists
        """
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)
        if callback in self._stage_callbacks:
            self._stage_callbacks.remove(callback)
        if callback in self._error_callbacks:
            self._error_callbacks.remove(callback)
    
    def _notify_progress(self, stage: PipelineStage, progress: float, message: str):
        """
        notify progress callbacks
        """
        for callback in self._progress_callbacks:
            try:
                callback(stage, progress, message)
            except Exception as e:
                print(f"progress callback error: {e}")
    
    def _notify_stage_change(self, stage: PipelineStage):
        """
        notify stage change callbacks
        """
        for callback in self._stage_callbacks:
            try:
                callback(stage, self._stages.get(stage))
            except Exception as e:
                print(f"stage callback error: {e}")
    
    def _notify_error(self, stage: PipelineStage, error: str):
        """
        notify error callbacks
        """
        for callback in self._error_callbacks:
            try:
                callback(stage, error)
            except Exception as e:
                print(f"error callback error: {e}")


# ================ SINGLETON INSTANCE ================

PIPELINE = PipelineManager()