import asyncio
import random
import pickle
import math
import time
import threading
from datetime import datetime
from typing import List, Dict, Any
from enum import Enum
import json
import uuid
from gremlin_python.process.graph_traversal import __
from concurrent.futures import ThreadPoolExecutor

# Import local modules
from services.fraud_service import FraudService
from services.graph_service import GraphService
from services.performance_monitor import performance_monitor
from logging_config import get_logger

logger = get_logger('fraud_detection.transaction_generator')
stats_logger = get_logger('fraud_detection.stats')

class FraudScenario(Enum):
    SCENARIO_A = "Multiple Small Credits Followed by Large Debit"
    SCENARIO_B = "Large Credit Followed by Structured Equal Debits"
    SCENARIO_C = "Multiple Large ATM Withdrawals"
    SCENARIO_D = "High-Frequency Transfers Between Mule Accounts"
    SCENARIO_E = "Salary-Like Deposits Followed by Suspicious Transfers"
    SCENARIO_F = "Dormant Account Sudden Activity"
    SCENARIO_G = "International Transfers to High-Risk Jurisdictions"
    SCENARIO_H = "Region-Specific Fraud (Indian Context)"

def get_stored_max_transaction_rate():
    try:
        file = open('store.pckl', 'rb')
        obj = pickle.load(file)
        file.close()
        return obj.get("rate", 50)
    except:
        return 50

class TransactionGeneratorService:
    def __init__(self, graph_service: GraphService, fraud_service: FraudService):
        self.graph_service = graph_service
        self.fraud_service = fraud_service
        self.is_running = False
        self.max_generation_rate = get_stored_max_transaction_rate()
        self.generation_rate = 1  # transactions per second
        self.generated_transactions = []
        self.transaction_counter = 0
        self.task = None
        self.account_vertices = []
        self.start_time = None

        self.transaction_worker = TransactionWorker(self, self.fraud_service)
        self.scheduler = TransactionScheduler(self.transaction_worker)

        # High-risk jurisdictions for international transfers
        self.high_risk_jurisdictions = ['Dubai', 'Bahrain', 'Thailand', 'Cayman Islands', 'Panama']
        
        # Indian fraud locations
        self.indian_fraud_locations = ['Jamtara', 'Bharatpur', 'Alwar', 'Mewat', 'Nuh']
        
        # Normal locations (Indian cities)
        # self.normal_locations = [
        #     'Mumbai, Maharashtra', 'Delhi, Delhi', 'Bangalore, Karnataka', 'Hyderabad, Telangana', 
        #     'Chennai, Tamil Nadu', 'Kolkata, West Bengal', 'Pune, Maharashtra', 'Ahmedabad, Gujarat',
        #     'Jaipur, Rajasthan', 'Surat, Gujarat', 'Lucknow, Uttar Pradesh', 'Kanpur, Uttar Pradesh',
        #     'Nagpur, Maharashtra', 'Visakhapatnam, Andhra Pradesh', 'Indore, Madhya Pradesh',
        #     'Thane, Maharashtra', 'Bhopal, Madhya Pradesh', 'Patna, Bihar', 'Vadodara, Gujarat',
        #     'Ghaziabad, Uttar Pradesh', 'Ludhiana, Punjab', 'Agra, Uttar Pradesh', 'Nashik, Maharashtra'
        # ]
        
        self.normal_locations = [
            'New York, New York', 'Los Angeles, California', 'Chicago, Illinois', 'Houston, Texas',
            'Phoenix, Arizona', 'Philadelphia, Pennsylvania', 'San Antonio, Texas', 'San Diego, California',
            'Dallas, Texas', 'San Jose, California', 'Austin, Texas', 'Jacksonville, Florida',
            'Fort Worth, Texas', 'Columbus, Ohio', 'Charlotte, North Carolina', 'San Francisco, California',
            'Indianapolis, Indiana', 'Seattle, Washington', 'Denver, Colorado', 'Washington, District of Columbia',
            'Boston, Massachusetts', 'El Paso, Texas', 'Nashville, Tennessee', 'Detroit, Michigan',
            'Oklahoma City, Oklahoma', 'Portland, Oregon', 'Las Vegas, Nevada', 'Memphis, Tennessee',
            'Louisville, Kentucky', 'Baltimore, Maryland', 'Milwaukee, Wisconsin', 'Albuquerque, New Mexico',
            'Tucson, Arizona', 'Fresno, California', 'Sacramento, California', 'Mesa, Arizona',
            'Kansas City, Missouri', 'Atlanta, Georgia', 'Long Beach, California', 'Colorado Springs, Colorado',
            'Raleigh, North Carolina', 'Miami, Florida', 'Virginia Beach, Virginia', 'Omaha, Nebraska',
            'Oakland, California', 'Minneapolis, Minnesota', 'Tulsa, Oklahoma', 'Arlington, Texas'
        ]
        
        # Transaction types
        self.transaction_types = ['purchase', 'transfer', 'withdrawal', 'deposit', 'payment']

    def initialize_workers(self):
        """Initialize workers and wait for them to be ready"""
        logger.info("Initializing transaction workers...")
        
        if self.transaction_worker is None:
            self.transaction_worker = TransactionWorker(self, self.fraud_service)
        if not self.transaction_worker.running:
            self.transaction_worker.start_workers()
            
        if self.scheduler is None:
            self.scheduler = TransactionScheduler(self.transaction_worker)
            
        logger.info("Workers initialized and ready")


    # ----------------------------------------------------------------------------------------------------------
    # Transaction generation control
    # ----------------------------------------------------------------------------------------------------------

    
    def get_max_transaction_rate(self):
        """Get the max rate for transactions genreated per second"""
        return self.max_generation_rate

    def set_max_transaction_rate(self, new_rate):
        """Set the max rate for transactions generated per second"""
        try:
            old_rate = self.max_generation_rate
            
            file = open('store.pckl', 'wb')
            pickle.dump({ "rate": new_rate }, file)
            file.close()

            self.max_generation_rate = new_rate
            
            logger.info(f"Max generation rate updated from {old_rate} to {new_rate} transactions/second")
            return True
        
        except Exception as e:
            logger.error(f"Unable to set new max generation rate: {e}")
            return False

    def start_generation(self, rate: float = 1, start: str = ""):
        """Start transaction generation at specified rate"""
        if self.is_running:
            logger.warning("Transaction generation is already running")
            return False
            
        self.initialize_workers()
        
        try:
            self.account_vertices = self.graph_service.client.V().has_label("account").id_().to_list()
            if len(self.account_vertices) < 1:
                raise Exception("No accounts available")
        except Exception as e:
            logger.error(f"Unable to start transaction generator: {e}")
            return False

        performance_monitor.reset_transaction_metrics()
        self.generated_transactions.clear()
        self.generation_rate = rate
        self.is_running = True
        self.transaction_counter = 0
        self.start_time = start
        
        success = self.scheduler.start_generation(rate)
        if not success:
            self.is_running = False
            return False
        
        logger.info(f"Starting transaction generation at {self.generation_rate} transactions/second")
        stats_logger.info(f"START: Generation started at {self.generation_rate} txn/sec")

        return True

    def stop_generation(self):
        """Stop transaction generation"""
        if not self.is_running:
            logger.warning("Transaction generation is not running")
            return False
            
        self.is_running = False
        
        if self.scheduler:
            self.scheduler.stop_generation()
        if self.scheduler:
            self.transaction_worker.stop_workers()

        logger.info("Transaction generation stopped")
        logger.info(f"Generated {self.transaction_counter} transactions")
        
        stats_logger.info(f"STOP: Generation stopped. Total: {self.transaction_counter} transactions")
        self._log_statistics()
        
        return True

    async def _generation_loop(self):
        """Main generation loop"""
        while self.is_running:
            try:    
                asyncio.create_task(self._generate_transaction())
                await asyncio.sleep(.0005)
        
            except Exception as e:
                logger.error(f"Error in generation loop: {e}")
                await asyncio.sleep(1)



    # ----------------------------------------------------------------------------------------------------------
    # Transaction generation functions
    # ----------------------------------------------------------------------------------------------------------

       
    def create_manual_transaction(self, from_id: str, to_id: str, amount: float, type: str = "transfer", gen_type: str = "MANUAL", force: bool = False) -> Dict[str, Any]:
        """Create a manual transaction between specified accounts"""
        try:
            logger.info(f"Creating {gen_type.lower()} transaction from {from_id} to {to_id} amount {amount}")

            if not force:
                try:
                    account_check = (self.graph_service.client.V(from_id, to_id)
                        .project("from_exists", "to_exists")
                        .by(__.V(from_id).count())
                        .by(__.V(to_id).count())
                        .next())

                    if account_check.get("from_exists", 0) == 0:
                        raise Exception(f"Source account {from_id} not found")
                    if account_check.get("to_exists", 0) == 0:
                        raise Exception(f"Destination account {to_id} not found")
                except Exception as e:
                    if "not found" in str(e):
                        raise e
                    # Fall back to individual validation if the optimized query fails
                    if not self._validate_account_exists(from_id):
                        raise Exception(f"Source account {from_id} not found")
                    if not self._validate_account_exists(to_id):
                        raise Exception(f"Destination account {to_id} not found")
            # Prevent self-transactions
            if from_id == to_id:
                raise Exception("Source and destination accounts cannot be the same")

            # Create transaction
            txn_id = str(uuid.uuid4())
            edge_id = (self.graph_service.client.V(from_id)
                .addE("TRANSACTS")
                .to(__.V(to_id))
                .property("txn_id", txn_id)
                .property("amount", round(amount, 2))
                .property("currency", "USD")
                .property("type", type)
                .property("method", "electronic_transfer")
                .property("location", random.choice(self.normal_locations))
                .property("timestamp", datetime.now().isoformat())
                .property("status", "completed")
                .property("gen_type", gen_type)
                .id_()
                .next())
            
            self.transaction_counter += 1
            logger.info(f"{gen_type} transaction created: {txn_id} from {from_id} to {to_id} amount {amount}")
            
            return {
                "success": True,
                "edge_id": edge_id,
                "txn_id": txn_id,
                "from_id": from_id,
                "to_id": to_id,
                "amount": amount
            }
        
        except Exception as e:
            logger.error(f"Error creating manual transaction: {e}")
            return {"success": False, "error": f"Error creating manual transaction: {e}"}

    def generate_transaction(self) -> Dict[str, Any]:
        """Generate a normal transaction between real users and accounts"""
        try:
            if len(self.account_vertices) < 1:
                self.account_vertices = self.graph_service.client.V().has_label("account").id_().to_list()
            if len(self.account_vertices) < 1:
                raise Exception("No accounts available")
            
            # Get 2 random accounts from the graph database
            sender_account_id, receiver_account_id = random.sample(self.account_vertices, 2)
            
            if not sender_account_id or not receiver_account_id:
                logger.error("Could not get accounts from graph database. Cannot generate transaction without valid accounts.")
                raise Exception("No valid accounts available in graph database for transaction generation")
            
            # Generate transaction data
            amount = random.uniform(100.0, 15000.0)
            transaction_type = random.choice(["transfer", "payment", "deposit", "withdrawal"])
            
            return self.create_manual_transaction(sender_account_id, receiver_account_id, amount, transaction_type, "AUTO", force=True)
        
        except Exception as e:
            logger.error(f"Error generating normal transaction: {e}")
            raise e
        
    def _validate_account_exists(self, account_id: str) -> bool:
        """Validate that an account exists in the graph database"""
        try:
            if self.graph_service.client:
                accounts = self.graph_service.client.V(str(account_id)).to_list()
                return len(accounts) > 0
            return False
        
        except Exception as e:
            logger.error(f"Error validating account {account_id}: {e}")
            return False


    # ----------------------------------------------------------------------------------------------------------
    # Transaction generation statistics
    # ----------------------------------------------------------------------------------------------------------


    def get_recent_transactions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent transactions generated by this service"""
        return self.generated_transactions[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get current status of transaction generation"""
        return {
            "status": "running" if self.is_running else "stopped",
            "generation_rate": self.generation_rate,
            "total_generated": len(self.generated_transactions),
            "transaction_count": self.transaction_counter,
            "last_10_transactions": self.get_recent_transactions(10),
            "start_time": self.start_time
        }

    def get_generation_stats(self) -> Dict[str, Any]:
        """Get detailed generation statistics"""
        return {
            "is_running": self.is_running,
            "generation_rate": self.generation_rate,
            "total_generated": len(self.generated_transactions),
            "transaction_count": self.transaction_counter,
            "start_time": self.start_time
        }


    # ----------------------------------------------------------------------------------------------------------
    # Logging functions
    # ----------------------------------------------------------------------------------------------------------


    def _log_transaction(self, transaction: Dict[str, Any], transaction_type: str = "TRANSACTION"):
        """Log transaction details to appropriate log files"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create detailed log message
        log_data = {
            "timestamp": timestamp,
            "transaction_id": transaction['id'],
            "user_id": transaction.get('user_id', ''),
            "account_id": transaction['sndr_id'],
            "receiver_user_id": transaction.get('recr_user_id'),
            "receiver_account_id": transaction.get('receiver_account_id'),
            "amount": transaction['amount'],
            "currency": transaction['currency'],
            "transaction_type": transaction['txn_type'],

            "location": transaction['location'],
            "status": transaction['status']
        }
        
        # Log to main transaction log
        logger.info(f"{transaction_type}: {json.dumps(log_data, indent=2)}")
        
        # Log basic transaction info
        transaction_log_msg = f"ID: {transaction['id']} | Amount: ${transaction['amount']} | Type: {transaction['transaction_type']} | Location: {transaction['location']}"
        logger.info(f"TRANSACTION: {transaction_log_msg}")

    def _log_statistics(self):
        """Log current statistics"""
        stats_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_transactions": self.transaction_counter,
            "generation_rate": self.generation_rate,
            "is_running": self.is_running
        }
        
        stats_logger.info(f"STATISTICS: {json.dumps(stats_data, indent=2)}")

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        # Update performance monitor with current queue size
        if self.transaction_worker:
            pool_status = self.transaction_worker.get_pool_status()
            performance_monitor.set_generation_state(
                performance_monitor.is_running, 
                performance_monitor.target_tps, 
                pool_status.get('queue_size', 0)
            )
        
        return performance_monitor.get_transaction_stats()
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get thread pool status"""
        if self.transaction_worker:
            return self.transaction_worker.get_pool_status()
        return {"pool_size": 0, "running": False, "active_threads": 0, "queue_size": 0}
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        if self.scheduler:
            return self.scheduler.get_status()
        return {"running": False, "target_tps": 0, "scheduler_workers": 0, "worker_names": []}
    
    def get_bottleneck_analysis(self) -> Dict[str, Any]:
        """Get bottleneck analysis data"""
        stats = self.get_performance_stats()
        pool_status = self.get_pool_status()
        scheduler_status = self.get_scheduler_status()
        
        return {
            "performance_stats": stats,
            "pool_status": pool_status,
            "scheduler_status": scheduler_status,
            "system_info": {
                "cpu_percent": __import__('psutil').cpu_percent(),
                "memory_percent": __import__('psutil').virtual_memory().percent,
                "active_threads": len(__import__('threading').enumerate())
            }
        }

    def shutdown(self):
        try:
            if self.is_running:
                self.stop_generation()
            
            if self.transaction_worker:
                self.transaction_worker.stop_workers()
                
            logger.info("TransactionGeneratorService shutdown complete")
        except Exception as e:
            logger.warning(f"Error during shutdown: {e}")


class TransactionWorker:
    def __init__(self, transaction_generator: 'TransactionGeneratorService', fraud_service):
        self.transaction_generator = transaction_generator
        self.fraud_service = fraud_service
        self.running = False
        self.executor = None
        self._max_workers = 128


    def start_workers(self):
        self.running = True
        self.executor = ThreadPoolExecutor(max_workers=self._max_workers, thread_name_prefix="txn_fraud_worker")
        logger.info(f"Transaction workers ready ({self.executor._max_workers} workers)")

    def stop_workers(self):
        self.running = False
        try:
            self.executor.shutdown(wait=False, cancel_futures=True)
            logger.info("Transaction workers stopped")
        except Exception as e:
            logger.warning(f"Error shutting down worker executor: {e}")
            self.executor.shutdown(wait=False)

    def submit_transaction(self, task_data: Dict[str, Any]):
        if not self.running:
            raise RuntimeError("Workers not started")
            
        future = self.executor.submit(self._execute_transaction, task_data)
        return future

    def _execute_transaction(self, task_data: Dict[str, Any]):
        scheduled_time = task_data['scheduled_time']
        start_time = time.time()
        
        queue_wait_ms = (start_time - scheduled_time) * 1000
        
        try:
            # Time the transaction generation (DB write)
            db_start_time = time.time()
            result = self.transaction_generator.generate_transaction()
            db_end_time = time.time()
            db_latency_ms = (db_end_time - db_start_time) * 1000
            
            if result and result.get('success') and 'edge_id' in result and 'txn_id' in result:
                fraud_start_time = time.time()
                self.fraud_service.submit_fraud_detection_async(
                    result['edge_id'],
                    result['txn_id']
                )
                fraud_end_time = time.time()
                fraud_latency_ms = (fraud_end_time - fraud_start_time) * 1000

                end_time = time.time()
                total_latency_ms = (end_time - scheduled_time) * 1000
                execution_latency_ms = (end_time - start_time) * 1000

                performance_monitor.record_transaction_completed_detailed(
                    total_latency_ms, 
                    execution_latency_ms,
                    queue_wait_ms,
                    db_latency_ms,
                    fraud_latency_ms
                )
                
                if total_latency_ms > 1000:
                    logger.info(f"HIGH LATENCY Transaction {result['txn_id']}: "
                              f"Total={total_latency_ms:.1f}ms "
                              f"(Queue={queue_wait_ms:.1f}ms, "
                              f"DB={db_latency_ms:.1f}ms, "
                              f"Fraud={fraud_latency_ms:.1f}ms)")
                elif queue_wait_ms > 500:
                    logger.info(f"HIGH QUEUE WAIT Transaction {result['txn_id']}: "
                              f"Queue={queue_wait_ms:.1f}ms, Total={total_latency_ms:.1f}ms")
            else:
                performance_monitor.record_transaction_failed()
                logger.warning("Transaction creation failed")

        except Exception as e:
            performance_monitor.record_transaction_failed()
            logger.error(f"Transaction+Fraud execution error: {e}")

    def get_pool_status(self) -> Dict[str, Any]:
        if self.executor is None:
            return {
                    "pool_size": 0,
                    "running": self.running,
                    "active_threads": 0,
                    "queue_size": 0
                    }
        return {
            "pool_size": self.executor._max_workers,
            "running": self.running,
            "active_threads": len(getattr(self.executor, '_threads', [])),
            "queue_size": getattr(self.executor._work_queue, 'qsize', lambda: 0)()
        }


class TransactionScheduler:
    def __init__(self, transaction_worker: TransactionWorker):
        self.transaction_worker = transaction_worker
        self.scheduler_workers = []
        self.running = False
        self.target_tps = 0
        
        # Synchronization events for coordinated startup
        self.workers_ready_event = threading.Event()
        self.start_timing_event = threading.Event()

    def start_generation(self, tps: float) -> bool:
        if self.running:
            return False
            
        self.target_tps = tps
        self.running = True
        
        self.workers_ready_event.clear()
        self.start_timing_event.clear()
        
        SCHEDULER_TPS_CAPACITY = 100
        workers_needed = max(1, math.ceil(tps / SCHEDULER_TPS_CAPACITY))
        tps_per_worker = tps / workers_needed
        
        logger.info(f"Starting {workers_needed} scheduler workers for {tps} TPS ({tps_per_worker:.1f} TPS each)")
        
        for i in range(workers_needed):
            worker = threading.Thread(
                target=self._generation_loop,
                args=(tps_per_worker, i, workers_needed),
                name=f"scheduler_worker_{i}",
                daemon=True
            )
            worker.start()
            self.scheduler_workers.append(worker)
        
        # Wait for all workers to be ready
        logger.info("Waiting for all scheduler workers to be ready...")
        ready_timeout = 10.0
        if self.workers_ready_event.wait(timeout=ready_timeout):
            logger.info("All scheduler workers ready - starting synchronized timing")
            
            # Signal all workers to start timing simultaneously
            self.start_timing_event.set()
            performance_monitor.set_generation_state(True, tps)
            
            logger.info(f"Transaction generation started at {tps} TPS with synchronized timing")
            return True
        else:
            logger.error(f"Timeout waiting for scheduler workers to be ready after {ready_timeout}s")
            self.stop_generation()
            return False

    def stop_generation(self) -> bool:
        if not self.running:
            return False
        self.target_tps = 0
        self.workers_ready_event.clear()
        self.start_timing_event.clear()
        self.running = False
        performance_monitor.set_generation_state(False)
        
        # Signal workers to stop and wait for them
        self.start_timing_event.set()  # Unblock any waiting workers
        
        for worker in self.scheduler_workers:
            worker.join(timeout=2.0)
        
        self.scheduler_workers.clear()
        
        # Reset synchronization state for next start
        if hasattr(self, '_ready_workers_count'):
            with self._ready_workers_lock:
                self._ready_workers_count = 0
        
        logger.info("Transaction generation stopped")
        return True

    def _generation_loop(self, worker_tps: float, worker_id: int, total_workers: int):
        """Generation loop with synchronized startup"""
        interval = 1.0 / worker_tps
        
        # Signal that this worker is ready
        logger.debug(f"Scheduler worker {worker_id} ready")
        
        # Use a thread-safe counter to track ready workers
        if not hasattr(self, '_ready_workers_lock'):
            self._ready_workers_lock = threading.Lock()

        with self._ready_workers_lock:
            if not hasattr(self, '_ready_workers_count'):
                self._ready_workers_count = 0
            self._ready_workers_count += 1
            if self._ready_workers_count == total_workers:
                logger.info(f"All {total_workers} scheduler workers ready")
                self.workers_ready_event.set()
        
        # Wait for the start signal before beginning timing
        logger.debug(f"Scheduler worker {worker_id} waiting for start signal...")
        if not self.start_timing_event.wait(timeout=15.0):
            logger.error(f"Scheduler worker {worker_id} timeout waiting for start signal")
            return
        
        # Now all workers start timing simultaneously
        logger.debug(f"Scheduler worker {worker_id} starting synchronized generation")
        next_time = time.time()
        
        # Per-second rate limiting
        current_second = int(time.time())
        transactions_this_second = 0
        max_transactions_per_second = int(worker_tps) * 1.5  # Allow slight buffer for rounding
        
        while self.running:
            current_time = time.time()
            current_time_second = int(current_time)
            
            if current_time_second != current_second:
                current_second = current_time_second
                transactions_this_second = 0
            
            if transactions_this_second >= max_transactions_per_second:
                sleep_until_next_second = (current_second + 1) - current_time
                if sleep_until_next_second > 0:
                    time.sleep(min(0.1, sleep_until_next_second))
                continue
            
            if current_time >= next_time:
                task_data = {
                    'scheduled_time': current_time,
                    'amount': random.uniform(100.0, 15000.0),
                    'type': random.choice(["transfer", "payment", "deposit", "withdrawal"])
                }
                
                try:
                    self.transaction_worker.submit_transaction(task_data)
                    performance_monitor.record_transaction_scheduled()
                    transactions_this_second += 1
                    
                    if transactions_this_second >= max_transactions_per_second * 0.9:
                        logger.debug(f"Scheduler worker approaching rate limit: {transactions_this_second}/{max_transactions_per_second} TPS")
                        
                except Exception as e:
                    logger.debug(f"Transaction submission failed (thread pool full): {e}")
                    performance_monitor.record_transaction_failed()
                
                next_time += interval
            else:
                sleep_time = min(0.001, next_time - current_time)
                time.sleep(sleep_time)

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "target_tps": self.target_tps,
            "scheduler_workers": len(self.scheduler_workers),
            "worker_names": [w.name for w in self.scheduler_workers]
        }