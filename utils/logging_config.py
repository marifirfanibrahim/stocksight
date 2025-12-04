"""
logging configuration module
sets up application logging
manages log files and formatting
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Optional

import config


# ============================================================================
#                           LOGGING SETUP
# ============================================================================

def setup_logging(level: Optional[str] = None) -> logging.Logger:
    # configure application logging
    
    # ensure log directory exists
    config.ensure_directories()
    
    # get settings from config
    log_config = config.LOGGING
    log_level = level or log_config["level"]
    
    # create logger
    logger = logging.getLogger("stocksight")
    logger.setLevel(getattr(logging, log_level))
    
    # clear existing handlers
    logger.handlers.clear()
    
    # console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # file handler
    log_filename = log_config["file_format"].format(
        date=datetime.now().strftime("%Y%m%d")
    )
    log_path = config.LOG_DIR / log_filename
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=log_config["max_file_size_mb"] * 1024 * 1024,
        backupCount=log_config["backup_count"]
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(log_config["format"])
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    logger.info(f"logging initialized - level: {log_level}")
    
    return logger


def get_logger(name: str = "stocksight") -> logging.Logger:
    # get logger instance
    return logging.getLogger(name)


class LogCapture:
    # context manager to capture log messages
    
    def __init__(self, logger_name: str = "stocksight", level: int = logging.INFO):
        # initialize capture
        self.logger = logging.getLogger(logger_name)
        self.level = level
        self.messages = []
        self.handler = None
    
    def __enter__(self):
        # start capturing
        self.handler = LogCaptureHandler(self.messages)
        self.handler.setLevel(self.level)
        self.logger.addHandler(self.handler)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # stop capturing
        if self.handler:
            self.logger.removeHandler(self.handler)
        return False
    
    def get_messages(self) -> list:
        # return captured messages
        return self.messages.copy()


class LogCaptureHandler(logging.Handler):
    # handler that captures messages to list
    
    def __init__(self, message_list: list):
        # initialize handler
        super().__init__()
        self.messages = message_list
    
    def emit(self, record):
        # capture log record
        self.messages.append({
            "level": record.levelname,
            "message": record.getMessage(),
            "time": datetime.fromtimestamp(record.created)
        })


# ============================================================================
#                           PROGRESS LOGGER
# ============================================================================

class ProgressLogger:
    # logger for progress updates
    
    def __init__(self, total: int, description: str = "processing"):
        # initialize progress logger
        self.total = total
        self.current = 0
        self.description = description
        self.logger = get_logger()
        self.last_logged_pct = -10
    
    def update(self, count: int = 1) -> None:
        # update progress
        self.current += count
        pct = int(self.current / self.total * 100)
        
        # log every 10%
        if pct >= self.last_logged_pct + 10:
            self.logger.info(f"{self.description}: {pct}% complete")
            self.last_logged_pct = pct
    
    def finish(self) -> None:
        # log completion
        self.logger.info(f"{self.description}: completed")