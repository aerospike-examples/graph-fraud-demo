import logging
import time
import json
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, Any
from gremlin_python.process.graph_traversal import __

from services.graph_service import GraphService
from services.performance_monitor import performance_monitor

from logging_config import get_logger
logger = get_logger('fraud_detection.fraud')

class FraudService:
    """Fraud Detection Service"""
    
    def __init__(self, graph_service: GraphService):
        self.graph_service = graph_service
        self.rt1_enabled = True
        self.rt2_enabled = True
        self.rt3_enabled = True
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=64, thread_name_prefix="fraud_rt")

    def shutdown(self):
        """Shutdown the fraud service executor"""
        try:
            logger.info("Shutting down fraud service executor...")
            self._executor.shutdown(wait=True, cancel_futures=True)
            logger.info("Fraud service executor shutdown complete")
        except Exception as e:
            logger.warning(f"Error shutting down fraud executor: {e}")
            self._executor.shutdown(wait=True)

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
            "rt1": self.rt1_enabled,
            "rt2": self.rt2_enabled,
            "rt3": self.rt3_enabled
        }

    def _create_flagged_connection(self, account_id, role, score):
        return {
            "account_id": account_id,
            "role": role,
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


    def _store_fraud_results(self, edge_id: str, fraud_checks: Dict[str, Dict[str, Any]]):
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
            
            (self.graph_service.main_client.E(edge_id)
                .property("is_fraud", True)
                .property("fraud_score", fraud_score)
                .property("fraud_status", status)
                .property("eval_timestamp", datetime.now().isoformat())
                .property("details", details)
                .next())
            
        except Exception as e:
            raise Exception(f"Error storing fraud result: {e}")

    def submit_fraud_detection_async(self, edge_id: str, txn_id: str):
        """Submit fraud detection without blocking the caller"""
        return self._executor.submit(self.run_fraud_detection, edge_id, txn_id)

    def run_fraud_detection(self, edge_id: str, txn_id: str):
        """Run fraud detection on the transaction in parallel"""
        fraud_start_time = time.time()

        if not self.graph_service.fraud_client:
            logger.warning("Graph client not available for fraud detection")
            return

        fraud_checks = {}

        if self.rt1_enabled:
            rt_fraud, rt_reason, rt_result = self.run_rt1_fraud_detection(edge_id, txn_id)
            if rt_fraud:
                fraud_checks['rt1'] = rt_result
        if self.rt2_enabled:
            rt_fraud, rt_reason, rt_result = self.run_rt2_fraud_detection(edge_id, txn_id)
            if rt_fraud:
                fraud_checks['rt2'] = rt_result
        if self.rt3_enabled:
            rt_fraud, rt_reason, rt_result = self.run_rt3_fraud_detection(edge_id, txn_id)
            if rt_fraud:
                fraud_checks['rt3'] = rt_result
        
        if fraud_checks:
            try:
                self._store_fraud_results(edge_id, fraud_checks)
            except Exception as e:
                logger.error(f"Error storing fraud results for transaction {txn_id}: {e}")

        fraud_end_time = time.time()
        fraud_latency_ms = (fraud_end_time - fraud_start_time) * 1000
        
        from services.performance_monitor import performance_monitor
        performance_monitor.record_fraud_detection_latency(fraud_latency_ms, txn_id)

    def run_rt1_fraud_detection(self, edge_id, txn_id) -> tuple[bool, str, Dict[str, Any]]:
        """RT1 Fraud Detection: Check if transaction involves flagged accounts"""
        start_time = time.time()
        try:
            connections = (self.graph_service.fraud_client.E(edge_id)
                .project("sender", "receiver")
                .by(__.outV().has("fraud_flag", True).id_())
                .by(__.inV().has("fraud_flag", True).id_())
                .next())

            sender = connections.get("sender", None)
            receiver = connections.get("receiver", None)

            if not sender and not receiver:
                execution_time = (time.time() - start_time) * 1000
                performance_monitor.record_rt1_performance(execution_time, success=True)
                
                logger.info(f"RT1 CHECK PASSED: Transaction {txn_id} - No flagged account connections")
                return False, "No flagged accounts involved", None
            
            flagged_connections = []
            
            if sender:
                flagged_connections.append(self._create_flagged_connection(sender, "sender", 100))
            if receiver:
                flagged_connections.append(self._create_flagged_connection(receiver, "receiver", 100))
           
            total_connections = len(flagged_connections)
                
            fraud_score = 100
            status = "blocked"
            reason = f"Connected to {total_connections} flagged account(s) - 'direct fraud'"
            details = {
                "flagged_connections": flagged_connections,
                "detection_time": datetime.now().isoformat(),
                "fraud_score": fraud_score,
                "reason": reason,
                "rule": "RT1_SingleLevelFlaggedAccountRule"
            }            
            fraud_result = self._create_fraud_result(fraud_score, status, details)

            execution_time = (time.time() - start_time) * 1000
            performance_monitor.record_rt1_performance(execution_time, success=True)
            
            return True, reason, fraud_result
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            performance_monitor.record_rt1_performance(execution_time, success=False)
            
            logger.error(f"Error in RT1 fraud detection for transaction {txn_id}: {e}")
            return False, f"Detection error: {str(e)}", None


    def run_rt2_fraud_detection(self, edge_id, txn_id) -> tuple[bool, str, Dict[str, Any]]:
        """
        RT2 Fraud Detection Service - Flagged Account Detection

        Check if transaction involves users connected to flagged accounts (RT2)
        1. RT2 checks if sender or receiver accounts have other transactions with accounts flagged as fraud
        2. Calculate a fraud score based on the number of such connections
        """
        start_time = time.time()
        try:
            connections = (self.graph_service.fraud_client.E(edge_id)
                .project("sender", "receiver")
                .by(__.outV()
                        .bothE("TRANSACTS").bothV()
                        .has("fraud_flag", True).id_().dedup().fold())
                .by(__.inV()
                        .bothE("TRANSACTS").bothV()
                        .has("fraud_flag", True).id_().dedup().fold())
                .next())
                    
            sender = connections.get("sender", [])
            receiver = connections.get("receiver", [])

            if len(sender) < 1 and len(receiver) < 1:
                execution_time = (time.time() - start_time) * 1000
                performance_monitor.record_rt2_performance(execution_time, success=True)
                
                logger.info(f"RT2 CHECK PASSED: Transaction {txn_id} - No flagged account connections")
                return False, "No flagged accounts involved", None
            
            flagged_connections = []
            
            if len(sender) > 0:
                for conn in sender:    
                    flagged_connections.append(self._create_flagged_connection(conn, "sender_txn_partner", 75))
            if len(receiver) > 0:
                for conn in receiver:          
                    flagged_connections.append(self._create_flagged_connection(conn, "receiver_txn_partner", 75))
           
            total_connections = len(flagged_connections)
                
            # Simple scoring: direct fraud = 100, transaction partners = 75
            fraud_score = min(75 + total_connections * 5, 95)
            status = "blocked" if fraud_score >= 90 else "review"
            reason = f"Connected to {total_connections} flagged account(s) - transaction partners"
            details = {
                "flagged_connections": flagged_connections,
                "total_connections": total_connections,
                "detection_time": datetime.now().isoformat(),
                "fraud_score": fraud_score,
                "reason": reason,
                "rule": "RT2_MultiLevelFlaggedAccountRule"
            }            
            fraud_result = self._create_fraud_result(fraud_score, status, details)

            execution_time = (time.time() - start_time) * 1000
            performance_monitor.record_rt2_performance(execution_time, success=True)
            
            return True, reason, fraud_result
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            performance_monitor.record_rt2_performance(execution_time, success=False)
            
            logger.error(f"Error in RT2 fraud detection for transaction {txn_id}: {e}")
            return False, f"Detection error: {str(e)}", None


    def run_rt3_fraud_detection(self, edge_id, txn_id) -> tuple[bool, str, Dict[str, Any] | None]:
        """
        RT3 Fraud Detection: Flagged Device Detection

        Check if transaction involves accounts connected to flagged devices
        Now checks connected accounts through transaction history, not just direct participants
        """

        start_time = time.time()
        try:
            results = (self.graph_service.fraud_client.E(edge_id)
                .project("sender", "receiver", "accounts", "devices")
                .by(__.outV().in_("OWNS").id_())
                .by(__.inV().in_("OWNS").id_())
                .by(__.bothV().in_("OWNS").out("OWNS")
                    .both("TRANSACTS").in_("OWNS").id_()
                    .dedup().fold())
                .by(__.bothV().in_("OWNS").out("OWNS")
                    .both("TRANSACTS").in_("OWNS").out("USES")
                    .has("fraud_flag", True).id_()
                    .dedup().fold())
                .next())
                    
            sender = results.get("sender", "")
            receiver = results.get("receiver", "")
            accounts = results.get("accounts", [])
            devices = results.get("devices", [])

            if len(devices) < 1:
                execution_time = (time.time() - start_time) * 1000
                performance_monitor.record_rt3_performance(execution_time, success=True)
                
                logger.info(f"RT3: Transaction {txn_id} passed flagged device check in transaction network")              
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
                "rule": "RT3_FlaggedDeviceConnection"
            }
            fraud_result = self._create_fraud_result(fraud_score, "review", details)
            
            execution_time = (time.time() - start_time) * 1000
            performance_monitor.record_rt3_performance(execution_time, success=True)

            return True, reason, fraud_result
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            performance_monitor.record_rt3_performance(execution_time, success=False)
            
            logger.error(f"RT3: Error checking transaction {txn_id}: {e}")
            return False, f"RT3 check failed: {str(e)}", None