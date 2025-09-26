"""
Performance Monitoring Service
Tracks Gremlin query latencies and performance metrics for fraud detection methods

This service monitors the performance of RT1, RT2, and RT3 fraud detection
methods and provides real-time metrics for the frontend dashboard.
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, Any, List
from collections import deque
import statistics

# Setup logging
logger = logging.getLogger('fraud_detection.performance')

class PerformanceMonitor:
    """Performance monitoring for fraud detection methods"""
    
    def __init__(self, max_history: int = 1000000):
        self.max_history = max_history
        # Background executor for async processing (eliminates lock contention)
        self.background_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="perf_background")

        # Performance data storage
        self.rt1_metrics = deque(maxlen=max_history)
        self.rt2_metrics = deque(maxlen=max_history)
        self.rt3_metrics = deque(maxlen=max_history)
        
        # Real-time counters
        self.rt1_counter = 0
        self.rt2_counter = 0
        self.rt3_counter = 0
        
        # Success/failure counters
        self.rt1_success = 0
        self.rt1_failure = 0
        self.rt2_success = 0
        self.rt2_failure = 0
        self.rt3_success = 0
        self.rt3_failure = 0
        
        # Transaction generation metrics
        self.transaction_metrics = deque(maxlen=max_history)
        self.total_scheduled = 0
        self.total_completed = 0
        self.total_failed = 0
        self.completion_times = deque(maxlen=100)
        self.latencies = deque(maxlen=1000)
        self.execution_latencies = deque(maxlen=1000)
        
        # Transaction generation state
        self.is_running = False
        self.target_tps = 0.0
        self.current_tps = 0.0
        self.start_time = None
        self.elapsed_time = 0.0
        self.queue_size = 0
        
        # Keep a minimal lock only for reading data (CLI queries)
        self._read_lock = threading.RLock()
        
        logger.info("Async Performance monitor initialized")
    
    def record_rt1_performance(self, execution_time: float, success: bool = True, 
                              query_complexity: str = "1-hop lookup", cache_hit: bool = False):
        """Record RT1 performance metrics"""
        self.background_executor.submit(
            self._record_rt1_performance_background,
            execution_time, success, query_complexity, cache_hit
        )

    def _record_rt1_performance_background(self, execution_time: float, success: bool,
                                         query_complexity: str, cache_hit: bool):
        """Background processing for RT1 metrics - no locks needed (single thread)"""
        metric = {
            'timestamp': datetime.now(),
            'execution_time': execution_time,
            'success': success,
            'query_complexity': query_complexity,
            'cache_hit': cache_hit,
            'method': 'RT1'
        }
        self.rt1_metrics.append(metric)
        self.rt1_counter += 1

        if success:
            self.rt1_success += 1
        else:
            self.rt1_failure += 1
    
    def record_rt2_performance(self, execution_time: float, success: bool = True,
                              query_complexity: str = "multi-hop network", cache_hit: bool = False):
        """Record RT2 performance metrics - NON-BLOCKING"""
        self.background_executor.submit(
            self._record_rt2_performance_background,
            execution_time, success, query_complexity, cache_hit
        )
    
    def _record_rt2_performance_background(self, execution_time: float, success: bool,
                                         query_complexity: str, cache_hit: bool):
        """Background processing for RT2 metrics - no locks needed (single thread)"""
        metric = {
            'timestamp': datetime.now(),
            'execution_time': execution_time,
            'success': success,
            'query_complexity': query_complexity,
            'cache_hit': cache_hit,
            'method': 'RT2'
        }
        self.rt2_metrics.append(metric)
        self.rt2_counter += 1

        if success:
            self.rt2_success += 1
        else:
            self.rt2_failure += 1
    
    def record_rt3_performance(self, execution_time: float, success: bool = True,
                              query_complexity: str = "multi-hop network", cache_hit: bool = False):
        """Record RT3 performance metrics - NON-BLOCKING"""
        self.background_executor.submit(
            self._record_rt3_performance_background,
            execution_time, success, query_complexity, cache_hit
        )
    
    def _record_rt3_performance_background(self, execution_time: float, success: bool,
                                         query_complexity: str, cache_hit: bool):
        """Background processing for RT3 metrics - no locks needed (single thread)"""
        metric = {
            'timestamp': datetime.now(),
            'execution_time': execution_time,
            'success': success,
            'query_complexity': query_complexity,
            'cache_hit': cache_hit,
            'method': 'RT3'
        }
        self.rt3_metrics.append(metric)
        self.rt3_counter += 1

        if success:
            self.rt3_success += 1
        else:
            self.rt3_failure += 1
    
    # Transaction generation performance tracking methods
    def record_transaction_scheduled(self):
        """Record a transaction was scheduled - NON-BLOCKING"""
        self.background_executor.submit(self._record_transaction_scheduled_background)
    
    def _record_transaction_scheduled_background(self):
        """Background processing for transaction scheduling - no locks needed"""
        self.total_scheduled += 1

    def record_transaction_completed(self, latency_ms: float, execution_latency_ms: float = None):
        """Record a transaction completion - NON-BLOCKING"""
        self.background_executor.submit(
            self._record_transaction_completed_background,
            latency_ms, execution_latency_ms
        )
    
    def _record_transaction_completed_background(self, latency_ms: float, execution_latency_ms: float = None):
        """Background processing for transaction completion - no locks needed (single thread)"""
        metric = {
            'timestamp': datetime.now(),
            'latency_ms': latency_ms,
            'execution_latency_ms': execution_latency_ms,
            'success': True,
            'method': 'TRANSACTION_GENERATION'
        }

        self.transaction_metrics.append(metric)
        self.total_completed += 1
        self.latencies.append(latency_ms)
        if execution_latency_ms is not None:
            self.execution_latencies.append(execution_latency_ms)
        self.completion_times.append(time.time())
        self._update_current_tps()  # Now safe since single-threaded

    def record_transaction_failed(self):
        """Record a transaction failure - NON-BLOCKING"""
        self.background_executor.submit(self._record_transaction_failed_background)
    
    def _record_transaction_failed_background(self):
        """Background processing for transaction failure - no locks needed"""
        self.total_failed += 1

    def _update_current_tps(self):
        """Update current TPS based on recent completions"""
        now = time.time()
        # Count completions in last second
        recent_completions = sum(1 for t in self.completion_times if now - t <= 1.0)
        self.current_tps = float(recent_completions)

    def set_generation_state(self, is_running: bool, target_tps: float = 0.0, queue_size: int = 0):
        """Set transaction generation state"""
        with self._read_lock:
            self.is_running = is_running
            self.target_tps = target_tps
            self.queue_size = queue_size
            
            if is_running and self.start_time is None:
                self.start_time = time.time()
            elif not is_running and self.start_time is not None:
                self.elapsed_time = time.time() - self.start_time

    def reset_transaction_metrics(self):
        """Reset transaction generation metrics"""
        with self._read_lock:
            self.transaction_metrics.clear()
            self.total_scheduled = 0
            self.total_completed = 0
            self.total_failed = 0
            self.completion_times.clear()
            self.latencies.clear()
            self.execution_latencies.clear()
            self.start_time = None
            self.elapsed_time = 0.0
            self.current_tps = 0.0

    def get_transaction_stats(self) -> Dict[str, Any]:
        """Get transaction generation statistics"""
        with self._read_lock:
            if self.latencies:
                avg_latency = sum(self.latencies) / len(self.latencies)
                min_latency = min(self.latencies)
                max_latency = max(self.latencies)
            else:
                avg_latency = min_latency = max_latency = 0.0

            # Calculate execution-only latencies
            if self.execution_latencies:
                avg_exec_latency = sum(self.execution_latencies) / len(self.execution_latencies)
                min_exec_latency = min(self.execution_latencies)
                max_exec_latency = max(self.execution_latencies)
            else:
                avg_exec_latency = min_exec_latency = max_exec_latency = 0.0

            # Calculate elapsed time and actual TPS
            if self.start_time and self.is_running:
                self.elapsed_time = time.time() - self.start_time
            elif not self.is_running and self.elapsed_time == 0.0:
                self.elapsed_time = 0.0

            # Calculate actual TPS based on completed transactions and elapsed time
            actual_tps = (self.total_completed / max(0.01, self.elapsed_time)) if self.elapsed_time > 0 else 0.0

            return {
                'is_running': self.is_running,
                'target_tps': self.target_tps,
                'current_tps': self.current_tps,
                'actual_tps': actual_tps,
                'elapsed_time': self.elapsed_time,
                'total_scheduled': self.total_scheduled,
                'total_completed': self.total_completed,
                'total_failed': self.total_failed,
                'queue_size': self.queue_size,
                'avg_latency_ms': avg_latency,
                'min_latency_ms': min_latency,
                'max_latency_ms': max_latency,
                'avg_exec_latency_ms': avg_exec_latency,
                'min_exec_latency_ms': min_exec_latency,
                'max_exec_latency_ms': max_exec_latency,
                'success_rate': (self.total_completed / max(1, self.total_scheduled)) * 100
            }

    def get_rt1_stats(self, time_window_minutes: int = 5) -> Dict[str, Any]:
        """Get RT1 performance statistics"""
        return self._get_method_stats(self.rt1_metrics, time_window_minutes, 'RT1')
    
    def get_rt2_stats(self, time_window_minutes: int = 5) -> Dict[str, Any]:
        """Get RT2 performance statistics"""
        return self._get_method_stats(self.rt2_metrics, time_window_minutes, 'RT2')
    
    def get_rt3_stats(self, time_window_minutes: int = 5) -> Dict[str, Any]:
        """Get RT3 performance statistics"""
        return self._get_method_stats(self.rt3_metrics, time_window_minutes, 'RT3')
    
    def _get_method_stats(self, metrics: deque, time_window_minutes: int, method: str) -> Dict[str, Any]:
        """Calculate performance statistics for a method"""
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        
        # Filter metrics within time window
        recent_metrics = [m for m in metrics if m['timestamp'] >= cutoff_time]

        if not recent_metrics:
            return {
                'method': method,
                'avg_execution_time': 0,
                'max_execution_time': 0,
                'min_execution_time': 0,
                'total_queries': 0,
                'success_rate': 0,
                'queries_per_second': 0,
                'cache_enabled': self._get_cache_status(method)
            }
        
        execution_times = [m['execution_time'] for m in recent_metrics]
        success_count = sum(1 for m in recent_metrics if m['success'])
        
        # Calculate queries per second
        time_span = (datetime.now() - cutoff_time).total_seconds()
        queries_per_second = len(recent_metrics) / time_span if time_span > 0 else 0
        
        return {
            'method': method,
            'avg_execution_time': round(statistics.mean(execution_times), 2),
            'max_execution_time': round(max(execution_times), 2),
            'min_execution_time': round(min(execution_times), 2),
            'total_queries': len(recent_metrics),
            'success_rate': round((success_count / len(recent_metrics)) * 100, 1),
            'queries_per_second': round(queries_per_second, 2),
            'cache_enabled': self._get_cache_status(method)
        }
    
    
    def _get_cache_status(self, method: str) -> str:
        """Get cache status for each method"""
        cache_status = {
            'RT1': 'Enabled (10min TTL)',
            'RT2': 'Disabled (real-time network)',
            'RT3': 'Enabled (5min TTL)'
        }
        return cache_status.get(method, 'Unknown')
    
    def get_all_stats(self, time_window_minutes: int = 5) -> Dict[str, Any]:
        """Get performance statistics for all methods"""
        # Don't acquire lock here - let individual methods handle their own locking
        return {
            'rt1': self.get_rt1_stats(time_window_minutes),
            'rt2': self.get_rt2_stats(time_window_minutes),
            'rt3': self.get_rt3_stats(time_window_minutes),
            'transaction_generation': self.get_transaction_stats(),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_recent_timeline_data(self, minutes: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Get timeline data for charts"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)

        # Use a single lock acquisition to get all timeline data atomically
        with self._read_lock:
            rt1_timeline = [
                {'timestamp': m['timestamp'].isoformat(), 'execution_time': m['execution_time'], 'method': 'RT1'}
                for m in self.rt1_metrics if m['timestamp'] >= cutoff_time
            ]

            rt2_timeline = [
                {'timestamp': m['timestamp'].isoformat(), 'execution_time': m['execution_time'], 'method': 'RT2'}
                for m in self.rt2_metrics if m['timestamp'] >= cutoff_time
            ]

            rt3_timeline = [
                {'timestamp': m['timestamp'].isoformat(), 'execution_time': m['execution_time'], 'method': 'RT3'}
                for m in self.rt3_metrics if m['timestamp'] >= cutoff_time
            ]
        
        return {
            'rt1': rt1_timeline,
            'rt2': rt2_timeline,
            'rt3': rt3_timeline
        }
    
    def reset_metrics(self):
        """Reset all performance metrics"""
        with self._read_lock:
            self.rt1_metrics.clear()
            self.rt2_metrics.clear()
            self.rt3_metrics.clear()

            self.rt1_counter = 0
            self.rt2_counter = 0
            self.rt3_counter = 0

            self.rt1_success = 0
            self.rt1_failure = 0
            self.rt2_success = 0
            self.rt2_failure = 0
            self.rt3_success = 0
            self.rt3_failure = 0
            
            # Reset transaction generation metrics
            self.transaction_metrics.clear()
            self.total_scheduled = 0
            self.total_completed = 0
            self.total_failed = 0
            self.completion_times.clear()
            self.latencies.clear()
            self.execution_latencies.clear()
            self.start_time = None
            self.elapsed_time = 0.0
            self.current_tps = 0.0
        
        logger.info("Performance metrics reset")

# Global performance monitor instance
performance_monitor = PerformanceMonitor()
