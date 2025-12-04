"""
stocksight configuration
contains all thresholds defaults and settings
manages application-wide constants
"""

import os
from pathlib import Path

# ============================================================================
#                                PATHS
# ============================================================================

# ---------- BASE DIRECTORIES ----------
BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
STYLES_DIR = ASSETS_DIR / "styles"
TEMPLATES_DIR = ASSETS_DIR / "templates"

# ---------- USER DIRECTORIES ----------
USER_HOME = Path.home()
APP_DATA_DIR = USER_HOME / ".stocksight"
LOG_DIR = APP_DATA_DIR / "logs"
CACHE_DIR = APP_DATA_DIR / "cache"

# ============================================================================
#                              APPLICATION
# ============================================================================

# ---------- APP INFO ----------
APP_NAME = "StockSight"
APP_VERSION = "1.0.0"
APP_AUTHOR = "StockSight Team"

# ---------- WINDOW SETTINGS ----------
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 800
WINDOW_DEFAULT_WIDTH = 1400
WINDOW_DEFAULT_HEIGHT = 900

# ============================================================================
#                             DATA PROCESSING
# ============================================================================

# ---------- FILE SUPPORT ----------
SUPPORTED_FILE_TYPES = {
    "csv": "CSV Files (*.csv)",
    "excel": "Excel Files (*.xlsx *.xls)",
    "parquet": "Parquet Files (*.parquet)"
}

MAX_FILE_SIZE_MB = 500

# ---------- COLUMN DETECTION ----------
COLUMN_DETECTION = {
    "date_keywords": [
        "date", "time", "timestamp", "period", "day", "week", "month", "year"
    ],
    "sku_keywords": [
        "sku", "item", "product", "article", "code", "id", "upc", "ean"
    ],
    "quantity_keywords": [
        "quantity", "qty", "sales", "demand", "units", "volume", "count"
    ],
    "category_keywords": [
        "category", "group", "family", "class", "type", "segment"
    ],
    "price_keywords": [
        "price", "cost", "value", "amount", "revenue"
    ],
    "promo_keywords": [
        "promo", "promotion", "discount", "offer", "sale", "campaign"
    ],
    "confidence_threshold": 0.7
}

# ---------- DATA QUALITY ----------
DATA_QUALITY = {
    "min_data_points": 12,
    "max_missing_pct": 30,
    "outlier_std_threshold": 3.0,
    "duplicate_check": True
}

# ============================================================================
#                              CLUSTERING
# ============================================================================

# ---------- VOLUME TIERS ----------
CLUSTERING = {
    "volume_thresholds": {
        "A": 1000,  # units per week
        "B": 100,
        "C": 0
    },
    "volume_percentiles": {
        "A": 80,  # top 20% by volume
        "B": 50,  # next 30%
        "C": 0    # bottom 50%
    },
    "pattern_thresholds": {
        "seasonal": 0.6,   # q4 concentration above 60%
        "erratic": 0.8,    # cv above 0.8
        "variable": 0.3,   # cv between 0.3 and 0.8
        "steady": 0.0      # cv below 0.3
    },
    "use_percentiles": True  # use percentiles instead of absolute thresholds
}

# ---------- CLUSTER LABELS ----------
CLUSTER_LABELS = {
    "volume": {
        "A": "High Volume",
        "B": "Medium Volume",
        "C": "Low Volume"
    },
    "pattern": {
        "seasonal": "Seasonal",
        "erratic": "Erratic",
        "variable": "Variable",
        "steady": "Steady"
    }
}

# ============================================================================
#                           FEATURE ENGINEERING
# ============================================================================

# ---------- CURATED FEATURES ----------
FEATURES = {
    "curated": [
        "lag_1", "lag_7", "lag_28",
        "rolling_mean_7", "rolling_mean_28",
        "rolling_std_7", "rolling_std_28",
        "year", "month", "week_of_year",
        "day_of_week", "is_weekend", "is_holiday",
        "days_to_holiday", "price_change_pct",
        "price_relative_to_avg", "promo_flag",
        "promo_intensity", "seasonal_index",
        "trend_component"
    ],
    "basic_5": [
        "lag_1", "lag_7", "rolling_mean_7", "month", "day_of_week"
    ],
    "top_10": [
        "lag_1", "lag_7", "lag_28",
        "rolling_mean_7", "rolling_mean_28",
        "month", "week_of_year", "day_of_week",
        "seasonal_index", "trend_component"
    ],
    "group_config": {
        "A": "all_20",
        "B": "top_10",
        "C": "basic_5"
    }
}

# ---------- FEATURE DESCRIPTIONS ----------
FEATURE_DESCRIPTIONS = {
    "lag_1": "yesterday's sales predict today",
    "lag_7": "last week's sales predict this week",
    "lag_28": "last month's sales predict this month",
    "rolling_mean_7": "average sales over past week",
    "rolling_mean_28": "average sales over past month",
    "rolling_std_7": "sales variability over past week",
    "rolling_std_28": "sales variability over past month",
    "year": "year number for trend detection",
    "month": "month of year for seasonality",
    "week_of_year": "week number for weekly patterns",
    "day_of_week": "weekday vs weekend patterns",
    "is_weekend": "saturday and sunday flag",
    "is_holiday": "holiday impact on sales",
    "days_to_holiday": "proximity to upcoming holiday",
    "price_change_pct": "price changes affect demand",
    "price_relative_to_avg": "price compared to average",
    "promo_flag": "promotion active indicator",
    "promo_intensity": "promotion strength measure",
    "seasonal_index": "seasonal pattern strength",
    "trend_component": "long-term trend direction"
}

# ============================================================================
#                              FORECASTING
# ============================================================================

# ---------- STRATEGIES ----------
FORECASTING = {
    "simple": {
        "name": "Simple & Fast",
        "icon": "🔵",
        "models": ["naive", "seasonal_naive", "exponential_smoothing"],
        "time_estimate": "5-10 minutes",
        "description": "Quick baseline forecasts for all items",
        "recommended_for": "Initial analysis and C-items"
    },
    "balanced": {
        "name": "Smart & Balanced",
        "icon": "🟡",
        "models": ["exponential_smoothing", "arima", "theta", "prophet"],
        "time_estimate": "20-30 minutes",
        "description": "Best balance of speed and accuracy",
        "recommended_for": "Most business scenarios"
    },
    "advanced": {
        "name": "Advanced AI",
        "icon": "🔴",
        "models": ["lightgbm", "xgboost", "ensemble"],
        "time_estimate": "1-2 hours",
        "description": "Maximum accuracy for critical items",
        "recommended_for": "Top A-items only"
    }
}

# ---------- MODEL SETTINGS ----------
MODEL_SETTINGS = {
    "naive": {
        "name": "Simple Average",
        "description": "Uses recent average as forecast"
    },
    "seasonal_naive": {
        "name": "Seasonal Pattern",
        "description": "Repeats last year's pattern"
    },
    "exponential_smoothing": {
        "name": "Smoothed Trend",
        "description": "Weights recent data more heavily"
    },
    "arima": {
        "name": "Statistical Model",
        "description": "Captures trends and patterns"
    },
    "theta": {
        "name": "Theta Method",
        "description": "Combines trend extrapolation"
    },
    "prophet": {
        "name": "Prophet",
        "description": "Handles holidays and seasonality"
    },
    "lightgbm": {
        "name": "Machine Learning",
        "description": "Learns complex patterns"
    },
    "xgboost": {
        "name": "Gradient Boosting",
        "description": "Powerful pattern detection"
    },
    "ensemble": {
        "name": "Combined Models",
        "description": "Averages multiple forecasts"
    }
}

# ---------- FORECAST HORIZONS ----------
FORECAST_HORIZONS = {
    "short": {"days": 7, "label": "1 Week"},
    "medium": {"days": 30, "label": "1 Month"},
    "long": {"days": 90, "label": "3 Months"},
    "extended": {"days": 180, "label": "6 Months"}
}

DEFAULT_HORIZON = "medium"

# ============================================================================
#                           ANOMALY DETECTION
# ============================================================================

# ---------- DETECTION METHODS ----------
ANOMALY_DETECTION = {
    "methods": {
        "iqr": {
            "name": "IQR Method",
            "description": "Detects values outside normal range",
            "multiplier": 1.5
        },
        "zscore": {
            "name": "Z-Score Method",
            "description": "Detects statistically unusual values",
            "threshold": 3.0
        },
        "rolling": {
            "name": "Rolling Window",
            "description": "Detects sudden changes",
            "window": 7,
            "threshold": 2.5
        }
    },
    "default_method": "iqr",
    "min_anomaly_score": 0.7
}

# ---------- ANOMALY TYPES ----------
ANOMALY_TYPES = {
    "spike": "Unusual high value",
    "drop": "Unusual low value",
    "zero": "Unexpected zero sales",
    "negative": "Negative value detected",
    "gap": "Missing data period"
}

# ============================================================================
#                              PERFORMANCE
# ============================================================================

# ---------- MEMORY MANAGEMENT ----------
PERFORMANCE = {
    "max_skus_in_memory": 1000,
    "chunk_size": 1000,
    "sample_size_visualization": 20,
    "sample_size_heatmap": 100,
    "background_threads": 4,
    "cache_size_mb": 512,
    "gc_threshold": 0.8  # trigger gc at 80% memory
}

# ---------- TIMING TARGETS ----------
TIMING_TARGETS = {
    "upload_per_10k": 150,      # seconds
    "exploration_initial": 90,  # seconds
    "feature_engineering": 150, # seconds
    "simple_forecast": 600,     # seconds
    "balanced_forecast": 1800,  # seconds
    "advanced_forecast": 7200   # seconds
}

# ============================================================================
#                                EXPORT
# ============================================================================

# ---------- EXPORT FORMATS ----------
EXPORT_FORMATS = {
    "csv": {
        "name": "CSV File",
        "extension": ".csv",
        "description": "For ERP and data systems"
    },
    "excel": {
        "name": "Excel Workbook",
        "extension": ".xlsx",
        "description": "For spreadsheet analysis"
    },
    "ppt": {
        "name": "PowerPoint",
        "extension": ".pptx",
        "description": "For management presentations"
    },
    "pdf": {
        "name": "PDF Report",
        "extension": ".pdf",
        "description": "For executive summary"
    }
}

# ---------- PPT TEMPLATE ----------
PPT_TEMPLATE = {
    "slides": [
        {"type": "title", "name": "Forecast Summary"},
        {"type": "overview", "name": "Key Metrics"},
        {"type": "details", "name": "Top Items Analysis"}
    ],
    "colors": {
        "primary": "#2E86AB",
        "secondary": "#A23B72",
        "accent": "#F18F01",
        "background": "#FFFFFF",
        "text": "#1B1B1E"
    }
}

# ============================================================================
#                                  UI
# ============================================================================

# ---------- COLORS ----------
UI_COLORS = {
    "primary": "#2E86AB",
    "secondary": "#A23B72",
    "success": "#28A745",
    "warning": "#FFC107",
    "danger": "#DC3545",
    "info": "#17A2B8",
    "light": "#F8F9FA",
    "dark": "#343A40",
    "background": "#FFFFFF",
    "surface": "#F5F5F5",
    "border": "#DEE2E6"
}

# ---------- QUALITY SCORE COLORS ----------
QUALITY_COLORS = {
    "excellent": {"min": 90, "color": "#28A745"},
    "good": {"min": 75, "color": "#8BC34A"},
    "fair": {"min": 60, "color": "#FFC107"},
    "poor": {"min": 40, "color": "#FF9800"},
    "critical": {"min": 0, "color": "#DC3545"}
}

# ---------- TAB NAMES ----------
TAB_NAMES = {
    0: "Data Health",
    1: "Pattern Discovery",
    2: "Feature Engineering",
    3: "Forecast Factory"
}

# ---------- PROGRESS MESSAGES ----------
PROGRESS_MESSAGES = {
    "loading": "Loading data...",
    "detecting": "Detecting columns...",
    "cleaning": "Cleaning data...",
    "clustering": "Grouping items...",
    "features": "Creating features...",
    "forecasting": "Generating forecasts...",
    "exporting": "Exporting results..."
}

# ============================================================================
#                               LOGGING
# ============================================================================

# ---------- LOG SETTINGS ----------
LOGGING = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file_format": "stocksight_{date}.log",
    "max_file_size_mb": 10,
    "backup_count": 5
}


def ensure_directories():
    # create required directories if missing
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_quality_color(score):
    # return color based on quality score
    for level, config in QUALITY_COLORS.items():
        if score >= config["min"]:
            return config["color"]
    return QUALITY_COLORS["critical"]["color"]


def get_cluster_label(volume_tier, pattern_type):
    # create human readable cluster label
    vol_label = CLUSTER_LABELS["volume"].get(volume_tier, volume_tier)
    pat_label = CLUSTER_LABELS["pattern"].get(pattern_type, pattern_type)
    return f"{vol_label} - {pat_label}"