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
            
            # We already have the account IDs in the transaction, no need to fetch them from the graph
            sender_account_id = transaction.get('account_id', '')
            receiver_account_id = transaction.get('receiver_account_id', '')
            
            if not sender_account_id or not receiver_account_id:
                logger.warning(f"⚠️ Missing account IDs in transaction: sender={sender_account_id}, receiver={receiver_account_id}")
                return {"is_fraud": False, "reason": "Missing account information"}
            
            logger.info(f"🔍 RT1 CHECK: Analyzing transaction {transaction['id']} for multi-level flagged account connections (Sender: {sender_account_id}, Receiver: {receiver_account_id})")
            
            def check_flagged_connections():
                try:
                    flagged_connections = []
                    
                    # Level 0: Check if sender account is directly flagged
                    sender_flagged = (self.graph_service.client.V()
                                    .has_label("account")
                                    .has("id", sender_account_id)
                                    .has("fraud_flag", True)
                                    .next())
                    
                    if sender_flagged:
                        flagged_connections.append({
                            "account_id": sender_account_id,
                            "role": "sender",
                            "level": 0,
                            "fraud_score": 100
                        })
                    
                    # Level 0: Check if receiver account is directly flagged
                    receiver_flagged = (self.graph_service.client.V()
                                      .has_label("account")
                                      .has("id", receiver_account_id)
                                      .has("fraud_flag", True)
                                      .next())
                    
                    if receiver_flagged:
                        flagged_connections.append({
                            "account_id": receiver_account_id,
                            "role": "receiver",
                            "level": 0,
                            "fraud_score": 100
                        })
                    
                    # Level 1: Check accounts connected via 1 transaction to sender
                    sender_connections = (self.graph_service.client.V()
                                       .has_label("account")
                                       .has("id", sender_account_id)
                                       .both("TRANSFERS_TO", "TRANSFERS_FROM")
                                       .has_label("transaction")
                                       .both("TRANSFERS_TO", "TRANSFERS_FROM")
                                       .has_label("account")
                                       .has("fraud_flag", True)
                                       .dedup()
                                       .to_list())
                    
                    for conn in sender_connections:
                        flagged_connections.append({
                            "account_id": conn.get("id", [""])[0] if isinstance(conn.get("id"), list) else conn.get("id", ""),
                            "role": "sender_connection",
                            "level": 1,
                            "fraud_score": 95
                        })
                    
                    # Level 1: Check accounts connected via 1 transaction to receiver
                    receiver_connections = (self.graph_service.client.V()
                                         .has_label("account")
                                         .has("id", receiver_account_id)
                                         .both("TRANSFERS_TO", "TRANSFERS_FROM")
                                         .has_label("transaction")
                                         .both("TRANSFERS_TO", "TRANSFERS_FROM")
                                         .has_label("account")
                                         .has("fraud_flag", True)
                                         .dedup()
                                         .to_list())
                    
                    for conn in receiver_connections:
                        flagged_connections.append({
                            "account_id": conn.get("id", [""])[0] if isinstance(conn.get("id"), list) else conn.get("id", ""),
                            "role": "receiver_connection",
                            "level": 1,
                            "fraud_score": 95
                        })
                    
                    # Level 2: Check accounts connected via 2 transactions (deeper connections)
                    sender_deep_connections = (self.graph_service.client.V()
                                            .has_label("account")
                                            .has("id", sender_account_id)
                                            .both("TRANSFERS_TO", "TRANSFERS_FROM")
                                            .has_label("transaction")
                                            .both("TRANSFERS_TO", "TRANSFERS_FROM")
                                            .has_label("account")
                                            .both("TRANSFERS_TO", "TRANSFERS_FROM")
                                            .has_label("transaction")
                                            .both("TRANSFERS_TO", "TRANSFERS_FROM")
                                            .has_label("account")
                                            .has("fraud_flag", True)
                                            .dedup()
                                            .to_list())
                    
                    for conn in sender_deep_connections:
                        flagged_connections.append({
                            "account_id": conn.get("id", [""])[0] if isinstance(conn.get("id"), list) else conn.get("id", ""),
                            "role": "sender_deep_connection",
                            "level": 2,
                            "fraud_score": 85
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
                
                # Base score calculation: higher levels = lower scores, more connections = higher scores
                if max_level == 0:  # Direct fraud
                    fraud_score = 100
                elif max_level == 1:  # Level 1 connections
                    fraud_score = min(95 + total_connections * 2, 100)
                else:  # Level 2+ connections
                    fraud_score = min(85 + total_connections * 3, 95)
                
                status = "blocked" if fraud_score >= 95 else "review"
                reason = f"Connected to {total_connections} flagged account(s) at level {max_level}"
                
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