import asyncio
import random
from datetime import datetime
from typing import List, Dict, Any
from enum import Enum
import json
import uuid
from gremlin_python.process.graph_traversal import __

# Import local modules
from services.fraud_service import FraudService
from services.graph_service import GraphService
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

class TransactionGeneratorService:
    def __init__(self, graph_service: GraphService, fraud_service: FraudService):
        self.graph_service = graph_service
        self.fraud_service = fraud_service
        self.is_running = False
        self.generation_rate = 1  # transactions per second
        self.generated_transactions = []
        self.transaction_counter = 0
        self.task = None
        self.account_vertices = []
        self.start_time = None

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


    # ----------------------------------------------------------------------------------------------------------
    # Transaction generation control
    # ----------------------------------------------------------------------------------------------------------


    async def start_generation(self, rate: int = 1, start: str = ""):
        """Start transaction generation at specified rate"""
        if self.is_running:
            logger.warning("Transaction generation is already running")
            return False
        try:
            self.account_vertices = self.graph_service.client.V().has_label("account").id_().to_list()
            if len(self.account_vertices) < 1:
                raise Exception("No accounts available")
        except Exception as e:
            logger.error(f"Unable to start transaction generator: {e}")
            return False

        self.generation_rate = rate
        self.is_running = True
        self.transaction_counter = 0
        self.start_time = start
        
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
        self.start_time = None
        self.transaction_counter = 0

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
                await self._generate_transaction()
                # Wait for next generation
                await asyncio.sleep(1.0 / self.generation_rate)
                
            except Exception as e:
                logger.error(f"❌ Error in generation loop: {e}")
                await asyncio.sleep(1)


    # ----------------------------------------------------------------------------------------------------------
    # Transaction generation functions
    # ----------------------------------------------------------------------------------------------------------

       
    async def create_manual_transaction(self, from_id: str, to_id: str, amount: float, type: str = "transfer", gen_type: str = "MANUAL") -> Dict[str, Any]:
        """Create a manual transaction between specified accounts"""
        try:
            logger.info(f"Creating {gen_type.lower()} transaction from {from_id} to {to_id} amount {amount}")
            # Validate accounts exist
            if not await self._validate_account_exists(from_id):
                raise Exception(f"Source account {from_id} not found")
            if not await self._validate_account_exists(to_id):
                raise Exception(f"Destination account {to_id} not found")
            # Prevent self-transactions
            if from_id == to_id:
                raise Exception("Source and destination accounts cannot be the same")

            # Create transaction
            txn_id = str(uuid.uuid4())
            loop = asyncio.get_event_loop()
            def create_transaction():
                try:
                    return (
                        self.graph_service.client.addE("TRANSACTS")
                            .from_(__.V(from_id))
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
                except Exception as e:
                    raise Exception(f"❌ Error storing transaction in graph: {e}")

            edge_id = await loop.run_in_executor(None, create_transaction)
            self.transaction_counter += 1
            logger.info(f"✅ Transaction {txn_id} stored in graph database with both sender and receiver edges")
                       
            # Run fraud detection
            try:
                await self.fraud_service.run_fraud_detection(edge_id, txn_id)
                logger.info(f"✅ {gen_type} transaction created: {txn_id} from {from_id} to {to_id} amount {amount}")
            except Exception as e:
                raise Exception(f"Error running fraud detection: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error creating manual transaction: {e}")
            return {"success": False, "error": f"❌ Error creating manual transaction: {e}"}

    async def _generate_transaction(self) -> Dict[str, Any]:
        """Generate a normal transaction between real users and accounts"""
        try:    
            # Get 2 random accounts from the graph database
            sender_account_id, receiver_account_id = random.sample(self.account_vertices, 2)
            
            if not sender_account_id or not receiver_account_id:
                logger.error("Could not get accounts from graph database. Cannot generate transaction without valid accounts.")
                raise Exception("No valid accounts available in graph database for transaction generation")
            
            # Generate transaction data
            amount = random.uniform(100.0, 15000.0)
            transaction_type = random.choice(["transfer", "payment", "deposit", "withdrawal"])
            
            await self.create_manual_transaction(sender_account_id, receiver_account_id, amount, transaction_type, "AUTO")
            
        except Exception as e:
            logger.error(f"Error generating normal transaction: {e}")
            raise e
        
    async def _validate_account_exists(self, account_id: str) -> bool:
        """Validate that an account exists in the graph database"""
        try:
            if self.graph_service.client:
                loop = asyncio.get_event_loop()
                def check_account():
                    accounts = self.graph_service.client.V(str(account_id)).to_list()
                    return len(accounts) > 0
                
                return await loop.run_in_executor(None, check_account)
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