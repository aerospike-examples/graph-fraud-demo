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
from gremlin_python.process.graph_traversal import __

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
            
            # Get event loop for async operations
            loop = asyncio.get_event_loop()
            
            # We already have the account IDs in the transaction, no need to fetch them from the graph
            sender_account_id = transaction['account_id']
            receiver_account_id = transaction['receiver_account_id']

            
            if not sender_account_id or not receiver_account_id:
                logger.warning(f"⚠️ Missing account IDs in transaction: sender={sender_account_id}, receiver={receiver_account_id}")
                return {"is_fraud": False, "reason": "Missing account information"}
            
            logger.info(f"🔍 RT1 CHECK: Analyzing transaction {transaction['id']} for multi-level flagged account connections (Sender: {sender_account_id}, Receiver: {receiver_account_id})")
            
            def check_flagged_connections():
                try:
                    flagged_connections = []
                    sender_flagged = (self.graph_service.client.V(sender_account_id)
                                    .has("fraud_flag", True)
                                    .hasNext())   
                    if sender_flagged:
                        flagged_connections.append({
                            "account_id": sender_account_id,
                            "role": "sender",
                            "level": 0,
                            "fraud_score": 100
                        })
                    
                    receiver_flagged = (self.graph_service.client.V(receiver_account_id)
                                      .has("fraud_flag", True)
                                      .hasNext())
                    
                    if receiver_flagged:
                        flagged_connections.append({
                            "account_id": receiver_account_id,
                            "role": "receiver",
                            "level": 0,
                            "fraud_score": 100
                        })
                    
                    # Early exit optimization: If either sender or receiver is flagged (Level 0),
                    # we already have maximum fraud score, no need to check deeper connections
                    if sender_flagged or receiver_flagged:
                        logger.info(f"RT1: Direct fraud detected - sender: {sender_flagged}, receiver: {receiver_flagged}. Skipping deeper connection checks.")
                        return flagged_connections
                    
                    # Check if sender has done transactions with any flagged accounts
                    # Path: sender_account → transactions → connected_accounts → check if flagged
                    sender_connections = (self.graph_service.client.V(sender_account_id)
                                       .both("TRANSFERS_TO", "TRANSFERS_FROM")  # Go to transactions
                                       .both("TRANSFERS_TO", "TRANSFERS_FROM")  # Go from transactions to connected accounts
                                       .has("fraud_flag", True)                  # Check if flagged
                                       .dedup()                                  # Remove duplicates
                                       .to_list())
                    
                    # Process sender's flagged connections
                    if sender_connections:
                        for conn in sender_connections:
                            # Extract ID from vertex object
                            flagged_account_id = str(conn.id) if hasattr(conn, 'id') else str(conn)
                            if flagged_account_id and flagged_account_id != sender_account_id:
                                flagged_connections.append({
                                    "account_id": flagged_account_id,
                                    "role": "sender_transaction_partner",
                                    "level": 1,
                                    "fraud_score": 75
                                })
                    
                    # Check if receiver has done transactions with any flagged accounts
                    # Path: receiver_account → transactions → connected_accounts → check if flagged
                    receiver_connections = (self.graph_service.client.V(receiver_account_id)
                                         .both("TRANSFERS_TO", "TRANSFERS_FROM")  # Go to transactions
                                         .both("TRANSFERS_TO", "TRANSFERS_FROM")  # Go from transactions to connected accounts
                                         .has("fraud_flag", True)                  # Check if flagged
                                         .dedup()                                  # Remove duplicates
                                         .to_list())
                    
                    # Process receiver's flagged connections
                    if receiver_connections:
                        for conn in receiver_connections:
                            # Extract ID from vertex object
                            flagged_account_id = str(conn.id) if hasattr(conn, 'id') else str(conn)
                            if flagged_account_id and flagged_account_id != receiver_account_id:
                                flagged_connections.append({
                                    "account_id": flagged_account_id,
                                    "role": "receiver_transaction_partner",
                                    "level": 1,
                                    "fraud_score": 75
                                })
                    
                    return flagged_connections
                    
                except Exception as e:
                    logger.error(f"Error checking flagged connections: {e}")
                    return []
            
            flagged_connections = await loop.run_in_executor(None, check_flagged_connections)
            
            # Log the multi-level detection results
            if flagged_connections:
                level_counts = {}
                for conn in flagged_connections:
                    level = conn.get("level", 0)
                    level_counts[level] = level_counts.get(level, 0) + 1
                
                logger.info(f"🔍 RT1 MULTI-LEVEL RESULTS: Found {len(flagged_connections)} flagged connections:")
                for level, count in sorted(level_counts.items()):
                    logger.info(f"   Level {level}: {count} flagged account(s)")
            
            # If flagged connections found, calculate fraud score and status based on levels
            if flagged_connections:
                # Calculate fraud score based on connection levels and counts
                max_level = max(conn.get("level", 0) for conn in flagged_connections)
                total_connections = len(flagged_connections)
                
                # Simple scoring: direct fraud = 100, transaction partners = 75
                if max_level == 0:  # Direct fraud
                    fraud_score = 100
                else:  # Transaction partners
                    fraud_score = min(75 + total_connections * 5, 95)
                
                status = "blocked" if fraud_score >= 90 else "review"
                reason = f"Connected to {total_connections} flagged account(s) - {'direct fraud' if max_level == 0 else 'transaction partners'}"
                
                fraud_result = {
                    "is_fraud": True,
                    "fraud_score": fraud_score,
                    "status": status,
                    "reason": reason,
                    "rule_name": "RT1_MultiLevelFlaggedAccountRule",
                    "details": {
                        "flagged_connections": flagged_connections,
                        "max_level": max_level,
                        "total_connections": total_connections,
                        "detection_method": "RT1_MultiLevel_Flagged_Account_Detection"
                    }
                }
                
                execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                performance_monitor.record_rt1_performance(execution_time, success=True)
                
                logger.warning(f"🚨 RT1 FRAUD DETECTED: Transaction {transaction['id']} - {reason} (Score: {fraud_score})")
                
                # Create fraud check result in the graph
                logger.info(f"🔗 RT1: Calling create_fraud_check_result for transaction {transaction['id']}")
                await self.create_fraud_check_result(transaction, fraud_result)
                
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
        logger.info(f"🔗 RT1: create_fraud_check_result called for transaction {transaction.get('id', 'unknown')}")
        try:
            if not self.graph_service.client or not fraud_result.get("is_fraud"):
                logger.info(f"🔗 RT1: Skipping fraud result creation - graph client: {bool(self.graph_service.client)}, is_fraud: {fraud_result.get('is_fraud')}")
                return
            
            # Get event loop for async operations
            loop = asyncio.get_event_loop()
            
            def create_fraud_result():
                try:
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
                    # Use proper Gremlin syntax with __ for child traversals
                    edge = (self.graph_service.client.add_e("flagged_by")
                           .from_(__.V(transaction['id']))
                           .to(__.V(fraud_result_vertex.id))
                           .next())
                    
                    logger.info(f"📊 Created RT1 FraudCheckResult for transaction {transaction['id']}: {fraud_result['status']} (Score: {fraud_result['fraud_score']})")
                    return True
                    
                except Exception as e:
                    logger.error(f"Error creating RT1 fraud check result: {e}")
                    return False
            
            await loop.run_in_executor(None, create_fraud_result)
            
        except Exception as e:
            logger.error(f"❌ Error creating RT1 fraud check result for transaction {transaction.get('id', 'unknown')}: {e}") 