import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Setup logging configuration for the backend"""
    
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create a custom logger
    logger = logging.getLogger('fraud_detection')
    logger.setLevel(logging.DEBUG)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    fraud_formatter = logging.Formatter(
        '%(asctime)s - FRAUD - %(message)s'
    )
    normal_formatter = logging.Formatter(
        '%(asctime)s - NORMAL - %(message)s'
    )
    stats_formatter = logging.Formatter(
        '%(asctime)s - STATS - %(message)s'
    )

    # Rotating file handler for all logs (50MB max, 5 backups)
    all_logs_handler = RotatingFileHandler(
        f'{log_dir}/all.log',
        maxBytes=50*1024*1024,
        backupCount=5
    )
    all_logs_handler.setLevel(logging.INFO)
    all_logs_handler.setFormatter(detailed_formatter)

    # Rotating file handler for errors only (10MB max, 3 backups)
    error_logs_handler = RotatingFileHandler(
        f'{log_dir}/errors.log',
        maxBytes=10*1024*1024,
        backupCount=3
    )
    error_logs_handler.setLevel(logging.ERROR)
    error_logs_handler.setFormatter(detailed_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)

    # Add handlers to main logger
    logger.addHandler(all_logs_handler)
    logger.addHandler(error_logs_handler)
    logger.addHandler(console_handler)

    # Create specific loggers - all use the same rotating handlers
    graph_logger = logging.getLogger('fraud_detection.graph')
    graph_logger.setLevel(logging.ERROR)
    graph_logger.addHandler(all_logs_handler)  # Use main rotating handler
    graph_logger.addHandler(console_handler)
    graph_logger.propagate = False

    api_logger = logging.getLogger('fraud_detection.api')
    api_logger.setLevel(logging.ERROR)
    api_logger.addHandler(all_logs_handler)  # Use main rotating handler
    api_logger.addHandler(console_handler)
    api_logger.propagate = False

    txn_logger = logging.getLogger('fraud_detection.transaction_generator')
    txn_logger.setLevel(logging.ERROR)
    txn_logger.addHandler(all_logs_handler)  # Use main rotating handler
    txn_logger.addHandler(console_handler)
    txn_logger.propagate = False

    stats_logger = logging.getLogger('fraud_detection.stats')
    stats_logger.setLevel(logging.INFO)
    stats_logger.addHandler(all_logs_handler)  # Use main rotating handler
    stats_logger.addHandler(console_handler)
    stats_logger.propagate = False
    
    return logger

def get_logger(name='fraud_detection'):
    """Get a logger instance"""
    return logging.getLogger(name) 