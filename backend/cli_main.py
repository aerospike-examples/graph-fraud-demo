import time
import signal
import sys
import os
import psutil
from services.graph_service import GraphService
from services.fraud_service import FraudService
from services.transaction_generator import TransactionGeneratorService
from services.performance_monitor import performance_monitor
from logging_config import setup_logging

def setup_cli_logging():
    return setup_logging()

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

    def shutdown(self):
        logger.info("Starting graceful shutdown...")
        self.transaction_generator.stop_generation()
        self.graph_service.close()
        time.sleep(2)
        logger.info("Application shutdown complete")

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
            print("Bulk Load Succeeded!")
        elif cmd == "stop":
            self._stop_generator()
        elif cmd == "status":
            self._show_generator_status()
        elif cmd == "clear":
            os.system('cls' if os.name == 'nt' else 'clear')
        elif cmd == "clear-txns":
            self._clear_transactions()
        elif cmd == "clear-logs":
            self._clear_logs()
        elif cmd == "logs":
            self._show_log_info()
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
Log Files Location: logs/
  all.log             - All application logs
  errors.log          - Error logs only
  graph.log           - Graph database logs
  fraud_transactions.log - Fraud transaction logs
  normal_transactions.log - Normal transaction logs
  statistics.log      - Statistics logs

To monitor logs in real-time:
  tail -f logs/all.log
  tail -f logs/errors.log
        """)

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

        print("Active Threads:")
        for thread in threading.enumerate():
            print(f"  - {thread.name}: {'ALIVE' if thread.is_alive() else 'DEAD'}")

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
            queue_wait = avg_total - avg_exec

            print(f"""
Latency Breakdown:
  Total Latency:       {avg_total:.1f}ms
  Execution Time:      {avg_exec:.1f}ms
  Queue Wait Time:     {queue_wait:.1f}ms
  Queue Wait %:        {(queue_wait/avg_total)*100:.1f}%
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
        queue_wait = avg_total - avg_exec
        success_rate = stats['success_rate']
        queue_size = stats['queue_size']

        # High queue wait time
        if queue_wait > avg_exec:
            print(f"HIGH QUEUE WAIT TIME ({queue_wait:.1f}ms)")
            print("   - Increase worker pool size")
            print("   - Check if workers are blocked on I/O")
            print("   - Consider reducing target TPS")

        # High execution time
        if avg_exec > 100:
            print(f"HIGH EXECUTION TIME ({avg_exec:.1f}ms)")
            print("   - Database queries are slow")
            print("   - Check network latency to database")
            print("   - Consider adding database indexes")
            print("   - Enable more caching")

        # Low success rate
        if success_rate < 95:
            print(f"LOW SUCCESS RATE ({success_rate:.1f}%)")
            print("   - Workers are timing out or failing")
            print("   - Check database connectivity")
            print("   - Review error logs")

        # Growing queue
        if queue_size > 100:
            print(f"LARGE QUEUE SIZE ({queue_size})")
            print("   - Workers can't keep up with scheduling")
            print("   - Increase worker pool size")
            print("   - Reduce target TPS")

        # CPU bottleneck
        cpu_usage = psutil.cpu_percent()
        if cpu_usage > 80:
            print(f"HIGH CPU USAGE ({cpu_usage:.1f}%)")
            print("   - CPU is bottleneck")
            print("   - Reduce worker count")
            print("   - Optimize query complexity")

        # Memory bottleneck
        memory_usage = psutil.virtual_memory().percent
        if memory_usage > 85:
            print(f"HIGH MEMORY USAGE ({memory_usage:.1f}%)")
            print("   - Memory is bottleneck")
            print("   - Reduce cache sizes")
            print("   - Check for memory leaks")

        # Good performance
        if queue_wait < 20 and avg_exec < 50 and success_rate > 95 and queue_size < 10:
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
                success = self.graph_service.drop_all_transactions()
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
        import glob

        log_dir = "logs"
        if not os.path.exists(log_dir):
            print("No logs directory found.")
            return

        log_files = glob.glob(os.path.join(log_dir, "*.log"))

        if not log_files:
            print("No log files found to clear.")
            return

        print(f"Warning: This will clear the contents of {len(log_files)} log files:")
        for log_file in log_files:
            file_size = os.path.getsize(log_file) if os.path.exists(log_file) else 0
            size_str = f"({file_size:,} bytes)" if file_size > 0 else "(empty)"
            print(f"  - {os.path.basename(log_file)} {size_str}")

        confirm = input("\nAre you sure you want to clear all log files? (yes/no): ").strip().lower()

        if confirm in ['yes', 'y']:
            print("Clearing log files...")
            cleared_count = 0
            failed_count = 0

            for log_file in log_files:
                try:
                    with open(log_file, 'w') as f:
                        pass
                    cleared_count += 1
                    print(f"  Cleared: {os.path.basename(log_file)}")
                except Exception as e:
                    failed_count += 1
                    print(f"  Failed to clear {os.path.basename(log_file)}: {e}")

            print(f"\nLog clearing complete: {cleared_count} cleared, {failed_count} failed")
            if cleared_count > 0:
                logger.info(f"Cleared {cleared_count} log files via CLI")
        else:
            print("Log clearing cancelled.")

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
