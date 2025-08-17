import logging
import os
from datetime import datetime

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
    
    # File handler for all logs
    all_logs_handler = logging.FileHandler(f'{log_dir}/all.log')
    all_logs_handler.setLevel(logging.DEBUG)
    all_logs_handler.setFormatter(detailed_formatter)
    
    # File handler for errors only
    error_logs_handler = logging.FileHandler(f'{log_dir}/errors.log')
    error_logs_handler.setLevel(logging.ERROR)
    error_logs_handler.setFormatter(detailed_formatter)
    
    # File handler for Aerospike Graph specific logs
    graph_logs_handler = logging.FileHandler(f'{log_dir}/graph.log')
    graph_logs_handler.setLevel(logging.DEBUG)
    graph_logs_handler.setFormatter(detailed_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # Add handlers to logger
    logger.addHandler(all_logs_handler)
    logger.addHandler(error_logs_handler)
    logger.addHandler(graph_logs_handler)
    logger.addHandler(console_handler)
    
    # Create specific loggers
    graph_logger = logging.getLogger('fraud_detection.graph')
    graph_logger.setLevel(logging.DEBUG)
    graph_logger.addHandler(graph_logs_handler)
    graph_logger.addHandler(console_handler)
    graph_logger.propagate = False  # Prevent propagation to parent logger
    
    api_logger = logging.getLogger('fraud_detection.api')
    api_logger.setLevel(logging.INFO)
    api_logger.addHandler(all_logs_handler)
    api_logger.addHandler(console_handler)
    api_logger.propagate = False  # Prevent propagation to parent logger
    
    return logger

def get_logger(name='fraud_detection'):
    """Get a logger instance"""
    return logging.getLogger(name) 