import logging
import queue
import threading
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
import os
import atexit

log_dir = "logs"

def setup_logging():
    """Setup queue-based logging with file output for high performance"""
    
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create the main logger
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

    # Create queues for different log types (larger sizes to prevent overflow)
    main_log_queue = queue.Queue(maxsize=50000)  # Increased from 10000
    transaction_log_queue = queue.Queue(maxsize=25000)  # Increased from 5000
    stats_log_queue = queue.Queue(maxsize=5000)  # Increased from 1000

    # Store queues globally for access
    global _log_queues
    _log_queues = {
        'main': main_log_queue,
        'transaction': transaction_log_queue,
        'stats': stats_log_queue
    }

    # Create file handlers (these will run in background threads)
    all_logs_handler = RotatingFileHandler(
        os.path.join(log_dir, "all.log"),
        maxBytes=50 * 1024 * 1024,  # 50MB per file
        backupCount=3,
        encoding='utf-8'
    )
    all_logs_handler.setLevel(logging.DEBUG)
    all_logs_handler.setFormatter(detailed_formatter)
    
    transaction_logs_handler = RotatingFileHandler(
        os.path.join(log_dir, "transactions.log"),
        maxBytes=100 * 1024 * 1024,  # 100MB per file (high volume)
        backupCount=5,
        encoding='utf-8'
    )
    transaction_logs_handler.setLevel(logging.INFO)
    transaction_logs_handler.setFormatter(simple_formatter)
    
    stats_logs_handler = RotatingFileHandler(
        os.path.join(log_dir, "stats.log"),
        maxBytes=10 * 1024 * 1024,  # 10MB per file
        backupCount=2,
        encoding='utf-8'
    )
    stats_logs_handler.setLevel(logging.INFO)
    stats_logs_handler.setFormatter(simple_formatter)

    # Console handler (only for critical errors)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(simple_formatter)

    # Create QueueListeners (background threads that handle actual file I/O)
    main_listener = QueueListener(
        main_log_queue, 
        all_logs_handler,
        respect_handler_level=True
    )
    
    transaction_listener = QueueListener(
        transaction_log_queue,
        transaction_logs_handler,
        respect_handler_level=True
    )
    
    stats_listener = QueueListener(
        stats_log_queue,
        stats_logs_handler,
        respect_handler_level=True
    )

    # Start the background listeners
    main_listener.start()
    transaction_listener.start()
    stats_listener.start()

    # Store listeners globally so they can be stopped on shutdown
    global _log_listeners
    _log_listeners = [main_listener, transaction_listener, stats_listener]
    
    # Register shutdown handler
    atexit.register(shutdown_logging)

    # Create QueueHandlers (these are what the loggers actually use)
    main_queue_handler = QueueHandler(main_log_queue)
    transaction_queue_handler = QueueHandler(transaction_log_queue)
    stats_queue_handler = QueueHandler(stats_log_queue)

    # Configure main logger
    logger.addHandler(main_queue_handler)
    logger.addHandler(console_handler)
    
    # Create specific loggers with appropriate queue handlers
    
    # Graph service logger
    graph_logger = logging.getLogger('fraud_detection.graph')
    graph_logger.setLevel(logging.INFO)
    graph_logger.addHandler(main_queue_handler)
    graph_logger.addHandler(console_handler)
    graph_logger.propagate = False
    
    # API logger
    api_logger = logging.getLogger('fraud_detection.api')
    api_logger.setLevel(logging.INFO)
    api_logger.addHandler(main_queue_handler)
    api_logger.addHandler(console_handler)
    api_logger.propagate = False
    
    # Transaction generator logger (uses transaction queue for high-volume logs)
    txn_logger = logging.getLogger('fraud_detection.transaction_generator')
    txn_logger.setLevel(logging.INFO)
    txn_logger.addHandler(transaction_queue_handler)  # High-volume transaction logs
    txn_logger.addHandler(console_handler)  # Errors still go to console
    txn_logger.propagate = False

    # Stats logger (uses dedicated stats queue)
    stats_logger = logging.getLogger('fraud_detection.stats')
    stats_logger.setLevel(logging.INFO)
    stats_logger.addHandler(stats_queue_handler)
    stats_logger.addHandler(console_handler)
    stats_logger.propagate = False
    
    # Fraud service logger
    fraud_logger = logging.getLogger('fraud_detection.fraud')
    fraud_logger.setLevel(logging.INFO)
    fraud_logger.addHandler(main_queue_handler)
    fraud_logger.addHandler(console_handler)
    fraud_logger.propagate = False
    
    # Performance monitor logger
    perf_logger = logging.getLogger('fraud_detection.performance')
    perf_logger.setLevel(logging.INFO)
    perf_logger.addHandler(main_queue_handler)
    perf_logger.addHandler(console_handler)
    perf_logger.propagate = False
    
    return logger

def get_logger(name='fraud_detection'):
    """Get a logger instance"""
    return logging.getLogger(name)

def get_queue_contents(queue_name='main'):
    """Get current contents of a specific log queue for debugging"""
    global _log_queues
    if '_log_queues' not in globals() or queue_name not in _log_queues:
        return []
    
    queue_obj = _log_queues[queue_name]
    contents = []
    
    # Non-destructively peek at queue contents
    temp_items = []
    try:
        while not queue_obj.empty():
            item = queue_obj.get_nowait()
            temp_items.append(item)
            contents.append(item)
    except:
        pass
    
    # Put items back
    for item in temp_items:
        try:
            queue_obj.put_nowait(item)
        except:
            pass
    
    return contents

def get_queue_stats():
    """Get statistics about all log queues"""
    global _log_queues
    if '_log_queues' not in globals():
        return {}
    
    stats = {}
    for name, queue_obj in _log_queues.items():
        stats[name] = {
            'size': queue_obj.qsize(),
            'maxsize': queue_obj.maxsize,
            'full': queue_obj.full(),
            'empty': queue_obj.empty()
        }
    
    return stats

def clear_queues():
    """Clear all log queues"""
    global _log_queues
    if '_log_queues' not in globals():
        return
    
    for name, queue_obj in _log_queues.items():
        while not queue_obj.empty():
            try:
                queue_obj.get_nowait()
            except:
                break

def shutdown_logging():
    """Shutdown all queue listeners gracefully"""
    global _log_listeners
    if '_log_listeners' in globals():
        for listener in _log_listeners:
            listener.stop()

# Global variables
_log_queues = {}
_log_listeners = []
