"""
application state management
global state object
"""


# ================ IMPORTS ================

import threading
from config import AutoTSConfig


# ================ GLOBAL STATE ================

class AppState:
    """
    store application state
    hold dataframes and settings
    """
    def __init__(self):
        # ---------- DATA ----------
        self.raw_data = None
        self.clean_data = None
        self.forecast_data = None
        self.upper_forecast = None
        self.lower_forecast = None
        self.sku_list = []
        
        # ---------- COLUMNS ----------
        self.additional_columns = []
        self.column_mapping = {}
        
        # ---------- DATE FORMAT ----------
        self.detected_date_format = '%Y-%m-%d'
        self.original_date_format = None
        self.date_grouping = 'Daily'
        self.forecast_granularity = 'Daily'
        
        # ---------- FORECAST ----------
        self.forecast_days = AutoTSConfig.DEFAULT_FORECAST_DAYS
        self.is_forecasting = False
        self.cancel_forecast = threading.Event()
        self.loaded_model = None
        self.loaded_model_path = None
        
        # ---------- FORECAST RESULTS ----------
        self.skipped_skus = {}  # sku -> reason
        self.successful_skus = []
        
        # ---------- OUTPUT ----------
        self.custom_output_dir = None
        
        # ---------- FEATURES ----------
        self.use_features = False
        self.feature_columns = []
        self.selected_features = []
        self.exog_data = None
        self.encoders = None
        self.seasonality_info = {}
        
        # ---------- MULTI-COLUMN MAPPING ----------
        self.sku_feature_map = {}
        
        # ---------- SCENARIOS ----------
        self.scenario_history = []
        self.original_forecast = None
        self.original_upper = None
        self.original_lower = None
        
        # ---------- DASHBOARD ----------
        self.grouped_forecast = None
        self.error_margins = None
    
    def reset_forecast_state(self):
        """
        reset forecast related state
        """
        self.forecast_data = None
        self.upper_forecast = None
        self.lower_forecast = None
        self.grouped_forecast = None
        self.error_margins = None
        self.scenario_history = []
        self.original_forecast = None
        self.original_upper = None
        self.original_lower = None
        self.skipped_skus = {}
        self.successful_skus = []
    
    def reset_cancel_flag(self):
        """
        reset cancellation flag
        """
        self.cancel_forecast.clear()
    
    def request_cancel(self):
        """
        request forecast cancellation
        """
        self.cancel_forecast.set()
    
    def is_cancelled(self):
        """
        check if cancellation requested
        """
        return self.cancel_forecast.is_set()


# ---------- SINGLETON INSTANCE ----------
STATE = AppState()