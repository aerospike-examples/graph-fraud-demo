"""
RT3 Fraud Detection Service
Real-time supernode detection for high-degree receiver accounts

This service implements RT3 fraud detection which identifies accounts that
receive transactions from an unusually high number of unique sender accounts
within a specified time window (supernode pattern).
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, List
from services.graph_service import GraphService
from services.performance_monitor import performance_monitor
from config.rt3_config import RT3_CONFIG

# Setup logging
logger = logging.getLogger('fraud_detection.rt3')

class RT3FraudService:
    """RT3 Fraud Detection Service - Supernode Detection"""
    
    def __init__(self, graph_service: GraphService):
        self.graph_service = graph_service
    
    async def check_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if transaction receiver is a supernode (RT3)
        
        Args:
            transaction: Transaction data
            
        Returns:
            Dict with fraud detection results
        """
        start_time = time.time()
        try:
            if not self.graph_service.client:
                logger.warning("⚠️ Graph client not available for RT3 fraud detection")
                return {"is_fraud": False, "reason": "Graph client unavailable"}
            
            # Get event loop for async operations
            loop = asyncio.get_event_loop()

            # We already have the receiver account ID in the transaction, no need to fetch it from the graph
            receiver_account_id = transaction.get('receiver_account_id', '')
            
            if not receiver_account_id:
                logger.warning(f"⚠️ Missing receiver account ID in transaction: {receiver_account_id}")
                return {"is_fraud": False, "reason": "Missing receiver account information"}
            logger.info(f"🔍 RT3 CHECK: Analyzing receiver account {receiver_account_id} for supernode patterns")
            
            def count_unique_senders():
                try:
                    # Get the lookback timestamp
                    lookback_timestamp = RT3_CONFIG.get_lookback_timestamp().isoformat()
                    
                    # Count unique sender accounts that have sent transactions to this receiver
                    # in the last N days using proper Gremlin traversal
                    unique_senders_query = f"""
                    g.V().has_label("account").has("id", "{receiver_account_id}")
                    .in_("TRANSFERS_TO")
                    .has("timestamp", P.gte("{lookback_timestamp}"))
                    .in_("TRANSFERS_TO")
                    .dedup()
                    .count()
                    """
                    
                    unique_sender_count = self.graph_service.client.submit(unique_senders_query).next()
                    
                    # Get sample sender account details for reporting
                    sender_details_query = f"""
                    g.V().has_label("account").has("id", "{receiver_account_id}")
                    .in_("TRANSFERS_TO")
                    .has("timestamp", P.gte("{lookback_timestamp}"))
                    .in_("TRANSFERS_TO")
                    .dedup()
                    .valueMap("id", "user_id")
                    .limit(100)
                    .toList()
                    """
                    
                    sender_details = self.graph_service.client.submit(sender_details_query).all().result()
                    
                    return {
                        'unique_sender_count': unique_sender_count,
                        'sender_details': sender_details,
                        'lookback_timestamp': lookback_timestamp
                    }
                    
                except Exception as e:
                    logger.error(f"Error in RT3 graph query: {e}")
                    return {'unique_sender_count': 0, 'sender_details': [], 'lookback_timestamp': None}
            
            # Execute the graph query
            result = await loop.run_in_executor(None, count_unique_senders)
            unique_sender_count = result['unique_sender_count']
            sender_details = result['sender_details']
            
            logger.info(f"📊 RT3 ANALYSIS: Receiver account {receiver_account_id} has received from {unique_sender_count} unique senders in last {RT3_CONFIG.LOOKBACK_DAYS} days")
            
            # Calculate fraud score using RT3 configuration
            fraud_score = RT3_CONFIG.calculate_fraud_score(unique_sender_count)
            
            # Check if this qualifies as fraud (supernode)
            if fraud_score > 0:
                status = RT3_CONFIG.get_fraud_status(fraud_score)
                reason = RT3_CONFIG.get_fraud_reason(unique_sender_count)
                
                fraud_result = {
                    "is_fraud": True,
                    "fraud_score": fraud_score,
                    "status": status,
                    "reason": reason,
                    "rule_name": "RT3_SupernodeRule",
                    "details": {
                        'unique_sender_count': unique_sender_count,
                        'threshold': RT3_CONFIG.MIN_UNIQUE_SENDERS_THRESHOLD,
                        'lookback_days': RT3_CONFIG.LOOKBACK_DAYS,
                        'sender_sample': sender_details[:10],  # Include first 10 senders as sample
                        'detection_method': 'RT3_Supernode_Detection'
                    }
                }

                (self.graph_service.client.add_v("FraudCheckResult")
                    .property("fraud_score", fraud_result["fraud_score"])
                    .property("status", fraud_result["status"])
                    .property("rule", fraud_result["rule_name"])
                    .property("evaluation_timestamp", datetime.now().isoformat())
                    .property("reason", fraud_result["reason"])
                    .property("details", str(fraud_result["details"]))
                    .next())
                
                execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                performance_monitor.record_rt3_performance(execution_time, success=True)
                
                logger.warning(f"🚨 RT3 FRAUD DETECTED: Transaction {transaction['id']} - {reason} (Score: {fraud_score})")
                return fraud_result
            else:
                execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                performance_monitor.record_rt3_performance(execution_time, success=True)
                
                logger.info(f"✅ RT3 CHECK PASSED: Transaction {transaction['id']} - Receiver account within normal connection limits ({unique_sender_count} senders)")
                return {"is_fraud": False, "reason": f"Normal connection pattern ({unique_sender_count} senders)"}
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            performance_monitor.record_rt3_performance(execution_time, success=False)
            
            logger.error(f"❌ Error in RT3 fraud detection for transaction {transaction.get('id', 'unknown')}: {e}")
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
                    
                    logger.info(f"📊 Created RT3 FraudCheckResult for transaction {transaction['id']}: {fraud_result['status']} (Score: {fraud_result['fraud_score']})")
                    return True
                    
                except Exception as e:
                    logger.error(f"Error creating RT3 fraud check result: {e}")
                    return False
            
            await loop.run_in_executor(None, create_fraud_result)
            
        except Exception as e:
            logger.error(f"❌ Error creating RT3 fraud check result for transaction {transaction.get('id', 'unknown')}: {e}") 