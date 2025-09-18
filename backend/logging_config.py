import logging
from logging.handlers import RotatingFileHandler
import os

log_dir = "logs"

def make_rotating_logger(name: str, backups : int = 2):
    return RotatingFileHandler(
        f'{log_dir}/{name}.log',
        maxBytes=50*1024*1024,
        backupCount=backups
    )

def setup_logging():
    """Setup logging configuration for the backend"""
    
    # Create logs directory if it doesn't exist
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

    # File handler for all logs
    all_logs_handler = make_rotating_logger("all", 3)
    all_logs_handler.setLevel(logging.DEBUG)
    all_logs_handler.setFormatter(detailed_formatter)
    
    # File handler for errors only
    error_logs_handler = make_rotating_logger("errors")
    error_logs_handler.setLevel(logging.ERROR)
    error_logs_handler.setFormatter(detailed_formatter)
    
    # File handler for Aerospike Graph specific logs
    graph_logs_handler = make_rotating_logger("graph")
    graph_logs_handler.setLevel(logging.DEBUG)
    graph_logs_handler.setFormatter(detailed_formatter)

    # Separate file handler for fraud transactions
    fraud_handler = make_rotating_logger("fraud_transactions")
    fraud_handler.setLevel(logging.ERROR)
    fraud_handler.setFormatter(fraud_formatter)
    
    # Separate file handler for normal transactions
    normal_handler = make_rotating_logger("normal_transactions")
    normal_handler.setLevel(logging.ERROR)
    normal_handler.setFormatter(normal_formatter)
    
    # Separate file handler for transaction stats
    stats_handler = make_rotating_logger("statistics")
    stats_handler.setLevel(logging.ERROR)
    stats_handler.setFormatter(stats_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(simple_formatter)

    # Add handlers to logger
    logger.addHandler(all_logs_handler)
    logger.addHandler(error_logs_handler)
    logger.addHandler(graph_logs_handler)
    logger.addHandler(console_handler)
    
    # Create specific loggers
    graph_logger = logging.getLogger('fraud_detection.graph')
    graph_logger.setLevel(logging.ERROR)
    graph_logger.addHandler(graph_logs_handler)
    graph_logger.addHandler(console_handler)
    graph_logger.propagate = False  # Prevent propagation to parent logger
    
    api_logger = logging.getLogger('fraud_detection.api')
    api_logger.setLevel(logging.ERROR)
    api_logger.addHandler(all_logs_handler)
    api_logger.addHandler(console_handler)
    api_logger.propagate = False  # Prevent propagation to parent logger
    
    txn_logger = logging.getLogger('fraud_detection.transaction_generator')
    txn_logger.setLevel(logging.ERROR)
    txn_logger.addHandler(normal_handler)
    txn_logger.addHandler(fraud_handler)
    txn_logger.addHandler(console_handler)

    stats_logger = logging.getLogger('fraud_detection.stats')
    stats_logger.setLevel(logging.ERROR)
    stats_logger.addHandler(stats_handler)
    stats_logger.addHandler(console_handler)
    
    return logger

def get_logger(name='fraud_detection'):
    """Get a logger instance"""
    return logging.getLogger(name) 