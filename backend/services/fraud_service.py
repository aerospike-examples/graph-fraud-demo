import asyncio
import logging
import time
import json
from datetime import datetime
from typing import Dict, Any
from gremlin_python.process.graph_traversal import __

from services.graph_service import GraphService
from services.performance_monitor import performance_monitor

# Setup logging
logger = logging.getLogger('fraud_detection.rt1')
logger.setLevel(logging.ERROR)

class FraudService:
    """Fraud Detection Service"""
    
    def __init__(self, graph_service: GraphService):
        self.graph_service = graph_service
        self.rt1_enabled = True
        self.rt2_enabled = True
        self.rt3_enabled = False
    
    
    # ----------------------------------------------------------------------------------------------------------
    # Control fraud check states
    # ----------------------------------------------------------------------------------------------------------


    def toggle_fraud_checks_state(self, check: str, enabled: bool):
        match check:
            case 'rt1':
                self.rt1_enabled = enabled
                return True
            case 'rt2':
                self.rt2_enabled = enabled
                return True
            case 'rt3':
                self.rt3_enabled = enabled
                return True
            case _:
                return False
    

    def get_fraud_checks_state(self):
        return {
            "rt1" : self.rt1_enabled,
            "rt2" : self.rt2_enabled,
            "rt3" : self.rt3_enabled
        }


    # ----------------------------------------------------------------------------------------------------------
    # Helper functions
    # ----------------------------------------------------------------------------------------------------------


    def _create_flagged_connection(self, account_id, role, level, score):
        return {
            "account_id": account_id,
            "role": role,
            "level": level,
            "fraud_score": score
        }
    

    def _create_fraud_result(self, score, status, details):
        return {
            "is_fraud": True,
            "fraud_score": score,
            "status": status,
            "eval_timestamp": datetime.now().isoformat(),
            "details": details
        }

    async def _store_fraud_results(self, edge_id: str, fraud_checks: Dict[str, Dict[str, Any]]):
        try:
            fraud_score = 0
            details = []
            status = "review"
            checks = [
                fraud_checks.get("rt1", {}),
                fraud_checks.get("rt2", {}),
                fraud_checks.get("rt3", {})
            ]

            for check in checks:
                if not check == {}:
                    this_fraud = check.get("fraud_score", 0)
                    this_details = check.get("details", {})
                    this_status = check.get("status", "review")

                    fraud_score = this_fraud if this_fraud > fraud_score else fraud_score
                    details.append(json.dumps(this_details))
                    status = "blocked" if this_status == "blocked" else status
            
            loop = asyncio.get_event_loop()
            def write_fraud_result():
                # Create fraud check result in graph
                (self.graph_service.client.E(edge_id)
                    .property("is_fraud", True)
                    .property("fraud_score", fraud_score)
                    .property("fraud_status", status)
                    .property("eval_timestamp", datetime.now().isoformat())
                    .property("details", details)
                    .next())
            await loop.run_in_executor(None, write_fraud_result)
            
        except Exception as e:
            raise Exception(f"Error storing fraud result: {e}")
        

    # ----------------------------------------------------------------------------------------------------------
    # Run fraud checks
    # ----------------------------------------------------------------------------------------------------------


    async def run_fraud_detection(self, edge_id: str, txn_id: str):
        """Run fraud detection on the transaction"""
        
        if not self.graph_service.client:
            logger.warning("⚠️ Graph client not available for fraud detection")
            return
        
        try:
            fraud_checks = {}
            # Run RT1 fraud detection (flagged accounts)
            if self.rt1_enabled:
                rt1_fraud, rt1_reason, rt1_result = await self.run_rt1_fraud_detection(edge_id, txn_id)
                if rt1_fraud:
                    fraud_checks["rt1"] = rt1_result
                    logger.warning(f"🚨 RT1 FRAUD ALERT: {rt1_reason}")
        
        except Exception as e:
            raise Exception(f"❌ Error in RT1 fraud detection for transaction {txn_id}: {e}")
        
        try:
            # Run RT2 fraud detection (flagged devices)
            if self.rt2_enabled:
                rt2_fraud, rt2_reason, rt2_result = await self.run_rt2_fraud_detection(edge_id, txn_id)
                if rt2_fraud:
                    fraud_checks["rt2"] = rt2_result
                    logger.warning(f"🚨 RT2 FRAUD ALERT: {rt2_reason}")
        
        except Exception as e:
            raise Exception(f"❌ Error in RT2 fraud detection for transaction {txn_id}: {e}")

        try:
            # Run RT3 fraud detection (account velocity) for now
            if self.rt3_enabled:
                rt3_fraud, rt3_reason, rt3_result = await self.run_rt3_fraud_detection(edge_id, txn_id)
                if rt3_fraud: 
                    fraud_checks["rt3"] = rt3_result
                    logger.warning(f"🚨 RT3 FRAUD ALERT: {rt3_reason}")
        
        except Exception as e:
            raise Exception(f"❌ Error in RT3 fraud detection for transaction {txn_id}: {e}")    
        
        if not fraud_checks == {}:
            await self._store_fraud_results(edge_id, fraud_checks)
                

    # ----------------------------------------------------------------------------------------------------------
    # Fraud check functions
    # ----------------------------------------------------------------------------------------------------------


    async def run_rt1_fraud_detection(self, edge_id, txn_id) -> tuple[bool, str, Dict[str, Any]]:
        """
        RT1 Fraud Detection Service - Flagged Account Detection

        Check if transaction involves flagged accounts (RT1)
        1. RT1 checks if the sender or receiver (accounts)of a transaction is flagged as fraudulent.
        2. If sender or receiver accounts have other transactions with accounts flagged as fraud - calculate a fraud score based on the number of such connections
        """
        start_time = time.time()
        try:
            # Get event loop for async operations
            loop = asyncio.get_event_loop()
                        
            def check_flagged_connections():
                try:
                    return (self.graph_service.client.E(edge_id)
                        .project("sender", "receiver")
                        .by(__.inV()
                            .project("direct", "out_1")
                            .by(__.has("fraud_flag", True).id_())
                            .by(__.bothE("TRANSACTS")
                                .has("fraud_flag", True).id_().dedup().fold()))
                        .by(__.outV()
                            .project("direct", "out_1")
                            .by(__.has("fraud_flag", True).id_())
                            .by(__.bothE("TRANSACTS")
                                .has("fraud_flag", True).id_().dedup().fold()))
                        .next())
                    
                except Exception as e:
                    logger.error(f"Error checking flagged connections: {e}")
                    return {}
            
            connections = await loop.run_in_executor(None, check_flagged_connections)

            sender = connections.get("sender", {})
            sender_direct = sender.get("direct", "")
            sender_out_1 = sender.get("out_1", [])

            receiver = connections.get("receiver", {})
            receiver_direct = receiver.get("direct", "")
            receiver_out_1 = receiver.get("out_1", [])

            if not sender_direct and len(sender_out_1) < 1 and not receiver_direct and len(receiver_out_1) < 1:
                execution_time = (time.time() - start_time) * 1000
                performance_monitor.record_rt1_performance(execution_time, success=True)
                
                logger.info(f"✅ RT1 CHECK PASSED: Transaction {txn_id} - No flagged account connections")
                return False, "No flagged accounts involved", None
            
            flagged_connections = []
            max_level = 0
            
            if sender_direct:
                flagged_connections.append(self._create_flagged_connection(sender_direct, "sender", 0, 100))
            if receiver_direct:
                flagged_connections.append(self._create_flagged_connection(receiver_direct, "receiver", 0, 100))
            if len(sender_out_1) > 0:
                max_level = 1
                for conn in sender_out_1:    
                    flagged_connections.append(self._create_flagged_connection(conn, "sender_txn_partner", 1, 75))
            if len(sender_out_1) > 0:
                max_level = 1
                for conn in receiver_out_1:          
                    flagged_connections.append(self._create_flagged_connection(conn, "receiver_txn_partner", 1, 75))
           
            total_connections = len(flagged_connections)
                
            # Simple scoring: direct fraud = 100, transaction partners = 75
            fraud_score = 100 if max_level == 0 else min(75 + total_connections * 5, 95)
            status = "blocked" if fraud_score >= 90 else "review"
            reason = f"Connected to {total_connections} flagged account(s) - {'direct fraud' if max_level == 0 else 'transaction partners'}"
            details = {
                "flagged_connections": flagged_connections,
                "max_level": max_level,
                "total_connections": total_connections,
                "detection_time": datetime.now().isoformat(),
                "fraud_score": fraud_score,
                "reason": reason,
                "rule": "RT1_MultiLevelFlaggedAccountRule"
            }            
            fraud_result = self._create_fraud_result(fraud_score, status, details)

            execution_time = (time.time() - start_time) * 1000
            performance_monitor.record_rt1_performance(execution_time, success=True)
            
            return True, reason, fraud_result
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            performance_monitor.record_rt1_performance(execution_time, success=False)
            
            logger.error(f"❌ Error in RT1 fraud detection for transaction {txn_id}: {e}")
            return False, f"Detection error: {str(e)}", None


    async def run_rt2_fraud_detection(self, edge_id, txn_id) -> tuple[bool, str, Dict[str, Any] | None]:
        """RT2 Fraud Detection: Flagged Device Detection

        Check if transaction involves accounts connected to flagged devices
        Now checks connected accounts through transaction history, not just direct participants
        """

        start_time = time.time()
        try:
            # Get event loop for async operations
            loop = asyncio.get_event_loop()
                        
            def check_flagged_devices():
                try:
                    return (self.graph_service.client.E(edge_id)
                        .project("sender", "receiver", "accounts", "devices")
                        .by(__.inV().in_("OWNS").id_())
                        .by(__.outV().in_("OWNS").id_())
                        .by(__.bothV().in_("OWNS").out("OWNS")
                            .both("TRANSACTS").in_("OWNS").id_()
                            .dedup().fold())
                        .by(__.bothV().in_("OWNS").out("OWNS")
                            .both("TRANSACTS").in_("OWNS").out("USES")
                            .has("fraud_flag", True).id_()
                            .dedup().fold())
                        .next())
                    
                except Exception as e:
                    logger.error(f"Error checking flagged connections: {e}")
                    return {}
            
            results = await loop.run_in_executor(None, check_flagged_devices)
            sender = results.get("sender", "")
            receiver = results.get("receiver", "")
            accounts = results.get("accounts", [])
            devices = results.get("devices", [])

            if len(devices) < 1:
                execution_time = (time.time() - start_time) * 1000
                performance_monitor.record_rt2_performance(execution_time, success=True)
                
                logger.info(f"✅ RT2: Transaction {txn_id} passed flagged device check in transaction network")              
                return False, "No flagged devices connected to transaction network", None
            
            fraud_score = 85
            reason = f"Transaction involves accounts connected to flagged devices in transaction network: {', '.join(devices)}"
            details = {
                "flagged_devices": devices,
                "sender_account": sender,
                "receiver_account": receiver,
                "connected_accounts_checked": len(accounts),
                "detection_time": datetime.now().isoformat(),
                "fraud_score": fraud_score,
                "reason": reason,
                "rule": "RT2_FlaggedDeviceConnection"
            }
            fraud_result = self._create_fraud_result(fraud_score, "review", details)
            
            execution_time = (time.time() - start_time) * 1000
            performance_monitor.record_rt2_performance(execution_time, success=True)

            return True, reason, fraud_result
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            performance_monitor.record_rt2_performance(execution_time, success=False)
            
            logger.error(f"❌ RT2: Error checking transaction {txn_id}: {e}")
            logger.error(f"📊 RT2 Error - Total execution time: {execution_time:.2f}ms before failure")
            return False, f"RT2 check failed: {str(e)}", None


    async def run_rt3_fraud_detection(self, edge_id, txn_id) -> tuple[bool, str, Dict[str, Any] | None]:
        """RT3 Fraud Detection Service - Supernode Detection
        
        Check if transaction receiver is a supernode (RT3)
        """
        start_time = time.time()
        try:           
            # # Get event loop for async operations
            # loop = asyncio.get_event_loop()
            
            # def count_unique_senders():
            #     # try:
            #         # Get the lookback timestamp
            #         # lookback_timestamp = RT3_CONFIG.get_lookback_timestamp().isoformat()
                    
            #         # # Count unique sender accounts that have sent transactions to this receiver
            #         # # in the last N days using proper Gremlin traversal
            #         # unique_senders_query = f"""
            #         # g.V().has_label("account").has("id", "{receiver_account_id}")
            #         # .in_("TRANSFERS_TO")
            #         # .has("timestamp", P.gte("{lookback_timestamp}"))
            #         # .in_("TRANSFERS_TO")
            #         # .dedup()
            #         # .count()
            #         # """
                    
            #         # unique_sender_count = self.graph_service.client.submit(unique_senders_query).next()
                    
            #         # # Get sample sender account details for reporting
            #         # sender_details_query = f"""
            #         # g.V().has_label("account").has("id", "{receiver_account_id}")
            #         # .in_("TRANSFERS_TO")
            #         # .has("timestamp", P.gte("{lookback_timestamp}"))
            #         # .in_("TRANSFERS_TO")
            #         # .dedup()
            #         # .valueMap("id", "user_id")
            #         # .limit(100)
            #         # .toList()
            #         # """
                    
            #         # sender_details = self.graph_service.client.submit(sender_details_query).all().result()
                    
            #         # return {
            #         #     'unique_sender_count': unique_sender_count,
            #         #     'sender_details': sender_details,
            #         #     'lookback_timestamp': lookback_timestamp
            #         # }
                    
            #     # except Exception as e:
            #     #     logger.error(f"Error in RT3 graph query: {e}")
            #     #     return {'unique_sender_count': 0, 'sender_details': [], 'lookback_timestamp': None}
            
            # # Execute the graph query
            # result = await loop.run_in_executor(None, count_unique_senders)
            # unique_sender_count = result['unique_sender_count']
            # sender_details = result['sender_details']
            
            # logger.info(f"📊 RT3 ANALYSIS: Receiver account {receiver_account_id} has received from {unique_sender_count} unique senders in last {RT3_CONFIG.LOOKBACK_DAYS} days")
            
            # # Calculate fraud score using RT3 configuration
            # fraud_score = RT3_CONFIG.calculate_fraud_score(unique_sender_count)
            
            # # Check if this qualifies as fraud (supernode)
            # if fraud_score > 0:
            #     status = RT3_CONFIG.get_fraud_status(fraud_score)
            #     reason = RT3_CONFIG.get_fraud_reason(unique_sender_count)
                
            #     fraud_result = {
            #         "is_fraud": True,
            #         "fraud_score": fraud_score,
            #         "status": status,
            #         "reason": reason,
            #         "rule_name": "RT3_SupernodeRule",
            #         "details": {
            #             'unique_sender_count': unique_sender_count,
            #             'threshold': RT3_CONFIG.MIN_UNIQUE_SENDERS_THRESHOLD,
            #             'lookback_days': RT3_CONFIG.LOOKBACK_DAYS,
            #             'sender_sample': sender_details[:10],  # Include first 10 senders as sample
            #             'detection_method': 'RT3_Supernode_Detection'
            #         }
            #     }

            #     (self.graph_service.client.add_v("FraudCheckResult")
            #         .property("fraud_score", fraud_result["fraud_score"])
            #         .property("status", fraud_result["status"])
            #         .property("rule", fraud_result["rule_name"])
            #         .property("evaluation_timestamp", datetime.now().isoformat())
            #         .property("reason", fraud_result["reason"])
            #         .property("details", str(fraud_result["details"]))
            #         .next())
                
            #     execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            #     performance_monitor.record_rt3_performance(execution_time, success=True)
                
            #     logger.warning(f"🚨 RT3 FRAUD DETECTED: Transaction {transaction['id']} - {reason} (Score: {fraud_score})")
            #     return fraud_result
            # else:
            #     execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            #     performance_monitor.record_rt3_performance(execution_time, success=True)
                
            #     logger.info(f"✅ RT3 CHECK PASSED: Transaction {transaction['id']} - Receiver account within normal connection limits ({unique_sender_count} senders)")
            #     return {"is_fraud": False, "reason": f"Normal connection pattern ({unique_sender_count} senders)"}
            pass    
        except Exception as e:
            # execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            # performance_monitor.record_rt3_performance(execution_time, success=False)
            
            # logger.error(f"❌ Error in RT3 fraud detection for transaction {transaction.get('id', 'unknown')}: {e}")
            # return {"is_fraud": False, "reason": f"Detection error: {str(e)}"}
            pass