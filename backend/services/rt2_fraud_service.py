"""
RT2 Fraud Detection Service - Flagged Device Detection

This service implements real-time fraud detection based on flagged devices:
- Checks if sender or receiver has accounts connected to flagged devices
- Creates fraud check results for suspicious transactions
- Integrates with transaction generation pipeline
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

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
        try:
            if not self.enabled or not self.graph_service.client:
                return {"is_fraud": False, "reason": "RT2 disabled or no graph client"}
            
            logger.info(f"🔍 RT2: Checking transaction {transaction.get('id', 'unknown')} for flagged device connections in transaction network")
            
            sender_account_id = transaction.get('account_id')
            receiver_account_id = transaction.get('receiver_account_id')
            
            if not sender_account_id or not receiver_account_id:
                logger.warning(f"⚠️ RT2: Missing account IDs - sender: {sender_account_id}, receiver: {receiver_account_id}")
                return {"is_fraud": False, "reason": "Missing account information"}
            
            # Get all accounts connected to sender and receiver through transaction history
            connected_accounts = await self._get_connected_accounts([sender_account_id, receiver_account_id])
            logger.info(f"🔍 RT2: Found {len(connected_accounts)} connected accounts in transaction network")
            
            # Check all connected accounts for flagged device connections
            flagged_devices = await self._check_accounts_for_flagged_devices(connected_accounts)
            
            if flagged_devices:
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
                
                logger.warning(f"🚨 RT2 FRAUD DETECTED: Transaction {transaction.get('id')} involves flagged devices in transaction network: {flagged_devices}")
                
                # Create fraud check result in graph
                await self.create_fraud_check_result(transaction, fraud_result)
                
                return fraud_result
            else:
                logger.info(f"✅ RT2: Transaction {transaction.get('id')} passed flagged device check in transaction network")
                return {"is_fraud": False, "reason": "No flagged devices connected to transaction network"}
                
        except Exception as e:
            logger.error(f"❌ RT2: Error checking transaction {transaction.get('id', 'unknown')}: {e}")
            return {"is_fraud": False, "reason": f"RT2 check failed: {str(e)}"}
    
    async def _get_connected_accounts(self, primary_account_ids: List[str]) -> List[str]:
        """
        Get all accounts that have had transactions with the primary accounts
        
        Args:
            primary_account_ids: List of primary account IDs to find connections for
            
        Returns:
            List of all connected account IDs (including the primary ones)
        """
        try:
            connected_accounts = set(primary_account_ids)  # Start with primary accounts
            loop = asyncio.get_event_loop()
            
            for account_id in primary_account_ids:
                def find_connected_accounts():
                    try:
                        # Find the account vertex
                        account_vertices = self.graph_service.client.V().has_label("account").has("account_id", account_id).to_list()
                        if not account_vertices:
                            logger.warning(f"⚠️ RT2: Account {account_id} not found in graph")
                            return []
                        
                        account_vertex = account_vertices[0]
                        connected_account_ids = []
                        
                        # Find accounts that received money FROM this account
                        # account --TRANSFERS_TO--> transaction --TRANSFERS_FROM--> connected_account
                        outgoing_connected_accounts = (self.graph_service.client.V(account_vertex)
                                                     .out("TRANSFERS_TO")
                                                     .out("TRANSFERS_FROM")
                                                     .has_label("account")
                                                     .valueMap("account_id")
                                                     .to_list())
                        
                        for acc_props in outgoing_connected_accounts:
                            acc_id = acc_props.get('account_id', ['Unknown'])
                            if isinstance(acc_id, list) and acc_id:
                                connected_account_ids.append(acc_id[0])
                        
                        # Find accounts that sent money TO this account
                        # connected_account --TRANSFERS_TO--> transaction --TRANSFERS_FROM--> account
                        incoming_connected_accounts = (self.graph_service.client.V(account_vertex)
                                                     .in_("TRANSFERS_FROM")
                                                     .in_("TRANSFERS_TO")
                                                     .has_label("account")
                                                     .valueMap("account_id")
                                                     .to_list())
                        
                        for acc_props in incoming_connected_accounts:
                            acc_id = acc_props.get('account_id', ['Unknown'])
                            if isinstance(acc_id, list) and acc_id:
                                connected_account_ids.append(acc_id[0])
                        
                        logger.info(f"🔍 RT2: Account {account_id} has {len(connected_account_ids)} connected accounts")
                        return connected_account_ids
                        
                    except Exception as e:
                        logger.error(f"❌ RT2: Error finding connected accounts for {account_id}: {e}")
                        return []
                
                account_connections = await loop.run_in_executor(None, find_connected_accounts)
                connected_accounts.update(account_connections)
            
            result = list(connected_accounts)
            logger.info(f"🔍 RT2: Total connected accounts in transaction network: {len(result)}")
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
            flagged_devices = []
            loop = asyncio.get_event_loop()
            
            for account_id in account_ids:
                def check_account_devices():
                    try:
                        # Find the account vertex
                        account_vertices = self.graph_service.client.V().has_label("account").has("account_id", account_id).to_list()
                        if not account_vertices:
                            logger.warning(f"⚠️ RT2: Account {account_id} not found in graph")
                            return []
                        
                        account_vertex = account_vertices[0]
                        
                        # Get the user who owns this account
                        user_vertices = self.graph_service.client.V(account_vertex).in_("OWNS").to_list()
                        if not user_vertices:
                            logger.warning(f"⚠️ RT2: No user found for account {account_id}")
                            return []
                        
                        user_vertex = user_vertices[0]
                        
                        # Get all devices used by this user
                        device_vertices = self.graph_service.client.V(user_vertex).out("USES_DEVICE").to_list()
                        
                        account_flagged_devices = []
                        for device_vertex in device_vertices:
                            # Get device properties
                            device_props = self.graph_service.client.V(device_vertex).value_map().next()
                            
                            # Check if device is flagged
                            fraud_flag = device_props.get('fraud_flag', [False])
                            if isinstance(fraud_flag, list):
                                fraud_flag = fraud_flag[0] if fraud_flag else False
                            
                            if fraud_flag:
                                device_id = device_props.get('device_id', ['Unknown'])
                                if isinstance(device_id, list):
                                    device_id = device_id[0] if device_id else 'Unknown'
                                account_flagged_devices.append(device_id)
                                logger.info(f"🔍 RT2: Found flagged device {device_id} connected to account {account_id}")
                        
                        return account_flagged_devices
                        
                    except Exception as e:
                        logger.error(f"❌ RT2: Error checking devices for account {account_id}: {e}")
                        return []
                
                account_flagged_devices = await loop.run_in_executor(None, check_account_devices)
                flagged_devices.extend(account_flagged_devices)
            
            # Remove duplicates
            return list(set(flagged_devices))
            
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