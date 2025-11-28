"""
logging utilities
handle application logging
file and console output
"""


# ================ IMPORTS ================

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

# ---------- LOCAL IMPORTS ----------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Paths, LogConfig


# ================ LOGGER SETUP ================

def setup_logger(name='stocksight'):
    """
    configure application logger
    setup file and console handlers
    """
    # ---------- CREATE LOGGER ----------
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LogConfig.LOG_LEVEL))
    
    # ---------- PREVENT DUPLICATES ----------
    if logger.handlers:
        return logger
    
    # ---------- FORMATTER ----------
    formatter = logging.Formatter(
        LogConfig.LOG_FORMAT,
        datefmt=LogConfig.DATE_FORMAT
    )
    
    # ---------- CONSOLE HANDLER ----------
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # ---------- FILE HANDLER ----------
    os.makedirs(Paths.OUTPUT_DIR, exist_ok=True)
    file_handler = RotatingFileHandler(
        Paths.LOG_FILE,
        maxBytes=LogConfig.MAX_LOG_SIZE,
        backupCount=LogConfig.BACKUP_COUNT
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# ================ LOGGER INSTANCE ================

logger = setup_logger()


# ================ LOGGING FUNCTIONS ================

def log_info(message):
    """
    log info message
    """
    logger.info(message)


def log_error(message):
    """
    log error message
    """
    logger.error(message)


def log_warning(message):
    """
    log warning message
    """
    logger.warning(message)


def log_debug(message):
    """
    log debug message
    """
    logger.debug(message)


def log_exception(message):
    """
    log exception with traceback
    """
    logger.exception(message)


# ================ PERFORMANCE LOGGING ================

class PerformanceTimer:
    """
    track execution time
    log performance metrics
    """
    
    def __init__(self, operation_name):
        self.operation = operation_name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        log_debug(f"started: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        log_info(f"completed: {self.operation} ({duration:.2f}s)")
        return False
    
    @property
    def elapsed(self):
        """
        get elapsed time in seconds
        """
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0


# ================ EVENT LOGGING ================

def log_data_loaded(file_path, record_count, sku_count):
    """
    log data load event
    """
    log_info(f"data loaded: {file_path}")
    log_info(f"records: {record_count}, skus: {sku_count}")


def log_forecast_started(forecast_days, sku_count):
    """
    log forecast start event
    """
    log_info(f"forecast started: {forecast_days} days, {sku_count} skus")


def log_forecast_completed(forecast_days, duration):
    """
    log forecast completion
    """
    log_info(f"forecast completed: {forecast_days} days in {duration:.2f}s")


def log_export_completed(file_path):
    """
    log export event
    """
    log_info(f"exported: {file_path}")


def log_scenario_applied(scenario_type, sku, params):
    """
    log scenario application
    """
    log_info(f"scenario applied: {scenario_type} on {sku}")
    log_debug(f"scenario params: {params}")