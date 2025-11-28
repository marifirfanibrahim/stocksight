"""
application state management
global state object
"""


# ================ IMPORTS ================

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
        
        # ---------- DATE FORMAT ----------
        self.detected_date_format = '%Y-%m-%d'
        self.date_grouping = 'Daily'
        self.forecast_granularity = 'Daily'
        
        # ---------- FORECAST ----------
        self.forecast_days = AutoTSConfig.DEFAULT_FORECAST_DAYS
        self.is_forecasting = False
        
        # ---------- OUTPUT ----------
        self.custom_output_dir = None
        
        # ---------- FEATURES ----------
        self.use_features = False
        self.feature_columns = []
        self.selected_features = []
        self.exog_data = None
        self.encoders = None
        self.seasonality_info = {}
        
        # ---------- SCENARIOS ----------
        self.scenario_history = []
        
        # ---------- DASHBOARD ----------
        self.grouped_forecast = None
        self.error_margins = None


# ---------- SINGLETON INSTANCE ----------
STATE = AppState()