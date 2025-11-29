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
    
    # ---------- UTILS DIRECTORY ----------
    UTILS_DIR = BASE_DIR / "utils"
    
    # ---------- USER DOCUMENTS ----------
    USER_DOCS = Path.home() / "Documents" / "Stocksight"
    USER_OUTPUT = USER_DOCS / "output"
    
    # ---------- DEFAULT FILES ----------
    DEFAULT_CSV = DATA_DIR / "inventory.csv"
    FORECAST_CHART = OUTPUT_DIR / "forecast.png"
    FORECAST_DATA = OUTPUT_DIR / "forecast_data.csv"
    SUMMARY_FILE = OUTPUT_DIR / "summary.txt"
    LOG_FILE = OUTPUT_DIR / "app.log"


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


# ================ LARGE DATA SETTINGS ================

class LargeDataConfig:
    """
    settings for handling large datasets
    """
    # ---------- THRESHOLDS ----------
    MAX_ROWS = 100000
    MAX_SKUS = 100
    MAX_SKUS_CHART = 15
    MAX_SKUS_DASHBOARD = 10
    
    # ---------- PARALLEL SETTINGS ----------
    PARALLEL_THRESHOLD = 10
    MAX_WORKERS = 8
    
    # ---------- SAMPLING ----------
    SAMPLE_ROWS = 50000
    KEEP_RECENT = True
    
    # ---------- MEMORY ----------
    OPTIMIZE_DTYPES = True
    FORCE_GC = True
    
    # ---------- CHART ----------
    LOW_DPI = 60
    MAX_CHART_HEIGHT = 50


# ================ GUI SETTINGS ================

class GUIConfig:
    """
    dear pygui settings
    """
    # ---------- WINDOW SETTINGS ----------
    WINDOW_TITLE = "Stocksight - Inventory Forecast"
    WINDOW_WIDTH = 1400
    WINDOW_HEIGHT = 800
    
    # ---------- PANEL SETTINGS ----------
    LEFT_PANEL_WIDTH = 320
    
    # ---------- COLORS ----------
    HEADER_COLOR = (255, 200, 100)
    STATUS_COLOR = (150, 150, 150)
    SUCCESS_COLOR = (100, 255, 100)
    ERROR_COLOR = (255, 100, 100)
    WARNING_COLOR = (255, 200, 100)
    
    # ---------- FONTS ----------
    DEFAULT_FONT_SIZE = 14
    HEADER_FONT_SIZE = 18
    HELP_TEXT_SIZE = 12


# ================ CHART SETTINGS ================

class ChartConfig:
    """
    matplotlib chart settings
    """
    # ---------- FIGURE SIZE ----------
    FIGURE_WIDTH = 12
    FIGURE_HEIGHT_PER_SKU = 3
    
    # ---------- DPI ----------
    SAVE_DPI = 100
    
    # ---------- COLORS ----------
    HISTORICAL_COLOR = 'blue'
    FORECAST_COLOR = 'red'
    CONFIDENCE_COLOR = 'lightcoral'
    CONFIDENCE_ALPHA = 0.2
    
    # ---------- LINE STYLES ----------
    HISTORICAL_STYLE = '-'
    FORECAST_STYLE = '--'
    
    # ---------- LINE WIDTH ----------
    LINE_WIDTH = 1.5
    
    # ---------- GRID ----------
    GRID_ALPHA = 0.3


# ================ SCENARIO SETTINGS ================

class ScenarioConfig:
    """
    scenario simulation settings
    """
    # ---------- DEMAND SPIKE ----------
    DEFAULT_SPIKE_MULTIPLIER = 1.5
    MIN_SPIKE_MULTIPLIER = 0.1
    MAX_SPIKE_MULTIPLIER = 10.0
    
    # ---------- SUPPLY DELAY ----------
    DEFAULT_DELAY_DAYS = 7
    MIN_DELAY_DAYS = 1
    MAX_DELAY_DAYS = 90


# ================ DATA SETTINGS ================

class DataConfig:
    """
    data processing settings
    """
    # ---------- REQUIRED COLUMNS ----------
    REQUIRED_COLUMNS = ['Date', 'SKU', 'Quantity']
    
    # ---------- OPTIONAL COLUMNS ----------
    OPTIONAL_COLUMNS = ['Category', 'Warehouse', 'Price', 'Cost']
    
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
    
    # ---------- PREVIEW ROWS ----------
    PREVIEW_ROWS = 20
    
    # ---------- AGGREGATION ----------
    DEFAULT_AGGREGATION = 'sum'
    
    # ---------- VALIDATION ----------
    MIN_DATA_POINTS = 14
    RECOMMENDED_DATA_POINTS = 60


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
    
    # ---------- DEFAULT LOCATION ----------
    USE_USER_DOCUMENTS = True
    ALLOW_CUSTOM_LOCATION = True
    
    # ---------- EXPORT OPTIONS ----------
    EXPORT_CHARTS = True
    EXPORT_DATA = True
    EXPORT_SUMMARY = True


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
    MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 mb
    BACKUP_COUNT = 3


# ================ INITIALIZATION ================

def init_directories():
    """
    create all required directories
    """
    os.makedirs(Paths.DATA_DIR, exist_ok=True)
    os.makedirs(Paths.OUTPUT_DIR, exist_ok=True)
    os.makedirs(Paths.USER_OUTPUT, exist_ok=True)