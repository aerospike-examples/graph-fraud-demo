import asyncio
import random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
import json
import uuid
import os
from gremlin_python.process.traversal import T


# Import local modules
from models.schemas import Transaction
from services.graph_service import GraphService
from services.rt1_fraud_service import RT1FraudService
from services.rt2_fraud_service import RT2FraudService
# from services.rt3_fraud_service import RT3FraudService

# Configure logging
def setup_logging():
    """Setup comprehensive logging for transaction generator"""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Main logger
    logger = logging.getLogger('fraud_detection.transaction_generator')
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler for all transactions
    file_handler = logging.FileHandler('logs/transactions.log')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Separate file handler for fraud transactions
    fraud_handler = logging.FileHandler('logs/fraud_transactions.log')
    fraud_handler.setLevel(logging.INFO)
    fraud_formatter = logging.Formatter(
        '%(asctime)s - FRAUD - %(message)s'
    )
    fraud_handler.setFormatter(fraud_formatter)
    logger.addHandler(fraud_handler)
    
    # Separate file handler for normal transactions
    normal_handler = logging.FileHandler('logs/normal_transactions.log')
    normal_handler.setLevel(logging.INFO)
    normal_formatter = logging.Formatter(
        '%(asctime)s - NORMAL - %(message)s'
    )
    normal_handler.setFormatter(normal_formatter)
    logger.addHandler(normal_handler)
    
    # Prevent propagation to parent logger
    logger.propagate = False
    
    # Statistics logger
    stats_logger = logging.getLogger('fraud_detection.stats')
    stats_logger.setLevel(logging.INFO)
    stats_logger.handlers.clear()
    
    stats_handler = logging.FileHandler('logs/statistics.log')
    stats_handler.setLevel(logging.INFO)
    stats_formatter = logging.Formatter(
        '%(asctime)s - STATS - %(message)s'
    )
    stats_handler.setFormatter(stats_formatter)
    stats_logger.addHandler(stats_handler)
    stats_logger.propagate = False  # Prevent propagation to parent logger
    
    return logger, stats_logger

# Setup logging
logger, stats_logger = setup_logging()

class FraudScenario(Enum):
    SCENARIO_A = "Multiple Small Credits Followed by Large Debit"
    SCENARIO_B = "Large Credit Followed by Structured Equal Debits"
    SCENARIO_C = "Multiple Large ATM Withdrawals"
    SCENARIO_D = "High-Frequency Transfers Between Mule Accounts"
    SCENARIO_E = "Salary-Like Deposits Followed by Suspicious Transfers"
    SCENARIO_F = "Dormant Account Sudden Activity"
    SCENARIO_G = "International Transfers to High-Risk Jurisdictions"
    SCENARIO_H = "Region-Specific Fraud (Indian Context)"

class TransactionGeneratorService:
    def __init__(self, graph_service: GraphService):
        self.graph_service = graph_service
        
        # Initialize fraud detection services
        self.rt1_service = RT1FraudService(graph_service)
        self.rt2_service = RT2FraudService(graph_service)
        # self.rt3_service = RT3FraudService(graph_service)
        self.is_running = False
        self.generation_rate = 1  # transactions per second
        self.generated_transactions = []
        self.transaction_counter = 0
        self.task = None
        
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

    def _log_transaction(self, transaction: Dict[str, Any], transaction_type: str = "TRANSACTION"):
        """Log transaction details to appropriate log files"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create detailed log message
        log_data = {
            "timestamp": timestamp,
            "transaction_id": transaction['id'],
            "user_id": transaction.get('user_id', ''),
            "account_id": transaction['account_id'],
            "receiver_user_id": transaction.get('receiver_user_id'),
            "receiver_account_id": transaction.get('receiver_account_id'),
            "amount": transaction['amount'],
            "currency": transaction['currency'],
            "transaction_type": transaction['transaction_type'],

            "location": transaction['location'],
            "status": transaction['status']
        }
        
        # Log to main transaction log
        logger.info(f"{transaction_type}: {json.dumps(log_data, indent=2)}")
        
        # Log basic transaction info
        transaction_log_msg = f"ID: {transaction['id']} | Amount: ₹{transaction['amount']} | Type: {transaction['transaction_type']} | Location: {transaction['location']}"
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

    async def start_generation(self, rate: int = 1):
        """Start transaction generation at specified rate"""
        if self.is_running:
            logger.warning("Transaction generation is already running")
            return False
            
        self.generation_rate = rate
        self.is_running = True
        self.transaction_counter = 0
        
        logger.info(f"🚀 Starting transaction generation at {self.generation_rate} transactions/second")
        stats_logger.info(f"START: Generation started at {self.generation_rate} txn/sec")
        
        # Start the generation task
        self.task = asyncio.create_task(self._generation_loop())
        return True

    async def stop_generation(self):
        """Stop transaction generation"""
        if not self.is_running:
            logger.warning("Transaction generation is not running")
            return False
            
        self.is_running = False
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
        
        logger.info("🛑 Transaction generation stopped")
        logger.info(f"📊 Generated {self.transaction_counter} transactions")
        
        stats_logger.info(f"STOP: Generation stopped. Total: {self.transaction_counter} transactions")
        self._log_statistics()
        
        return True

    async def _generation_loop(self):
        """Main generation loop"""
        while self.is_running:
            try:
                # Generate transaction (already stores in memory, graph, and runs fraud detection)
                transaction = await self._generate_transaction()
                
                # Transaction processing is already handled by create_manual_transaction:
                # - Memory storage: self.generated_transactions.append(transaction)
                # - Graph storage: await self._store_transaction_in_graph(transaction) 
                # - Fraud detection: await self._run_fraud_detection(transaction)
                
                # Keep only last 1000 transactions
                if len(self.generated_transactions) > 1000:
                    self.generated_transactions = self.generated_transactions[-1000:]
                
                # Log transaction
                #self._log_transaction(transaction)
                
                # Log statistics every 10 transactions
                if self.transaction_counter % 10 == 0:
                    self._log_statistics()
                
                # Wait for next generation
                await asyncio.sleep(1.0 / self.generation_rate)
                
            except Exception as e:
                logger.error(f"❌ Error in generation loop: {e}")
                await asyncio.sleep(1)

    async def _generate_transaction(self) -> Dict[str, Any]:
        """Generate a single transaction (always normal - fraud detection happens post-transaction)"""
        return await self._generate_normal_transaction()



    async def _generate_normal_transaction(self) -> Dict[str, Any]:
        """Generate a normal transaction between real users and accounts"""
        try:    
            # Get 2 random accounts from the graph database
            sender_account_id, receiver_account_id = await self._get_random_accounts()
            
            if not sender_account_id or not receiver_account_id:
                logger.error("Could not get accounts from graph database. Cannot generate transaction without valid accounts.")
                raise Exception("No valid accounts available in graph database for transaction generation")
            
            # Generate transaction data
            amount = random.uniform(100.0, 1000000.0)
            transaction_type = random.choice(["transfer", "payment", "deposit", "withdrawal"])
            
            transaction = await self.create_manual_transaction(sender_account_id, receiver_account_id, amount, transaction_type, "AUTO")
            # Log and update counters
            #self._log_transaction(transaction, "TRANSACTION")
            self.transaction_counter += 1
            
            return transaction
            
        except Exception as e:
            logger.error(f"Error generating normal transaction: {e}")
            raise e





    async def _get_random_accounts(self) -> Optional[tuple]:
        """Get 2 random account vertices from the graph database using Gremlin query"""
        try:
            logger.debug("Getting 2 random account vertices from graph")
            
            # Use Gremlin query to get 2 random account vertices
            loop = asyncio.get_event_loop()
            
            def get_random_accounts():
                return self.graph_service.client.V().has_label("account").limit(2).to_list()
            
            account_vertices = await loop.run_in_executor(None, get_random_accounts)
            
            sender_account_id = str(account_vertices[0].id)
            receiver_account_id = str(account_vertices[1].id)
            logger.debug(f"Found random accounts: {sender_account_id} and {receiver_account_id}")
            return sender_account_id, receiver_account_id
                
        except Exception as e:
            logger.error(f"Error getting random accounts: {e}")
            return None, None

    



    async def _run_fraud_detection(self, transaction: Dict[str, Any]):
        """Run fraud detection on the transaction"""
        try:
            # Run RT1 fraud detection (flagged accounts)
            rt1_result = await self.rt1_service.check_transaction(transaction)
            if rt1_result.get("is_fraud"):
                logger.warning(f"🚨 RT1 FRAUD ALERT: {rt1_result.get('reason', 'Unknown reason')}")
            
            # Run RT2 fraud detection (flagged devices)
            rt2_result = await self.rt2_service.check_transaction_fraud(transaction)
            if rt2_result.get("is_fraud"):
                logger.warning(f"🚨 RT2 FRAUD ALERT: {rt2_result.get('reason', 'Unknown reason')}")
            
            # Skip RT3 fraud detection (account velocity) for now
            # rt3_result = await self.rt3_service.check_transaction_fraud(transaction)
            # if rt3_result.get("is_fraud"):
            #     logger.warning(f"🚨 RT3 FRAUD ALERT: {rt3_result.get('reason', 'Unknown reason')}")
                
        except Exception as e:
            logger.error(f"❌ Error in fraud detection for transaction {transaction.get('id', 'unknown')}: {e}")

    async def _store_transaction_in_graph(self, transaction: Dict[str, Any]):
        """Store transaction in the graph database"""
        try:
            if self.graph_service.client:
                loop = asyncio.get_event_loop()
                
                # We already have the account IDs, no need to fetch the vertices again
                sender_account_id = transaction['account_id']
                receiver_account_id = transaction['receiver_account_id']
                
                if sender_account_id and receiver_account_id and receiver_account_id != 'unknown':
                    # Create transaction vertex and both edges in one Gremlin query
                    def create_transaction_and_edges():
                        return self.graph_service.client.add_v("transaction") \
                            .property(T.id, transaction['id'])\
                            .property("amount", transaction['amount'])\
                            .property("currency", transaction['currency'])\
                            .property("timestamp", transaction['timestamp'])\
                            .property("location", transaction['location'])\
                            .property("type", transaction['transaction_type'])\
                            .property("status", transaction['status'])\
                            .as_("tx")\
                            .V(sender_account_id)\
                            .add_e("TRANSFERS_TO").to("tx")\
                            .V(receiver_account_id)\
                            .add_e("TRANSFERS_FROM").from_("tx")\
                            .select("tx")\
                            .next()
                    
                    transaction_vertex = await loop.run_in_executor(None, create_transaction_and_edges)
                    
                    logger.info(f"✅ Transaction {transaction['id']} stored in graph database with both sender and receiver edges")
                else:
                    if not sender_account_id:
                        logger.warning(f"⚠️ Sender account ID not found in transaction: {sender_account_id}")
                    if not receiver_account_id or receiver_account_id == 'unknown':
                        logger.warning(f"⚠️ Receiver account ID not found in transaction: {receiver_account_id}")
                
        except Exception as e:
            logger.error(f"❌ Error storing transaction in graph: {e}")
            # Don't fail the transaction generation, just log the error

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
            "last_10_transactions": self.get_recent_transactions(10)
        }

    def get_generation_stats(self) -> Dict[str, Any]:
        """Get detailed generation statistics"""
        return {
            "is_running": self.is_running,
            "generation_rate": self.generation_rate,
            "total_generated": len(self.generated_transactions),
            "transaction_count": self.transaction_counter
        }

    async def create_manual_transaction(self, from_account_id: str, to_account_id: str, amount: float, transaction_type: str = "transfer", generation_type: str = "MANUAL") -> Dict[str, Any]:
        """Create a manual transaction between specified accounts"""
        try:
            logger.info(f"Creating {generation_type.lower()} transaction from {from_account_id} to {to_account_id} amount {amount}")
            # Validate accounts exist
            if not await self._validate_account_exists(from_account_id):
                return {"success": False, "error": f"Source account {from_account_id} not found"}
                
            if not await self._validate_account_exists(to_account_id):
                return {"success": False, "error": f"Destination account {to_account_id} not found"}
            
            # Prevent self-transactions
            if from_account_id == to_account_id:
                return {"success": False, "error": "Source and destination accounts cannot be the same"}
            
            
            # Create transaction data
            transaction_id = str(uuid.uuid4())
            transaction = {
                "id": transaction_id,
                "account_id": from_account_id,
                "receiver_account_id": to_account_id,
                "amount": round(amount, 2),
                "currency": "INR",
                "transaction_type": transaction_type,
                "location": random.choice(self.normal_locations),
                "timestamp": datetime.now().isoformat(),
                "status": "completed",
                "generation_type": generation_type
            }
            
            # Store in memory
            self.generated_transactions.append(transaction)
            
            # Store in graph database
            await self._store_transaction_in_graph(transaction)
            
            # Run fraud detection
            await self._run_fraud_detection(transaction)
            
            # Log transaction
            self._log_transaction(transaction, generation_type.upper())
            self.transaction_counter += 1
            
            logger.info(f"✅ {generation_type} transaction created: {transaction_id} from {from_account_id} to {to_account_id} amount {amount}")
            
            return transaction
            
        except Exception as e:
            logger.error(f"❌ Error creating manual transaction: {e}")
            return None

    async def _validate_account_exists(self, account_id: str) -> bool:
        """Validate that an account exists in the graph database"""
        try:
            if self.graph_service.client:
                loop = asyncio.get_event_loop()
                
                def check_account():
                    accounts = self.graph_service.client.V(str(account_id)).to_list()
                    # logger.info(f"Account {account_id} exists: {accounts}")
                    return len(accounts) > 0
                
                return await loop.run_in_executor(None, check_account)
            return False
        except Exception as e:
            logger.error(f"Error validating account {account_id}: {e}")
            return False

    async def _get_user_id_from_account(self, account_id: str) -> str:
        """Get user_id from account by following OWNS relationship"""
        try:
            if self.graph_service.client:
                loop = asyncio.get_event_loop()
                
                def get_user_id():
                    try:
                        # Account ID is a vertex ID - access directly
                        users = self.graph_service.client.V(account_id).in_("OWNS").to_list()
                        logger.info(f"User query result for account {account_id}: {users}")
                        if users and len(users) > 0:
                            return str(users[0])
                        logger.warning(f"No user found for account {account_id}")
                        return ""
                    except Exception as e:
                        logger.error(f"Error getting user_id for account {account_id}: {e}")
                        return ""
                
                return await loop.run_in_executor(None, get_user_id)
            return ""
        except Exception as e:
            logger.error(f"Error in _get_user_id_from_account for {account_id}: {e}")
            return ""

# Global instance
transaction_generator = None

def get_transaction_generator(graph_service: GraphService) -> TransactionGeneratorService:
    """Get or create the global transaction generator instance"""
    global transaction_generator
    if transaction_generator is None:
        transaction_generator = TransactionGeneratorService(graph_service)
    return transaction_generator 