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
    all_logs_handler.setLevel(logging.DEBUG)
    all_logs_handler.setFormatter(detailed_formatter)

    error_logs_handler = RotatingFileHandler(
        f'{log_dir}/errors.log',
        maxBytes=10*1024*1024,
        backupCount=3
    )
    error_logs_handler.setLevel(logging.DEBUG)
    error_logs_handler.setFormatter(detailed_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)

    # Add handlers to main logger
    logger.addHandler(all_logs_handler)
    logger.addHandler(error_logs_handler)
    logger.addHandler(console_handler)

    # Create specific loggers - all use the same rotating handlers with detailed formatting
    service_loggers = [
        'fraud_detection.graph',
        'fraud_detection.api', 
        'fraud_detection.transaction_generator',
        'fraud_detection.stats',
        'fraud_detection.fraud_service',
        'fraud_detection.performance'
    ]
    
    for logger_name in service_loggers:
        service_logger = logging.getLogger(logger_name)
        service_logger.setLevel(logging.INFO)
        service_logger.addHandler(all_logs_handler)  # Rotating handler with detailed formatter
        service_logger.addHandler(console_handler)   # Console handler with simple formatter
        service_logger.propagate = False  # Don't propagate to parent to avoid duplicate logs
    
    return logger

def get_logger(name='fraud_detection'):
    """Get a logger instance"""
    return logging.getLogger(name) 