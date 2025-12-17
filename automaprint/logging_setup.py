"""
Logging utilities for AutomaPrint
"""

import os
import sys
import glob
import logging
import traceback
from datetime import datetime, timedelta

from .config import get_data_dir


def get_logs_dir():
    """Get or create logs directory in the app data folder"""
    logs_dir = os.path.join(get_data_dir(), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


def setup_logger(name, prefix=""):
    """Setup a logger with file and console handlers"""
    logs_dir = get_logs_dir()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.log" if prefix else f"{timestamp}.log"
    log_path = os.path.join(logs_dir, filename)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers
    if not logger.handlers:
        # File handler
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def setup_early_logging():
    """Setup logging as early as possible to capture startup issues"""
    try:
        logs_dir = get_logs_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        startup_log_path = os.path.join(logs_dir, f"{timestamp}_startup.log")

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(startup_log_path, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

        logger = logging.getLogger('startup')
        logger.info("=== AutomaPrint Server Startup Log ===")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Platform: {sys.platform}")
        logger.info(f"Working directory: {os.getcwd()}")
        logger.info(f"Script path: {os.path.abspath(__file__)}")
        logger.info(f"Command line arguments: {sys.argv}")

        return logger

    except Exception as e:
        print(f"CRITICAL: Failed to setup early logging: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return None


def cleanup_old_logs(logs_dir=None, days_to_keep=30):
    """Clean up old log files"""
    if logs_dir is None:
        logs_dir = get_logs_dir()

    try:
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        log_pattern = os.path.join(logs_dir, "*.log")

        for log_file in glob.glob(log_pattern):
            try:
                file_time = datetime.fromtimestamp(os.path.getctime(log_file))
                if file_time < cutoff_date:
                    os.remove(log_file)
                    print(f"Cleaned up old log: {os.path.basename(log_file)}")
            except Exception as e:
                print(f"Error removing log file {log_file}: {e}")
    except Exception as e:
        print(f"Error during log cleanup: {e}")
