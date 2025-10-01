import time
import signal
import sys
import os
import psutil
from services.graph_service import GraphService
from services.fraud_service import FraudService
from services.transaction_generator import TransactionGeneratorService
from services.performance_monitor import performance_monitor
from logging_config import setup_logging, get_logger, get_queue_stats, get_queue_contents, clear_queues, shutdown_logging

def setup_cli_logging():
    setup_logging()
    return get_logger('fraud_detection.cli')

logger = setup_cli_logging()

class FraudDetectionCLI:
    def __init__(self):
        print("Initializing Fraud Detection CLI...")
        print("Logs will be written to: logs/all.log, logs/errors.log, etc.")

        self.graph_service = GraphService()
        self.fraud_service = FraudService(self.graph_service)
        self.transaction_generator = TransactionGeneratorService(self.graph_service, self.fraud_service)

        try:
            self.graph_service.connect()
        except Exception as e:
            print(f"Failed to connect to graph database: {e}")
            print("Please ensure the graph database is running and accessible.")
            sys.exit(1)

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)


    def _signal_handler(self, signum, frame):
        print("\nShutting down gracefully...")
        self.shutdown()
        sys.exit(0)

    def _show_logging_stats(self):
        """Show logging queue statistics"""
    stats = get_queue_stats()
    print("\nLogging Queue Status:")
    for queue_name, queue_stats in stats.items():
        utilization = (queue_stats['size'] / queue_stats['maxsize']) * 100
        status = "FULL" if queue_stats['full'] else "OK"
        print(f"  {queue_name:12} {queue_stats['size']:5,}/{queue_stats['maxsize']:5,} ({utilization:5.1f}%) [{status}]")

    def _show_recent_logs(self, queue_name='transaction', count=10):
        """Show recent log entries from a queue"""
        contents = get_queue_contents(queue_name)
        print(f"\nRecent {queue_name} logs ({len(contents)} total):")
        for i, log_record in enumerate(contents[-count:]):
            print(f"  {i+1}. {log_record.getMessage()}")


    def shutdown(self):
        logger.info("Starting graceful shutdown...")
        self.transaction_generator.stop_generation()
        self.fraud_service.shutdown()
        self.graph_service.close()
        shutdown_logging()
        time.sleep(1)
        print("Application shutdown complete")

    def run(self):
        print("\nFraud Detection CLI Ready!")
        print("Type 'help' for available commands")
        print("All detailed logs are written to logs/ directory\n\n")

        while True:
            try:
                status = "[RUNNING]" if performance_monitor.is_running else "[STOPPED]"
                command = input(f"{status} fraud-cli> ").strip().lower()

                if not command:
                    continue
                self._handle_command(command)

            except EOFError:
                print("\nExiting...")
                break
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
                logger.error(f"CLI error: {e}")

    def _handle_command(self, command: str):
        parts = command.split()
        cmd = parts[0] if parts else ""
        args = parts[1:] if len(parts) > 1 else []

        if cmd == "help":
            self._show_help()
        elif cmd == "stats":
            self._show_stats()
        elif cmd in ["performance", "perf"]:
            time_window = 1
            if args:
                try:
                    time_window = int(args[0])
                    if time_window not in [1, 5, 10]:
                        print("Time window must be 1, 5, or 10 minutes. Using default of 1 minute.")
                        time_window = 1
                except ValueError:
                    print("Invalid time window. Using default of 1 minute.")
                    time_window = 1
            self._show_performance(time_window)
        elif cmd in ["fraud", "fraud-perf"]:
            time_window = 1
            if args:
                try:
                    time_window = int(args[0])
                    if time_window not in [1, 5, 10]:
                        print("Time window must be 1, 5, or 10 minutes. Using default of 1 minute.")
                        time_window = 1
                except ValueError:
                    print("Invalid time window. Using default of 1 minute.")
                    time_window = 1
            self._show_fraud_detection_performance(time_window)
        elif cmd in ["bottleneck", "debug"]:
            self._show_bottleneck_analysis()
        elif cmd == "users":
            self._show_users()
        elif cmd in ["transactions", "txns"]:
            self._show_transactions()
        elif cmd == "start":
            if args:
                try:
                    tps = float(args[0])
                    self._start_generator(tps)
                except ValueError:
                    print("Invalid TPS value. Use: start <number>")
            else:
                print("Usage: start <tps>")
        elif cmd == "indexes":
            self._show_indexes()
        elif cmd == "seed":
            self.graph_service.seed_sample_data()
            # Refresh account cache after seeding
            self.transaction_generator.refresh_account_cache()
            print("Bulk Load Succeeded!")
        elif cmd == "stop":
            self._stop_generator()
        elif cmd == "status":
            self._show_generator_status()
        elif cmd == "clear":
            os.system('cls' if os.name == 'nt' else 'clear')
        elif cmd == "clear-txns":
            self._clear_transactions()
            print("The System is now Bulkloading the Vertices back in")
        elif cmd == "clear-logs":
            self._clear_logs()
        elif cmd == "logs":
            self._show_log_info()
        elif cmd == "log" and len(args) > 0:
            if args[0] == "stats":
                self._show_logging_stats()
            elif args[0] == "recent":
                queue_name = args[1] if len(args) > 1 else "transaction"
                self._show_recent_logs(queue_name)
            else:
                print(f"Unknown log command: {args[0]}. Use 'log stats' or 'log recent'")
        elif cmd in ["quit", "exit"]:
            print("Exiting...")
            self.shutdown()
            sys.exit(0)
        elif cmd == "create-fraud-index":
            self._create_fraud_indexes()
        else:
            print(f"Unknown command: {cmd}. Type 'help' for available commands.")

    def _show_help(self):
        print("""
Available Commands:
  help                 - Show this help message
  stats               - Show database statistics
  performance, perf [time]   - Show performance metrics (time: 1, 5, or 10 minutes, default: 1)
  fraud, fraud-perf [time]   - Show fraud detection performance (time: 1, 5, or 10 minutes, default: 1)
  bottleneck, debug   - Show bottleneck analysis and system diagnostics
  users               - Show user statistics
  transactions, txns  - Show transaction statistics
  indexes             - Show database indexes information
  create-fraud-index  - Create Fraud App indexes
  seed                - Bulk load users from data/graph_csv
  start <tps>         - Start generator at specified TPS (e.g., start 50)
  stop                - Stop transaction generator
  status              - Show generator status
  logs                - Show log file information
  clear               - Clear screen
  clear-txns          - Clear all transactions from the graph
  clear-logs          - Clear all log files
  quit, exit          - Exit application

Examples:
  seed                - Bulk load users from existing CSV data
  start 25            - Start generating 25 transactions per second
  start 100           - Start generating 100 transactions per second
  perf                - Show current performance metrics
  fraud               - Show RT1, RT2, RT3 fraud detection latencies
  debug               - Show bottleneck analysis and diagnostics
  stats               - Show database overview
  clear-txns          - Clear all transactions (with confirmation)
  clear-logs          - Clear all log files (with confirmation)
  logs                - Show where logs are written
        """)

    def _show_log_info(self):
        print("""
Logging System: Queue-based with file output
  Files written to:   logs/ directory
  - all.log           All application logs (50MB, 3 backups)
  - transactions.log  High-volume transaction logs (100MB, 5 backups)
  - stats.log         Performance statistics (10MB, 2 backups)

Commands:
  log stats           - Show queue statistics
  log recent          - Show recent log entries
  clear-logs          - Clear in-memory log queues
        """)

    def _show_logging_stats(self):
        """Show logging queue statistics"""
        try:
            stats = get_queue_stats()
            print("\nLogging Queue Statistics:")
            print("=" * 40)
            for queue_name, queue_stats in stats.items():
                utilization = (queue_stats['size'] / queue_stats['maxsize']) * 100 if queue_stats['maxsize'] > 0 else 0
                status = "FULL" if queue_stats['full'] else "OK"
                print(f"  {queue_name.title():12} {queue_stats['size']:5,}/{queue_stats['maxsize']:5,} ({utilization:5.1f}%) [{status}]")
                
            total_queued = sum(q['size'] for q in stats.values())
            print(f"\nTotal Queued Messages: {total_queued:,}")
            
        except Exception as e:
            print(f"Error getting logging stats: {e}")

    def _show_recent_logs(self, queue_name='transaction', count=10):
        """Show recent log entries from a queue"""
        try:
            contents = get_queue_contents(queue_name)
            print(f"\nRecent {queue_name} logs ({len(contents)} total, showing last {count}):")
            print("=" * 60)
            
            if not contents:
                print("  No log entries found")
                return
                
            for i, log_record in enumerate(contents[-count:]):
                try:
                    timestamp = log_record.created
                    level = log_record.levelname
                    message = log_record.getMessage()
                    print(f"  {i+1:2d}. [{level:5}] {message[:80]}{'...' if len(message) > 80 else ''}")
                except Exception as e:
                    print(f"  {i+1:2d}. [ERROR] Could not format log record: {e}")
                    
        except Exception as e:
            print(f"Error getting recent logs: {e}")

    def _show_indexes(self):
        try:
            print("Database Indexes Information")
            print("=" * 50)
            
            result = self.graph_service.inspect_indexes()
            
            if result.get("status") == "success":
                cardinality = result.get("cardinality", {})
                if cardinality:
                    print("\nIndex Cardinality:")
                    for index_name, count in cardinality.items():
                        print(f"  {index_name}: {count:,} entries")
                
                index_list = result.get("index_list", [])
                if index_list and index_list != "Error getting index list":
                    print(f"\nAvailable Indexes ({len(index_list)} total):")
                    for i, index in enumerate(index_list, 1):
                        print(f"  {i}. {index}")
                else:
                    print(f"\nIndex List: {index_list}")
                    
            else:
                print(f"Error: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"Error getting index information: {e}")
            logger.error(f"Error getting index information: {e}")

    def _create_fraud_indexes(self):
        print("Creating fraud detection indexes...")
        try:
            result = self.graph_service.create_fraud_detection_indexes()
            if result.get("status") == "completed":
                print(f"Successfully created {result['successful']}/{result['total_indexes']} indexes")
                for r in result["results"]:
                    status_icon = "SUCCESS" if r["status"] == "created" else "FAIL"
                    print(f"  {status_icon} {r['index']}: {r['status']}")
            else:
                print(f"Error: {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"Error creating indexes: {e}")

    def _show_stats(self):
        try:
            dashboard_stats = self.graph_service.get_dashboard_stats()
            print(f"""
Database Statistics:
  Users:              {dashboard_stats.get('users', 0):,}
  Transactions:       {dashboard_stats.get('txns', 0):,}
  Accounts:           {dashboard_stats.get('accounts', 0):,}
  Devices:            {dashboard_stats.get('devices', 0):,}
  Flagged:            {dashboard_stats.get('flagged', 0):,}
  Total Amount:      ${dashboard_stats.get('amount', 0):,.2f}
  Fraud Rate:        {dashboard_stats.get('fraud_rate', 0):.1f}%
  Health:            {dashboard_stats.get('health', 'unknown')}
            """)
        except Exception as e:
            print(f"Error getting database stats: {e}")
            logger.error(f"Error getting database stats: {e}")

    def _show_performance(self, time_window: int = 1):
        stats = self.transaction_generator.get_performance_stats()

        elapsed_time = stats['elapsed_time']
        if elapsed_time >= 3600:  # More than 1 hour
            time_str = f"{elapsed_time/3600:.1f}h"
        elif elapsed_time >= 60:  # More than 1 minute
            time_str = f"{elapsed_time/60:.1f}m"
        else:
            time_str = f"{elapsed_time:.1f}s"

        print(f"""
Performance Metrics:
  Generator Status:   {'RUNNING' if stats['is_running'] else 'STOPPED'}
  Elapsed Time:       {time_str}
  Target TPS:         {stats['target_tps']:.2f}
  Current TPS:        {stats['current_tps']:.2f}
  Actual TPS:         {stats['actual_tps']:.2f}
  
  Transactions:
    Scheduled:        {stats['total_scheduled']:,}
    Completed:        {stats['total_completed']:,}
    Failed:           {stats['total_failed']:,}
    Success Rate:     {stats['success_rate']:.1f}%
  
  Queue:
    Current Size:     {stats['queue_size']}
  
  Total Latency (ms):
    Average:          {stats['avg_latency_ms']:.1f}
    Minimum:          {stats['min_latency_ms']:.1f}
    Maximum:          {stats['max_latency_ms']:.1f}
  
  Execution Latency (ms):
    Average:          {stats['avg_exec_latency_ms']:.1f}
    Minimum:          {stats['min_exec_latency_ms']:.1f}
    Maximum:          {stats['max_exec_latency_ms']:.1f}
  
  Latency Breakdown (ms):
    Queue Wait:       {stats.get('avg_queue_wait_ms', 0):.1f} avg ({stats.get('min_queue_wait_ms', 0):.1f}-{stats.get('max_queue_wait_ms', 0):.1f})
    DB Operations:    {stats.get('avg_db_latency_ms', 0):.1f} avg ({stats.get('min_db_latency_ms', 0):.1f}-{stats.get('max_db_latency_ms', 0):.1f})
    Fraud Detection:  {stats.get('avg_fraud_latency_ms', 0):.1f} avg ({stats.get('min_fraud_latency_ms', 0):.1f}-{stats.get('max_fraud_latency_ms', 0):.1f})
        """)

        self._show_fraud_detection_performance(time_window)

    def _show_fraud_detection_performance(self, time_window: int = 1):
        try:
            # Get recent fraud detection stats for the specified time window
            rt1_stats = performance_monitor.get_rt1_stats(time_window)
            rt2_stats = performance_monitor.get_rt2_stats(time_window)
            rt3_stats = performance_monitor.get_rt3_stats(time_window)

            time_desc = f"last {time_window} min" if time_window > 1 else "last 1 min"
            
            print(f"""
  Fraud Detection Performance ({time_desc}):
    RT1 (Flagged Accounts):
      Queries:          {rt1_stats['total_queries']:,}
      Latency (ms):     {rt1_stats['avg_execution_time']:.1f} avg, {rt1_stats['min_execution_time']:.1f}-{rt1_stats['max_execution_time']:.1f} range
      Success Rate:     {rt1_stats['success_rate']:.1f}%
      QPS:              {rt1_stats['queries_per_second']:.1f}
    
    RT2 (Transaction Partners):
      Queries:          {rt2_stats['total_queries']:,}
      Latency (ms):     {rt2_stats['avg_execution_time']:.1f} avg, {rt2_stats['min_execution_time']:.1f}-{rt2_stats['max_execution_time']:.1f} range
      Success Rate:     {rt2_stats['success_rate']:.1f}%
      QPS:              {rt2_stats['queries_per_second']:.1f}
    
    RT3 (Flagged Devices):
      Queries:          {rt3_stats['total_queries']:,}
      Latency (ms):     {rt3_stats['avg_execution_time']:.1f} avg, {rt3_stats['min_execution_time']:.1f}-{rt3_stats['max_execution_time']:.1f} range
      Success Rate:     {rt3_stats['success_rate']:.1f}%
      QPS:              {rt3_stats['queries_per_second']:.1f}
            """)

        except Exception as e:
            print(f"\n  Fraud Detection Performance: Error retrieving stats - {e}")
            logger.error(f"Error getting fraud detection performance: {e}")

    def _show_bottleneck_analysis(self):
        import threading
        import gc
        disk_io_start = psutil.disk_io_counters()
        time.sleep(1)
        disk_io_end = psutil.disk_io_counters()
        read_rate = (disk_io_end.read_bytes - disk_io_start.read_bytes) / (1024**2)  # MB/s
        write_rate = (disk_io_end.write_bytes - disk_io_start.write_bytes) / (1024**2)  # MB/s
        print(f"""
=== BOTTLENECK ANALYSIS ===

System Resources:
  CPU Usage:           {psutil.cpu_percent(interval=1):.1f}%
  Memory Usage:        {psutil.virtual_memory().percent:.1f}%
  Available Memory:    {psutil.virtual_memory().available / (1024**3):.1f} GB
  Disk I/O Rate:       Read: {read_rate:.1f} MB/s, Write: {write_rate:.1f} MB/s
Total Disk I/O:      Read: {disk_io_end.read_bytes / (1024**3):.1f} GB, Write: {disk_io_end.write_bytes / (1024**3):.1f} GB


Python Process:
  Thread Count:        {threading.active_count()}
  GC Collections:      Gen0: {gc.get_count()[0]}, Gen1: {gc.get_count()[1]}, Gen2: {gc.get_count()[2]}
  Memory Objects:      {len(gc.get_objects()):,}
        """)

        active_threads = threading.enumerate()
        thread_groups = {}
        for thread in active_threads:
            prefix = thread.name.split('-')[0] if '-' in thread.name else thread.name
            thread_groups[prefix] = thread_groups.get(prefix, 0) + 1
        
        print("Thread Analysis:")
        total_threads = len(active_threads)
        cpu_count = psutil.cpu_count()
        print(f"  Total Threads:       {total_threads}")
        print(f"  CPU Cores:           {cpu_count}")
        print(f"  Thread/Core Ratio:   {total_threads/cpu_count:.1f}:1")
        
        if total_threads > cpu_count * 4:
            print(f"WARNING: High thread count may cause context switching overhead")
        elif total_threads > cpu_count * 2:
            print(f"CAUTION: Thread count is high relative to CPU cores")
        else:
            print(f"Thread count looks reasonable")
            
        print("\nThread Groups:")
        for group, count in sorted(thread_groups.items()):
            print(f"  {group:20} {count:3d} threads")
            
        print("\nActive Threads:")
        for thread in active_threads:
            status = 'ALIVE' if thread.is_alive() else 'DEAD'
            daemon = 'DAEMON' if thread.daemon else 'MAIN'
            print(f"  - {thread.name:30} {status:5} {daemon}")

        analysis = self.transaction_generator.get_bottleneck_analysis()
        pool_status = analysis['pool_status']
        scheduler_status = analysis['scheduler_status']
        
        print(f"""
Thread Pool Analysis:
  Pool Size:           {pool_status.get('pool_size', 0)}
  Active Threads:      {pool_status.get('active_threads', 0)}
  Queue Size:          {pool_status.get('queue_size', 0)}
  Running:             {'YES' if pool_status.get('running', False) else 'NO'}
        """)

        print(f"""
Scheduler Analysis:
  Scheduler Workers:   {scheduler_status.get('scheduler_workers', 0)}
  Target TPS:          {scheduler_status.get('target_tps', 0):.2f}
  Scheduler Status:    {'RUNNING' if scheduler_status.get('running', False) else 'STOPPED'}
        """)

        stats = analysis['performance_stats']
        if stats['total_completed'] > 0:
            avg_total = stats['avg_latency_ms']
            avg_exec = stats['avg_exec_latency_ms']
            avg_queue_wait = stats.get('avg_queue_wait_ms', avg_total - avg_exec)

            print(f"""
Latency Breakdown:
  Total Latency:       {avg_total:.1f}ms
  Execution Time:      {avg_exec:.1f}ms
  Queue Wait Time:     {avg_queue_wait:.1f}ms
  Queue Wait %:        {(avg_queue_wait/avg_total)*100 if avg_total > 0 else 0:.1f}%
            """)

        try:
            if hasattr(self.graph_service, 'client') and self.graph_service.client:
                print("Database Connection:     ACTIVE")
            else:
                print("Database Connection:     INACTIVE")
        except:
            print("Database Connection:     ERROR")

        self._show_bottleneck_recommendations(stats)

    def _show_bottleneck_recommendations(self, stats):
        print("\n=== BOTTLENECK RECOMMENDATIONS ===")

        if stats['total_completed'] == 0:
            print("- No transactions completed - check if generator is running")
            return

        avg_total = stats['avg_latency_ms']
        avg_exec = stats['avg_exec_latency_ms']
        avg_queue_wait = stats.get('avg_queue_wait_ms', 0)
        avg_db_latency = stats.get('avg_db_latency_ms', 0)
        avg_fraud_latency = stats.get('avg_fraud_latency_ms', 0)
        success_rate = stats['success_rate']
        queue_size = stats['queue_size']

        if avg_queue_wait > 0:
            queue_wait_pct = (avg_queue_wait / avg_total) * 100
            db_latency_pct = (avg_db_latency / avg_total) * 100
            fraud_latency_pct = (avg_fraud_latency / avg_total) * 100 if avg_fraud_latency > 0 else 0
            
            print(f"LATENCY BREAKDOWN ANALYSIS:")
            print(f"   Queue Wait:      {avg_queue_wait:.1f}ms ({queue_wait_pct:.1f}%)")
            print(f"   DB Operations:   {avg_db_latency:.1f}ms ({db_latency_pct:.1f}%)")
            if avg_fraud_latency > 0:
                print(f"   Fraud Detection: {avg_fraud_latency:.1f}ms ({fraud_latency_pct:.1f}%)")
            print()

        if avg_queue_wait > 100:
            print(f"HIGH QUEUE WAIT TIME ({avg_queue_wait:.1f}ms)")
            print("   - Workers can't keep up with scheduling rate")
            print("   - Increase worker pool size")
            print("   - Check if workers are blocked on I/O")
            print("   - Consider reducing target TPS")
            print()

        if avg_db_latency > 200:
            print(f"HIGH DATABASE LATENCY ({avg_db_latency:.1f}ms)")
            print("   - Database operations are slow")
            print("   - Check network latency to database")
            print("   - Consider adding database indexes")
            print("   - Review connection pool settings")
            print("   - Check if DNS resolution is cached")
            print()

        if avg_fraud_latency > 150:
            print(f"HIGH FRAUD DETECTION LATENCY ({avg_fraud_latency:.1f}ms)")
            print("   - RT1/RT2/RT3 queries are slow")
            print("   - Consider optimizing fraud detection queries")
            print("   - Check fraud detection thread pool size")
            print("   - Review graph indexes for fraud queries")
            print()

        if avg_exec > 100:
            print(f"HIGH EXECUTION TIME ({avg_exec:.1f}ms)")
            print("   - Database queries are slow")
            print("   - Check network latency to database")
            print("   - Consider adding database indexes")
            print("   - Enable more caching")

        if success_rate < 95:
            print(f"LOW SUCCESS RATE ({success_rate:.1f}%)")
            print("   - Workers are timing out or failing")
            print("   - Check database connectivity")
            print("   - Review error logs")

        if queue_size > 100:
            print(f"LARGE QUEUE SIZE ({queue_size})")
            print("   - Workers can't keep up with scheduling")
            print("   - Increase worker pool size")
            print("   - Reduce target TPS")

        cpu_usage = psutil.cpu_percent()
        if cpu_usage > 80:
            print(f"HIGH CPU USAGE ({cpu_usage:.1f}%)")
            print("   - CPU is bottleneck")
            print("   - Reduce worker count")
            print("   - Optimize query complexity")

        memory_usage = psutil.virtual_memory().percent
        if memory_usage > 85:
            print(f"HIGH MEMORY USAGE ({memory_usage:.1f}%)")
            print("   - Memory is bottleneck")
            print("   - Reduce cache sizes")
            print("   - Check for memory leaks")

        # Good performance
        if avg_queue_wait < 20 and avg_exec < 50 and success_rate > 95 and queue_size < 10:
            print("PERFORMANCE LOOKS GOOD")
            print("   - All metrics within acceptable ranges")
            print("   - Consider increasing target TPS")

    def _show_users(self):
        try:
            user_stats = self.graph_service.get_user_stats()
            print(f"""
User Statistics:
  Total Users:        {user_stats.get('total_users', 0):,}
  Active Users:       {user_stats.get('active_users', 0):,}
  Flagged Users:      {user_stats.get('flagged_users', 0):,}
            """)
        except Exception as e:
            print(f"Error getting user stats: {e}")
            logger.error(f"Error getting user stats: {e}")

    def _show_transactions(self):
        try:
            txn_stats = self.graph_service.get_transaction_stats()
            print(f"""
Transaction Statistics:
  Total Transactions: {txn_stats.get('total_txns', 0):,}
  Blocked:           {txn_stats.get('total_blocked', 0):,}
  Under Review:      {txn_stats.get('total_review', 0):,}
  Clean:             {txn_stats.get('total_clean', 0):,}
            """)
        except Exception as e:
            print(f"Error getting transaction stats: {e}")
            logger.error(f"Error getting transaction stats: {e}")

    def _start_generator(self, tps: float):
        if tps <= 0:
            print("TPS must be greater than 0")
            return

        if tps > 1000:
            print("Warning: TPS > 1000 may cause performance issues")

        success = self.transaction_generator.start_generation(tps)
        if success:
            print(f"Started transaction generator at {tps} TPS")
            print("Monitor progress with 'perf' command or check logs/all.log")
        else:
            print("Generator is already running. Use 'stop' first.")

    def _stop_generator(self):
        self.transaction_generator.stop_generation()
        print("Stopped transaction generator")

    def _show_generator_status(self):
        """Show detailed generator status"""
        # Get stats from transaction generator service
        stats = self.transaction_generator.get_performance_stats()

        status = "RUNNING" if stats['is_running'] else "STOPPED"

        # Format elapsed time
        elapsed_time = stats['elapsed_time']
        if elapsed_time >= 3600:  # More than 1 hour
            time_str = f"{elapsed_time/3600:.1f}h"
        elif elapsed_time >= 60:  # More than 1 minute
            time_str = f"{elapsed_time/60:.1f}m"
        else:
            time_str = f"{elapsed_time:.1f}s"

        print(f"""
Generator Status: {status}
  Elapsed Time:       {time_str}
  Target TPS:         {stats['target_tps']:.2f}
  Current TPS:        {stats['current_tps']:.2f}
  Actual TPS:         {stats['actual_tps']:.2f}
  Queue Size:         {stats['queue_size']}
  Total Scheduled:    {stats['total_scheduled']:,}
  Total Completed:    {stats['total_completed']:,}
  Total Failed:       {stats['total_failed']:,}
  Success Rate:       {stats['success_rate']:.1f}%
        """)

    def _clear_transactions(self):
        print("Warning: This will delete ALL transactions from the graph database.")
        confirm = input("Are you sure you want to continue? (yes/no): ").strip().lower()

        if confirm in ['yes', 'y']:
            print("Clearing transactions...")
            try:
                success = self.graph_service.drop_all_transactions_large()
                if success:
                    print("Successfully cleared all transactions from the graph.")
                    logger.info("All transactions cleared from graph via CLI")
                else:
                    print("Failed to clear transactions. Check logs for details.")
                    logger.error("Failed to clear transactions via CLI")
            except Exception as e:
                print(f"Error clearing transactions: {e}")
                logger.error(f"Error clearing transactions via CLI: {e}")
        else:
            print("Transaction clearing cancelled.")

    def _clear_logs(self):
        try:
            stats = get_queue_stats()
            if not stats:
                print("No logging queues found.")
                return

            total_messages = sum(q['size'] for q in stats.values())
            if total_messages == 0:
                print("All logging queues are already empty.")
                return

            print(f"Warning: This will clear all messages from {len(stats)} logging queues:")
            for queue_name, queue_stats in stats.items():
                print(f"  - {queue_name.title()} Queue: {queue_stats['size']:,} messages")

            print(f"\nTotal messages to clear: {total_messages:,}")
            confirm = input("\nAre you sure you want to clear all log queues? (yes/no): ").strip().lower()

            if confirm in ['yes', 'y']:
                print("Clearing log queues...")
                clear_queues()
                
                new_stats = get_queue_stats()
                remaining_messages = sum(q['size'] for q in new_stats.values())
                cleared_messages = total_messages - remaining_messages
                
                print(f"Log clearing complete: {cleared_messages:,} messages cleared")
                if remaining_messages > 0:
                    print(f"Warning: {remaining_messages:,} messages remain (may have been added during clearing)")
                
                logger.info(f"Cleared {cleared_messages:,} log messages via CLI")
            else:
                print("Log clearing cancelled.")
                
        except Exception as e:
            print(f"Error clearing logs: {e}")
            logger.error(f"Error clearing logs via CLI: {e}")

def main():
    try:
        cli = FraudDetectionCLI()
        print("Process PID: " + str(os.getpid()))
        cli.run()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"Fatal error: {e}")
        print("Check logs/all.log and logs/errors.log for detailed error information")
        sys.exit(1)

if __name__ == "__main__":
    main()
