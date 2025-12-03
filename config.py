"""
application configuration
store settings and constants
manage paths and parameters
"""


# ================ IMPORTS ================

import os
from pathlib import Path


# ================ PATHS ================

class Paths:
    """
    directory and file paths
    """
    # ---------- BASE DIRECTORY ----------
    BASE_DIR = Path(__file__).parent.absolute()
    
    # ---------- DATA DIRECTORY ----------
    DATA_DIR = BASE_DIR / "data"
    
    # ---------- OUTPUT DIRECTORY ----------
    OUTPUT_DIR = BASE_DIR / "output"
    
    # ---------- CACHE DIRECTORY ----------
    CACHE_DIR = BASE_DIR / "cache"
    
    # ---------- MODELS DIRECTORY ----------
    MODELS_DIR = BASE_DIR / "models"
    
    # ---------- PROFILES DIRECTORY ----------
    PROFILES_DIR = OUTPUT_DIR / "profiles"
    
    # ---------- FEATURES DIRECTORY ----------
    FEATURES_DIR = OUTPUT_DIR / "features"
    
    # ---------- FORECASTS DIRECTORY ----------
    FORECASTS_DIR = OUTPUT_DIR / "forecasts"
    
    # ---------- USER DOCUMENTS ----------
    USER_DOCS = Path.home() / "Documents" / "Stocksight"
    USER_OUTPUT = USER_DOCS / "output"
    
    # ---------- DEFAULT FILES ----------
    DEFAULT_CSV = DATA_DIR / "inventory.csv"
    BOOKMARKS_FILE = DATA_DIR / "bookmarks.json"
    ALERTS_FILE = DATA_DIR / "alerts.json"
    SETTINGS_FILE = DATA_DIR / "settings.json"


# ================ WINDOW SETTINGS ================

class WindowConfig:
    """
    pyqt window settings
    """
    # ---------- MAIN WINDOW ----------
    TITLE = "Stocksight - Inventory Forecasting"
    WIDTH = 1600
    HEIGHT = 900
    MIN_WIDTH = 1200
    MIN_HEIGHT = 700
    
    # ---------- THEME ----------
    DARK_MODE = True
    
    # ---------- FONTS ----------
    FONT_FAMILY = "Segoe UI"
    FONT_SIZE_NORMAL = 10
    FONT_SIZE_HEADER = 14
    FONT_SIZE_TITLE = 18
    FONT_SIZE_SMALL = 8


# ================ PROFILING SETTINGS ================

class ProfilingConfig:
    """
    ydata profiling settings
    """
    # ---------- REPORT SETTINGS ----------
    TITLE = "Data Quality Report"
    MINIMAL = False
    EXPLORATIVE = True
    
    # ---------- SAMPLES ----------
    SAMPLE_SIZE = 10000
    SAMPLE_FOR_LARGE = True
    LARGE_THRESHOLD = 100000
    
    # ---------- CORRELATIONS ----------
    CORRELATION_THRESHOLD = 0.9
    
    # ---------- MISSING VALUES ----------
    MISSING_THRESHOLD = 0.05
    
    # ---------- DUPLICATES ----------
    CHECK_DUPLICATES = True
    
    # ---------- CACHE ----------
    CACHE_REPORTS = True


# ================ CLEANING SETTINGS ================

class CleaningConfig:
    """
    data cleaning settings
    """
    # ---------- IMPUTATION METHODS ----------
    IMPUTATION_METHODS = [
        'mean',
        'median',
        'mode',
        'forward_fill',
        'backward_fill',
        'interpolate',
        'zero',
        'drop'
    ]
    DEFAULT_IMPUTATION = 'forward_fill'
    
    # ---------- DUPLICATE HANDLING ----------
    DUPLICATE_METHODS = [
        'keep_first',
        'keep_last',
        'drop_all'
    ]
    DEFAULT_DUPLICATE = 'keep_last'
    
    # ---------- OUTLIER HANDLING ----------
    OUTLIER_METHODS = [
        'clip',
        'remove',
        'winsorize',
        'none'
    ]
    DEFAULT_OUTLIER = 'clip'
    OUTLIER_STD_THRESHOLD = 3.0
    
    # ---------- ROLLBACK ----------
    MAX_ROLLBACK_STATES = 10


# ================ EXPLORATION SETTINGS ================

class ExplorationConfig:
    """
    autoviz exploration settings
    """
    # ---------- CHART SETTINGS ----------
    MAX_CHARTS = 20
    CHART_FORMAT = 'svg'
    
    # ---------- DECOMPOSITION ----------
    DECOMPOSITION_MODEL = 'additive'
    SEASONAL_PERIOD = 7
    
    # ---------- ANOMALY DETECTION ----------
    ANOMALY_CONTAMINATION = 0.05
    ANOMALY_METHODS = [
        'isolation_forest',
        'local_outlier_factor',
        'zscore'
    ]
    DEFAULT_ANOMALY_METHOD = 'isolation_forest'
    
    # ---------- DISPLAY ----------
    MAX_SKUS_DISPLAY = 50


# ================ FEATURE ENGINEERING SETTINGS ================

class FeatureConfig:
    """
    tsfresh and featuretools settings
    """
    # ---------- TSFRESH ----------
    TSFRESH_DEFAULTS = 'efficient'
    MIN_TIMESHIFT = 1
    MAX_TIMESHIFT = 7
    
    # ---------- FEATURE SELECTION ----------
    RELEVANCE_THRESHOLD = 0.05
    MAX_FEATURES = 100
    
    # ---------- FEATURETOOLS ----------
    MAX_DEPTH = 2
    PRIMITIVES = [
        'sum',
        'mean',
        'std',
        'min',
        'max',
        'trend',
        'skew'
    ]
    
    # ---------- EXPORT ----------
    EXPORT_FORMATS = ['csv', 'parquet', 'pickle']


# ================ AUTOTS SETTINGS ================

class AutoTSConfig:
    """
    autots model parameters
    """
    # ---------- FORECAST LENGTH ----------
    DEFAULT_FORECAST_DAYS = 30
    MIN_FORECAST_DAYS = 1
    MAX_FORECAST_DAYS = 365
    
    # ---------- MODEL SETTINGS ----------
    FREQUENCY = 'infer'
    ENSEMBLE = 'simple'
    MAX_GENERATIONS = 2
    NUM_VALIDATIONS = 1
    VALIDATION_METHOD = 'backwards'
    MODEL_LIST = 'fast'
    TRANSFORMER_LIST = 'fast'
    N_JOBS = 'auto'
    
    # ---------- CONFIDENCE SETTINGS ----------
    PREDICTION_INTERVAL = 0.95
    SHOW_CONFIDENCE_BANDS = True
    
    # ---------- SPEED PRESETS ----------
    SUPERFAST_MODE = {
        'max_generations': 1,
        'num_validations': 0,
        'model_list': 'superfast',
        'transformer_list': 'superfast',
        'ensemble': None,
        'models_to_validate': 0.1
    }
    
    FAST_MODE = {
        'max_generations': 2,
        'num_validations': 1,
        'model_list': 'fast',
        'transformer_list': 'fast',
        'ensemble': 'simple',
        'models_to_validate': 0.15
    }
    
    BALANCED_MODE = {
        'max_generations': 5,
        'num_validations': 2,
        'model_list': 'default',
        'transformer_list': 'fast',
        'ensemble': 'simple',
        'models_to_validate': 0.25
    }
    
    ACCURATE_MODE = {
        'max_generations': 10,
        'num_validations': 3,
        'model_list': 'all',
        'transformer_list': 'all',
        'ensemble': 'all',
        'models_to_validate': 0.35
    }
    
    # ---------- EVALUATION METRICS ----------
    METRICS = ['MAE', 'RMSE', 'MAPE', 'SMAPE']


# ================ PIPELINE SETTINGS ================

class PipelineConfig:
    """
    pipeline orchestration settings
    """
    # ---------- STAGES ----------
    STAGES = [
        'data_quality',
        'exploration',
        'features',
        'forecasting'
    ]
    
    STAGE_NAMES = {
        'data_quality': 'Data Quality',
        'exploration': 'Exploration',
        'features': 'Feature Engineering',
        'forecasting': 'Forecasting'
    }
    
    # ---------- AUTO ADVANCE ----------
    AUTO_ADVANCE = False
    
    # ---------- VALIDATION ----------
    REQUIRE_CLEAN_DATA = True
    REQUIRE_FEATURES = False


# ================ ALERT SETTINGS ================

class AlertConfig:
    """
    alert and notification settings
    """
    # ---------- ALERT TYPES ----------
    TYPES = [
        'anomaly',
        'model_drift',
        'pipeline_error',
        'data_quality',
        'info'
    ]
    
    # ---------- SEVERITY ----------
    SEVERITY_LEVELS = ['low', 'medium', 'high', 'critical']
    
    # ---------- RETENTION ----------
    MAX_ALERTS = 100
    AUTO_DISMISS_DAYS = 7


# ================ EXPORT SETTINGS ================

class ExportConfig:
    """
    export settings
    """
    # ---------- TIMESTAMP FORMAT ----------
    TIMESTAMP_FORMAT = '%Y%m%d_%H%M%S'
    
    # ---------- CSV SETTINGS ----------
    CSV_INDEX = True
    CSV_ENCODING = 'utf-8'
    
    # ---------- EXCEL SETTINGS ----------
    EXCEL_ENGINE = 'openpyxl'
    
    # ---------- API SETTINGS ----------
    API_TIMEOUT = 30
    API_RETRY = 3
    
    # ---------- FORMATS ----------
    AVAILABLE_FORMATS = ['csv', 'xlsx', 'json', 'parquet']
    DEFAULT_FORMAT = 'csv'


# ================ CHART SETTINGS ================

class ChartConfig:
    """
    chart visualization settings
    """
    # ---------- FIGURE SIZE ----------
    FIGURE_WIDTH = 12
    FIGURE_HEIGHT_PER_SKU = 2.5
    MAX_FIGURE_HEIGHT = 20
    
    # ---------- DPI ----------
    SAVE_DPI = 100
    DISPLAY_DPI = 100
    
    # ---------- COLORS ----------
    HISTORICAL_COLOR = '#2196F3'
    FORECAST_COLOR = '#F44336'
    CONFIDENCE_COLOR = '#FFCDD2'
    ANOMALY_COLOR = '#FF9800'
    CONFIDENCE_ALPHA = 0.3
    
    # ---------- THEME ----------
    DARK_THEME = {
        'background': '#1e1e1e',
        'text': '#ffffff',
        'grid': '#333333',
        'accent': '#2196F3'
    }
    
    LIGHT_THEME = {
        'background': '#ffffff',
        'text': '#000000',
        'grid': '#e0e0e0',
        'accent': '#1976D2'
    }


# ================ DATA SETTINGS ================

class DataConfig:
    """
    data processing settings
    """
    # ---------- REQUIRED COLUMNS ----------
    REQUIRED_COLUMNS = ['Date', 'SKU', 'Quantity']
    
    # ---------- OPTIONAL COLUMNS ----------
    OPTIONAL_COLUMNS = ['Category', 'Warehouse', 'Price', 'Cost', 'Promotion']
    
    # ---------- DATE FORMATS ----------
    DATE_FORMATS = [
        '%Y-%m-%d',
        '%d-%m-%Y',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%Y/%m/%d',
        '%d %b %Y',
        '%d %B %Y',
        '%b %d, %Y',
        '%B %d, %Y'
    ]
    
    # ---------- GROUPING OPTIONS ----------
    GROUP_OPTIONS = ['Daily', 'Weekly', 'Monthly', 'Quarterly']
    
    # ---------- VALIDATION ----------
    MIN_DATA_POINTS = 14
    RECOMMENDED_DATA_POINTS = 60
    
    # ---------- LARGE DATA ----------
    MAX_ROWS = 100000
    MAX_SKUS = 500
    SAMPLE_SIZE = 50000


# ================ DISPLAY SETTINGS ================

class DisplayConfig:
    """
    ui display formats
    """
    # ---------- DATE FORMAT ----------
    DATE_FORMAT = '%d %b %Y'
    DATETIME_FORMAT = '%d %b %Y %H:%M'
    
    # ---------- NUMBER FORMAT ----------
    DECIMAL_PLACES = 2
    THOUSAND_SEPARATOR = ','


# ================ LOGGING SETTINGS ================

class LogConfig:
    """
    logging configuration
    """
    # ---------- LOG LEVEL ----------
    LOG_LEVEL = 'INFO'
    
    # ---------- FORMAT ----------
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    # ---------- FILE SETTINGS ----------
    MAX_LOG_SIZE = 5 * 1024 * 1024
    BACKUP_COUNT = 3
    LOG_FILE = Paths.OUTPUT_DIR / 'stocksight.log'


# ================ INITIALIZATION ================

def init_directories():
    """
    create all required directories
    """
    directories = [
        Paths.DATA_DIR,
        Paths.OUTPUT_DIR,
        Paths.CACHE_DIR,
        Paths.MODELS_DIR,
        Paths.PROFILES_DIR,
        Paths.FEATURES_DIR,
        Paths.FORECASTS_DIR,
        Paths.USER_OUTPUT
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)