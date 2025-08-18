"""
RT1 Fraud Detection Service
Real-time detection of transactions involving flagged accounts

This service implements RT1 fraud detection which checks if a transaction
involves accounts that have been previously flagged as fraudulent.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, List
from services.graph_service import GraphService
from services.performance_monitor import performance_monitor

# Setup logging
logger = logging.getLogger('fraud_detection.rt1')

class RT1FraudService:
    """RT1 Fraud Detection Service - Flagged Account Detection"""
    
    def __init__(self, graph_service: GraphService):
        self.graph_service = graph_service
    
    async def check_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if transaction involves flagged accounts (RT1)
        1. RT1 checks if the sender or receiver (accounts)of a transaction is flagged as fraudulent.
        2. If sender or receiver accounts have other transactions with accounts flagged as fraud - calculate a fraud score based on the number of such connections
        
        Args:
            transaction: Transaction data
            
        Returns:
            Dict with fraud detection results
        """
        start_time = time.time()
        try:
            if not self.graph_service.client:
                logger.warning("⚠️ Graph client not available for RT1 fraud detection")
                return {"is_fraud": False, "reason": "Graph client unavailable"}
            
            # Get sender and receiver account IDs from graph relationships
            # sender_account --TRANSFERS_TO--> transaction --TRANSFERS_FROM--> receiver_account
            
            loop = asyncio.get_event_loop()
            
            def get_account_ids():
                try:
                    # Find the transaction vertex
                    # tx_vertex = self.graph_service.client.V().has_label("transaction").has("transaction_id", transaction['id']).next()
                    tx_vertex = self.graph_service.client.V().has_label("transaction").has("transaction_id", transaction['id']).next()
                    
                    
                    # Get sender account (incoming TRANSFERS_TO edge)
                    sender_accounts = self.graph_service.client.V(tx_vertex).in_("TRANSFERS_TO").has_label("account").valueMap("account_id").to_list()
                    sender_account_id = sender_accounts[0].get("account_id", [""])[0] if sender_accounts else ""
                    
                    # Get receiver account (outgoing TRANSFERS_FROM edge)
                    receiver_accounts = self.graph_service.client.V(tx_vertex).out("TRANSFERS_FROM").has_label("account").valueMap("account_id").to_list()
                    receiver_account_id = receiver_accounts[0].get("account_id", [""])[0] if receiver_accounts else ""
                    
                    return sender_account_id, receiver_account_id
                except Exception as e:
                    logger.error(f"Error getting account IDs: {e}")
                    return "", ""
            
            sender_account_id, receiver_account_id = await loop.run_in_executor(None, get_account_ids)
            
            logger.info(f"🔍 RT1 CHECK: Analyzing transaction {transaction['id']} for flagged account connections (Sender: {sender_account_id}, Receiver: {receiver_account_id})")
            
            def check_flagged_connections():
                try:
                    flagged_connections = []
                    
                    # Check if sender account is flagged
                    sender_flagged = (self.graph_service.client.V()
                                    .has_label("account")
                                    .has("account_id", sender_account_id)
                                    .has("fraud_flag", True)
                                    .to_list())
                    
                    if sender_flagged:
                        flagged_connections.extend([{
                            "account_id": conn.get("account_id", [""])[0],
                            "user_id": conn.get("user_id", [""])[0],
                            "role": "sender"
                        } for conn in sender_flagged])
                    
                    # Check if receiver account is flagged
                    receiver_flagged = (self.graph_service.client.V()
                                      .has_label("account")
                                      .has("account_id", receiver_account_id)
                                      .has("fraud_flag", True)
                                      .to_list())
                    
                    if receiver_flagged:
                        flagged_connections.extend([{
                            "account_id": conn.get("account_id", [""])[0],
                            "flag_reason": conn.get("flagReason", ["Unknown"])[0],
                            "user_id": conn.get("user_id", [""])[0],
                            "role": "receiver"
                        } for conn in receiver_flagged])
                    
                    return flagged_connections
                    
                except Exception as e:
                    logger.error(f"Error checking flagged connections: {e}")
                    return []
            
            flagged_connections = await loop.run_in_executor(None, check_flagged_connections)
            
            # If flagged connections found, calculate fraud score and status
            if flagged_connections:
                fraud_score = min(90 + len(flagged_connections) * 5, 100)  # Score 90-100 based on number of connections
                status = "blocked" if fraud_score >= 95 else "review"
                reason = f"Connected to {len(flagged_connections)} flagged account(s)"
                
                fraud_result = {
                    "is_fraud": True,
                    "fraud_score": fraud_score,
                    "status": status,
                    "reason": reason,
                    "rule_name": "RT1_FlaggedAccountRule",
                    "details": {
                        "flagged_connections": flagged_connections,
                        "detection_method": "RT1_Flagged_Account_Detection"
                    }
                }
                
                execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                performance_monitor.record_rt1_performance(execution_time, success=True)
                
                logger.warning(f"🚨 RT1 FRAUD DETECTED: Transaction {transaction['id']} - {reason} (Score: {fraud_score})")
                return fraud_result
            else:
                execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                performance_monitor.record_rt1_performance(execution_time, success=True)
                
                logger.info(f"✅ RT1 CHECK PASSED: Transaction {transaction['id']} - No flagged account connections")
                return {"is_fraud": False, "reason": "No flagged accounts involved"}
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            performance_monitor.record_rt1_performance(execution_time, success=False)
            
            logger.error(f"❌ Error in RT1 fraud detection for transaction {transaction.get('id', 'unknown')}: {e}")
            return {"is_fraud": False, "reason": f"Detection error: {str(e)}"}
    
    async def create_fraud_check_result(self, transaction: Dict[str, Any], fraud_result: Dict[str, Any]):
        """Create FraudCheckResult vertex and flagged_by edge"""
        try:
            if not self.graph_service.client or not fraud_result.get("is_fraud"):
                return
                
            loop = asyncio.get_event_loop()
            
            def create_fraud_result():
                try:
                    # Find the transaction vertex
                    transaction_vertex = self.graph_service.client.V().has_label("transaction").has("transaction_id", transaction['id']).next()
                    
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
                    self.graph_service.client.add_e("flagged_by").from_(transaction_vertex).to(fraud_result_vertex).iterate()
                    
                    logger.info(f"📊 Created RT1 FraudCheckResult for transaction {transaction['id']}: {fraud_result['status']} (Score: {fraud_result['fraud_score']})")
                    return True
                    
                except Exception as e:
                    logger.error(f"Error creating RT1 fraud check result: {e}")
                    return False
            
            await loop.run_in_executor(None, create_fraud_result)
            
        except Exception as e:
            logger.error(f"❌ Error creating RT1 fraud check result for transaction {transaction.get('id', 'unknown')}: {e}") 