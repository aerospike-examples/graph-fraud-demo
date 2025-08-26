"""
RT2 Fraud Detection Service - Flagged Device Detection

This service implements real-time fraud detection based on flagged devices:
- Checks if sender or receiver has accounts connected to flagged devices
- Creates fraud check results for suspicious transactions
- Integrates with transaction generation pipeline
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from gremlin_python.process.graph_traversal import __
from services.graph_service import GraphService
from services.performance_monitor import performance_monitor

# Setup logging
logger = logging.getLogger('fraud_detection.rt2')

class RT2FraudService:
    """RT2 Fraud Detection: Flagged Device Detection"""
    
    def __init__(self, graph_service):
        self.graph_service = graph_service
        self.enabled = True
        
    async def check_transaction_fraud(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if transaction involves accounts connected to flagged devices
        Now checks connected accounts through transaction history, not just direct participants
        
        Args:
            transaction: Transaction data containing sender and receiver account IDs
            
        Returns:
            Dict containing fraud check results
        """
        overall_start_time = time.time()
        try:
            if not self.enabled or not self.graph_service.client:
                return {"is_fraud": False, "reason": "RT2 disabled or no graph client"}
            
            logger.info(f"🔍 RT2: Checking transaction {transaction['id']} for flagged device connections in transaction network")
            
            # Step 1: Validation and setup
            validation_start_time = time.time()
            sender_account_id = transaction['account_id']
            receiver_account_id = transaction['receiver_account_id']
            
            if not sender_account_id or not receiver_account_id:
                logger.warning(f"⚠️ RT2: Missing account IDs - sender: {sender_account_id}, receiver: {receiver_account_id}")
                return {"is_fraud": False, "reason": "Missing account information"}
            
            validation_time = (time.time() - validation_start_time) * 1000
            logger.info(f"⏱️ RT2: Validation completed in {validation_time:.2f}ms")
            
            # Step 2: Get all accounts connected to sender and receiver through transaction history
            connected_accounts_start_time = time.time()
            connected_accounts = await self._get_connected_accounts([sender_account_id, receiver_account_id])
            connected_accounts_time = (time.time() - connected_accounts_start_time) * 1000
            logger.info(f"🔍 RT2: Found {len(connected_accounts)} connected accounts in transaction network")
            logger.info(f"⏱️ RT2: Connected accounts retrieval completed in {connected_accounts_time:.2f}ms")
            
            # Step 3: Check all connected accounts for flagged device connections
            flagged_devices_start_time = time.time()
            flagged_devices = await self._check_accounts_for_flagged_devices(connected_accounts)
            flagged_devices_time = (time.time() - flagged_devices_start_time) * 1000
            logger.info(f"⏱️ RT2: Flagged device checking completed in {flagged_devices_time:.2f}ms")
            
            # Step 4: Process results and create fraud check if needed
            if flagged_devices:
                fraud_result_start_time = time.time()
                fraud_result = {
                    "is_fraud": True,
                    "fraud_score": 85.0,  # High score for flagged device connection
                    "status": "review",
                    "rule_name": "RT2_FlaggedDeviceConnection",
                    "reason": f"Transaction involves accounts connected to flagged devices in transaction network: {', '.join(flagged_devices)}",
                    "details": {
                        "flagged_devices": flagged_devices,
                        "sender_account": sender_account_id,
                        "receiver_account": receiver_account_id,
                        "connected_accounts_checked": len(connected_accounts),
                        "detection_time": datetime.now().isoformat(),
                        "rule_type": "RT2"
                    }
                }
                
                overall_execution_time = (time.time() - overall_start_time) * 1000  # Convert to milliseconds
                performance_monitor.record_rt2_performance(overall_execution_time, success=True)
                
                logger.warning(f"🚨 RT2 FRAUD DETECTED: Transaction {transaction.get('id')} involves flagged devices in transaction network: {flagged_devices}")
                
                # Create fraud check result in graph
                (self.graph_service.client.V(transaction['id'])
                    .property("fraud_score", fraud_result["fraud_score"])
                    .property("fraud_status", fraud_result["status"])
                    .property("rule", fraud_result["rule_name"])
                    .property("evaluation_timestamp", datetime.now().isoformat())
                    .property("reason", fraud_result["reason"])
                    .property("details", str(fraud_result["details"]))
                    .next())
                fraud_result_time = (time.time() - fraud_result_start_time) * 1000
                logger.info(f"⏱️ RT2: Fraud result creation completed in {fraud_result_time:.2f}ms")
                
                # Log performance breakdown
                logger.info(f"📊 RT2 Performance Breakdown - Total: {overall_execution_time:.2f}ms | "
                          f"Validation: {validation_time:.2f}ms | "
                          f"Connected Accounts: {connected_accounts_time:.2f}ms | "
                          f"Flagged Devices: {flagged_devices_time:.2f}ms | "
                          f"Fraud Result: {fraud_result_time:.2f}ms")
                
                return fraud_result
            else:
                overall_execution_time = (time.time() - overall_start_time) * 1000  # Convert to milliseconds
                performance_monitor.record_rt2_performance(overall_execution_time, success=True)
                
                logger.info(f"✅ RT2: Transaction {transaction.get('id')} passed flagged device check in transaction network")
                
                # Log performance breakdown for clean transactions
                logger.info(f"📊 RT2 Performance Breakdown - Total: {overall_execution_time:.2f}ms | "
                          f"Validation: {validation_time:.2f}ms | "
                          f"Connected Accounts: {connected_accounts_time:.2f}ms | "
                          f"Flagged Devices: {flagged_devices_time:.2f}ms")
                
                return {"is_fraud": False, "reason": "No flagged devices connected to transaction network"}
                
        except Exception as e:
            overall_execution_time = (time.time() - overall_start_time) * 1000  # Convert to milliseconds
            performance_monitor.record_rt2_performance(overall_execution_time, success=False)
            
            logger.error(f"❌ RT2: Error checking transaction {transaction.get('id', 'unknown')}: {e}")
            logger.error(f"📊 RT2 Error - Total execution time: {overall_execution_time:.2f}ms before failure")
            return {"is_fraud": False, "reason": f"RT2 check failed: {str(e)}"}
    
    async def _get_connected_accounts(self, primary_account_ids: List[str]) -> List[str]:
        """
        Get all accounts that have had transactions with the primary accounts
        
        Args:
            primary_account_ids: List of primary account IDs to find connections for
            
        Returns:
            List of all connected account IDs (including the primary ones)
        """
        function_start_time = time.time()
        try:
            connected_accounts = set(primary_account_ids)  # Start with primary accounts
            loop = asyncio.get_event_loop()
            
            for account_id in primary_account_ids:
                account_query_start_time = time.time()
                def find_connected_accounts():
                    try:
                        query_start_time = time.time()
                        # Find the account vertex
                        # We already have the account ID, no need to fetch the vertex again
                        account_id_to_use = account_id
                        connected_account_ids = []
                        
                        # Find all accounts connected via transactions (same logic as RT1) 
                        # account --TRANSFERS_TO--> transaction --TRANSFERS_FROM--> connected_account
                        connected_accounts = (self.graph_service.client.V(account_id_to_use)
                                           .both("TRANSFERS_TO", "TRANSFERS_FROM")  # Go to transactions
                                           .both("TRANSFERS_TO", "TRANSFERS_FROM")  # Go from transactions to connected accounts
                                           .has_label("account")                     # Filter to only accounts
                                           .dedup()                                  # Remove duplicates
                                           .to_list())

                        # Process connected accounts
                        for conn in connected_accounts:
                            # Extract ID from vertex object (same as RT1)
                            connected_account_id = str(conn.id) if hasattr(conn, 'id') else str(conn)
                            if connected_account_id and connected_account_id != account_id_to_use:
                                connected_account_ids.append(connected_account_id)
                        
                        return connected_account_ids
                        
                    except Exception as e:
                        logger.error(f"❌ RT2: Error finding connected accounts for {account_id}: {e}")
                        return []
                
                account_connections = await loop.run_in_executor(None, find_connected_accounts)
                connected_accounts.update(account_connections)
                
            result = list(connected_accounts)
            function_time = (time.time() - function_start_time) * 1000
            logger.info(f"🔍 RT2: Total connected accounts in transaction network: {len(result)}")
            logger.info(f"⏱️ RT2: _get_connected_accounts completed in {function_time:.2f}ms")
            return result
            
        except Exception as e:
            logger.error(f"❌ RT2: Error getting connected accounts: {e}")
            return primary_account_ids  # Fall back to primary accounts only
    
    async def _check_accounts_for_flagged_devices(self, account_ids: List[str]) -> List[str]:
        """
        Check if any of the given accounts are connected to flagged devices
        
        Args:
            account_ids: List of account IDs to check
            
        Returns:
            List of flagged device IDs connected to the accounts
        """
        
        try:
            loop = asyncio.get_event_loop()
            
            logger.info(f"🔍 RT2: Checking {len(account_ids)} accounts for flagged devices")
            
            def find_flagged_devices():
                try:
                    # Single optimized query: Find all flagged devices connected to accounts through OWNS relationship
                    # Path: account_ids -> OWNS -> user -> uses -> device (where fraud_flag = True)
                    flagged_devices = (self.graph_service.client.V(account_ids)
                                     .in_("OWNS")                    # Go to users who own these accounts
                                     .out("USES")                    # Go to devices used by these users
                                     .has("fraud_flag", True)        # Filter to only flagged devices # Get device IDs
                                     .dedup()                        # Remove duplicates
                                     .to_list())
                    
                    # Extract device IDs from the results
                    device_ids = []
                    for device_vertex in flagged_devices:
                        # Extract ID from vertex object (same as RT1)
                        device_id = str(device_vertex.id)
                        device_ids.append(device_id)
                    
                    logger.info(f"🔍 RT2: Found {len(device_ids)} flagged devices connected to {len(account_ids)} accounts")
                    return device_ids
                    
                except Exception as e:
                    logger.error(f"❌ RT2: Error finding flagged devices: {e}")
                    return []
            
            flagged_devices = await loop.run_in_executor(None, find_flagged_devices)
            return flagged_devices
            
        except Exception as e:
            logger.error(f"❌ RT2: Error checking accounts for flagged devices: {e}")
            return []
    
    async def create_fraud_check_result(self, transaction: Dict[str, Any], fraud_result: Dict[str, Any]):
        """Create FraudCheckResult vertex and flagged_by edge"""
        try:
            if not self.graph_service.client or not fraud_result.get("is_fraud"):
                return
                
            loop = asyncio.get_event_loop()
            
            def create_fraud_result():
                try:
                    # Find the transaction vertex
                    transaction_vertex = self.graph_service.client.V(transaction['id']).next()
                    
                    # Create FraudCheckResult vertex
                    fraud_result_vertex = (self.graph_service.client.add_v("FraudCheckResult")
                                         .property("fraud_score", fraud_result["fraud_score"])
                                         .property("status", fraud_result["status"])
                                         .property("rule", fraud_result["rule_name"])
                                         .property("evaluation_timestamp", datetime.now().isoformat())
                                         .property("reason", fraud_result["reason"])
                                         .property("details", str(fraud_result["details"]))
                                         .next())
                    
                    # Create flagged_by edge from transaction to fraud result
                    # Use proper Gremlin syntax with __ for child traversals (same as RT1)
                    edge = (self.graph_service.client.add_e("flagged_by")
                           .from_(__.V(transaction['id']))
                           .to(__.V(fraud_result_vertex.id))
                           .next())
                    
                    logger.info(f"📊 Created RT2 FraudCheckResult for transaction {transaction['id']}: {fraud_result['status']} (Score: {fraud_result['fraud_score']})")
                    return True
                    
                except Exception as e:
                    logger.error(f"Error creating RT2 fraud check result: {e}")
                    return False
            
            await loop.run_in_executor(None, create_fraud_result)
            
        except Exception as e:
            logger.error(f"❌ Error creating RT2 fraud check result for transaction {transaction.get('id', 'unknown')}: {e}")
    
    def enable(self):
        """Enable RT2 fraud detection"""
        self.enabled = True
        logger.info("✅ RT2 Fraud Detection enabled")
    
    def disable(self):
        """Disable RT2 fraud detection"""
        self.enabled = False
        logger.info("🔇 RT2 Fraud Detection disabled")
    
    def get_status(self) -> Dict[str, Any]:
        """Get RT2 service status"""
        return {
            "service": "RT2_FlaggedDeviceDetection",
            "enabled": self.enabled,
            "description": "Detects transactions involving accounts connected to flagged devices"
        }