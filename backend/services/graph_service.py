import asyncio
from typing import List, Dict, Any, Optional
import random
from datetime import datetime, timedelta
import uuid
import logging
import json
import os

from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.process.traversal import P

from models.schemas import (
    User, Account, Device, Transaction, UserSummary, TransactionDetail,
    DashboardStats, SearchResult, FraudRiskLevel, TransactionStatus
)
from typing import List, Dict, Any

# Get logger for graph service
logger = logging.getLogger('fraud_detection.graph')

class GraphService:
    def __init__(self, host: str = "localhost", port: int = 8182):
        self.host = host
        self.port = port
        self.client = None
        self.connection = None
        self.users_data = []
        
    def connect_sync(self):
        """Synchronous connection to Aerospike Graph (to be called outside async context)"""
        try:
            url = f'ws://{self.host}:{self.port}/gremlin'
            logger.info(f"🔄 Connecting to Aerospike Graph: {url}")
            
            # Use the same approach as the working sample
            self.connection = DriverRemoteConnection(url, "g")
            self.client = traversal().with_remote(self.connection)
            
            # Test connection using the same method as the sample
            test_result = self.client.inject(0).next()
            if test_result != 0:
                raise Exception("Failed to connect to graph instance")
            
            logger.info("✅ Connected to Aerospike Graph Service")
            return True
                
        except Exception as e:
            logger.error(f"❌ Could not connect to Aerospike Graph: {e}")
            logger.error("   Graph database connection is required. Please ensure Aerospike Graph is running on port 8182")
            self.client = None
            self.connection = None
            raise Exception(f"Failed to connect to Aerospike Graph: {e}")

    async def connect(self):
        """Async wrapper for synchronous connection"""
        import asyncio
        loop = asyncio.get_event_loop()
        
        # Run the synchronous connection in a thread pool
        success = await loop.run_in_executor(None, self.connect_sync)
        return success

    def close_sync(self):
        """Synchronous close of graph connection"""
        if self.connection:
            try:
                self.connection.close()
                logger.info("✅ Disconnected from Aerospike Graph")
            except Exception as e:
                logger.warning(f"⚠️  Error closing connection: {e}")

    async def close(self):
        """Async wrapper for synchronous close"""
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.close_sync)

    async def _execute_query(self, query: str) -> List[Any]:
        """Execute a Gremlin query using the traversal API"""
        if not self.client:
            logger.debug("Graph client not available, returning empty results")
            return []
        
        try:
            logger.debug(f"Executing Gremlin query: {query}")
            # For now, we'll use the traversal API directly in the specific methods
            # This method is kept for compatibility but the real queries will be in the specific methods
            return []
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []



    async def bulk_load_csv_data(self, vertices_path: str = None, edges_path: str = None) -> Dict[str, Any]:
        """Bulk load data from CSV files using Aerospike Graph bulk loader"""
        try:
            if not self.client:
                raise Exception("Graph client not available. Cannot bulk load data without graph database connection.")
            
            # Default paths if not provided
            if not vertices_path:
                vertices_path = "/data/graph_csv/vertices"
            if not edges_path:
                edges_path = "/data/graph_csv/edges"
            
            logger.info(f"Starting bulk load with vertices path: {vertices_path}, edges path: {edges_path}")
            
            # Run bulk load operation in a thread pool since it's blocking
            loop = asyncio.get_event_loop()
            
            def run_bulk_load():
                try:
                    # Clear existing data first
                    logger.info("Clearing existing data before bulk load...")
                    self.client.V().drop().iterate()
                    logger.info("Existing data cleared successfully")
                    
                    # Execute bulk load using Aerospike Graph loader
                    logger.info("Starting bulk load operation...")
                    result = (self.client
                             .with_("evaluationTimeout", 2000000)
                             .call("aerospike.graphloader.admin.bulk-load.load")
                             .with_("aerospike.graphloader.vertices", vertices_path)
                             .with_("aerospike.graphloader.edges", edges_path)
                             .next())
                    
                    logger.info("Bulk load operation completed successfully")
                    return {"success": True, "result": result}
                except Exception as e:
                    logger.error(f"Bulk load failed: {e}")
                    return {"success": False, "error": str(e)}
            
            bulk_load_result = await loop.run_in_executor(None, run_bulk_load)
            
            if bulk_load_result["success"]:
                logger.info("Bulk load completed successfully")
                
                # Get statistics about loaded data
                stats = await self._get_bulk_load_statistics()
                
                return {
                    "success": True,
                    "message": "Data bulk loaded successfully from CSV files",
                    "vertices_path": vertices_path,
                    "edges_path": edges_path,
                    "statistics": stats,
                    "bulk_load_result": bulk_load_result["result"]
                }
            else:
                return {
                    "success": False,
                    "error": bulk_load_result["error"],
                    "vertices_path": vertices_path,
                    "edges_path": edges_path
                }
                
        except Exception as e:
            logger.error(f"Error during bulk load: {e}")
            return {
                "success": False,
                "error": str(e),
                "vertices_path": vertices_path if vertices_path else "default",
                "edges_path": edges_path if edges_path else "default"
            }

    async def _get_bulk_load_statistics(self) -> Dict[str, Any]:
        """Get statistics about the loaded data after bulk load using Aerospike Graph Summary API"""
        try:
            loop = asyncio.get_event_loop()
            
            def get_summary():
                try:
                    # Use Aerospike Graph Summary API for efficient statistics
                    logger.info("Retrieving graph summary using Aerospike Graph Summary API...")
                    summary_result = self.client.call("aerospike.graph.admin.metadata.summary").next()
                    
                    # Parse the summary result which comes as a formatted string
                    summary_lines = str(summary_result).split('\n')
                    
                    # Initialize statistics
                    stats = {
                        "total_vertices": 0,
                        "total_edges": 0,
                        "users": 0,
                        "accounts": 0,
                        "devices": 0,
                        "owns_edges": 0,
                        "uses_edges": 0,
                        "vertex_counts_by_label": {},
                        "edge_counts_by_label": {},
                        "vertex_properties_by_label": {},
                        "edge_properties_by_label": {},
                        "supernode_count": 0,
                        "supernode_counts_by_label": {}
                    }
                    
                    # Parse summary output
                    for line in summary_lines:
                        line = line.strip()
                        if "Total vertex count=" in line:
                            stats["total_vertices"] = int(line.split("=")[1])
                        elif "Vertex count by label=" in line:
                            # Parse vertex counts: {user=1000, account=2500, device=1800}
                            label_counts = line.split("=", 1)[1].strip("{}")
                            for item in label_counts.split(", "):
                                if "=" in item:
                                    label, count = item.split("=")
                                    count_val = int(count)
                                    stats["vertex_counts_by_label"][label] = count_val
                                    
                                    # Map to our expected format
                                    if label == "user":
                                        stats["users"] = count_val
                                    elif label == "account":
                                        stats["accounts"] = count_val
                                    elif label == "device":
                                        stats["devices"] = count_val
                        elif "Total edge count=" in line:
                            stats["total_edges"] = int(line.split("=")[1])
                        elif "Edge count by label=" in line:
                            # Parse edge counts: {OWNS=2500, USES=3200}
                            label_counts = line.split("=", 1)[1].strip("{}")
                            for item in label_counts.split(", "):
                                if "=" in item:
                                    label, count = item.split("=")
                                    count_val = int(count)
                                    stats["edge_counts_by_label"][label] = count_val
                                    
                                    # Map to our expected format
                                    if label == "OWNS":
                                        stats["owns_edges"] = count_val
                                    elif label == "USES":
                                        stats["uses_edges"] = count_val
                        elif "Vertex properties by label=" in line:
                            # Parse vertex properties
                            props_str = line.split("=", 1)[1]
                            # This is more complex parsing, store as string for now
                            stats["vertex_properties_summary"] = props_str
                        elif "Edge properties by label=" in line:
                            # Parse edge properties
                            props_str = line.split("=", 1)[1]
                            stats["edge_properties_summary"] = props_str
                        elif "Total supernode count=" in line:
                            stats["supernode_count"] = int(line.split("=")[1])
                        elif "Supernode count by label=" in line:
                            # Parse supernode counts
                            label_counts = line.split("=", 1)[1].strip("{}")
                            if label_counts:
                                for item in label_counts.split(", "):
                                    if "=" in item:
                                        label, count = item.split("=")
                                        stats["supernode_counts_by_label"][label] = int(count)
                    
                    logger.info(f"Graph summary retrieved: {stats['total_vertices']} vertices, {stats['total_edges']} edges")
                    return stats
                    
                except Exception as e:
                    logger.error(f"Error getting graph summary: {e}")
                    return {
                        "total_vertices": 0,
                        "total_edges": 0,
                        "users": 0,
                        "accounts": 0,
                        "devices": 0,
                        "owns_edges": 0,
                        "uses_edges": 0,
                        "error": str(e)
                    }
            
            return await loop.run_in_executor(None, get_summary)
            
        except Exception as e:
            logger.error(f"Error getting bulk load statistics: {e}")
            return {
                "total_vertices": 0,
                "total_edges": 0,
                "users": 0,
                "accounts": 0,
                "devices": 0,
                "owns_edges": 0,
                "uses_edges": 0,
                "error": str(e)
            }

    async def get_bulk_load_status(self) -> Dict[str, Any]:
        """Get the status of the current bulk load operation using Aerospike Graph Status API"""
        try:
            if not self.client:
                raise Exception("Graph client not available. Cannot check bulk load status without graph database connection.")
            
            logger.info("Checking bulk load status using Aerospike Graph Status API...")
            
            # Run status check in a thread pool since it's blocking
            loop = asyncio.get_event_loop()
            
            def check_status():
                try:
                    # Use Aerospike Graph Status API to check bulk load progress
                    status_result = self.client.call("aerospike.graphloader.admin.bulk-load.status").next()
                    
                    # Parse the status result
                    status_info = {
                        "step": status_result.get("step", "unknown"),
                        "complete": status_result.get("complete", False),
                        "status": status_result.get("status", "unknown"),
                        "elements_written": status_result.get("elements-written"),
                        "complete_partitions_percentage": status_result.get("complete-partitions-percentage"),
                        "duplicate_vertex_ids": status_result.get("duplicate-vertex-ids"),
                        "bad_entries": status_result.get("bad-entries"),
                        "bad_edges": status_result.get("bad-edges"),
                        "message": status_result.get("message"),
                        "stacktrace": status_result.get("stacktrace")
                    }
                    
                    # Clean up None values
                    status_info = {k: v for k, v in status_info.items() if v is not None}
                    
                    logger.info(f"Bulk load status: {status_info['status']} - {status_info['step']}")
                    
                    return {
                        "success": True,
                        "status_info": status_info
                    }
                    
                except Exception as e:
                    logger.error(f"Error checking bulk load status: {e}")
                    return {
                        "success": False,
                        "error": str(e)
                    }
            
            status_result = await loop.run_in_executor(None, check_status)
            
            if status_result["success"]:
                return {
                    "success": True,
                    "message": "Bulk load status retrieved successfully",
                    "status": status_result["status_info"]
                }
            else:
                return {
                    "success": False,
                    "error": status_result["error"],
                    "message": "Failed to retrieve bulk load status"
                }
                
        except Exception as e:
            logger.error(f"Error getting bulk load status: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Error occurred while checking bulk load status"
            }



    async def get_user_summary(self, user_id: str) -> Optional[UserSummary]:
        """Get user's profile, connected accounts, and transaction summary"""
        try:
            if self.client:
                logger.info(f"Getting user summary for user {user_id}")
                # Query real graph - use synchronous calls like get_users_paginated
                user_vertex = self.client.V(user_id).has_label("user").to_list()
                
                user_props = {}
                
                # Get user properties using the same approach as get_users_paginated
                props = self.client.V(user_vertex).value_map().next()
                for key, value in props.items():
                    if isinstance(value, list) and len(value) > 0:
                        user_props[key] = value[0]
                    else:
                        user_props[key] = value
                
                # Get user's accounts
                account_vertices = self.client.V(user_vertex).out("OWNS").to_list()
                accounts = []
                for acc_vertex in account_vertices:
                    acc_props = {}
                    acc_prop_map = self.client.V(acc_vertex).value_map().next()
                    for key, value in acc_prop_map.items():
                        if isinstance(value, list) and len(value) > 0:
                            acc_props[key] = value[0]
                        else:
                            acc_props[key] = value
                    
                    accounts.append(Account(
                        id=acc_props.get('account_id', ''),
                        user_id=user_id,
                        account_type=acc_props.get('type', 'checking'),
                        balance=acc_props.get('balance', 0.0),
                        created_date=acc_props.get('created_date', ''),
                        fraud_flag=acc_props.get('fraud_flag', False)
                    ))

                # Get user's devices
                device_vertices = self.client.V(user_vertex).out("USES").to_list()
                devices = []
                for device_vertex in device_vertices:
                    device_props = {}
                    device_prop_map = self.client.V(device_vertex).value_map().next()
                    for key, value in device_prop_map.items():
                        if isinstance(value, list) and len(value) > 0:
                            device_props[key] = value[0]
                        else:
                            device_props[key] = value
                    
                    devices.append(Device(
                        id=device_props.get('device_id', ''),
                        type=device_props.get('type', ''),
                        os=device_props.get('os', ''),
                        browser=device_props.get('browser', ''),
                        fingerprint=device_props.get('fingerprint', ''),
                        first_seen=device_props.get('first_seen', ''),
                        last_login=device_props.get('last_login', ''),
                        login_count=device_props.get('login_count', 0),
                        fraud_flag=device_props.get('fraud_flag', False)
                    ))
                
                # Get transaction summary - find transactions where user's accounts are sender or receiver
                # Find transactions where user's accounts are senders (TRANSFERS_TO edges)
                logger.info(f"Looking for transactions for user {user_id}")
                
                try:
                    sender_transaction_vertices = self.client.V(user_vertex).out("OWNS").out("TRANSFERS_TO").to_list()
                    logger.info(f"Found {len(sender_transaction_vertices)} sent transactions")
                    
                    # Find transactions where user's accounts are receivers (incoming TRANSFERS_FROM edges)
                    receiver_transaction_vertices = self.client.V(user_vertex).out("OWNS").in_("TRANSFERS_FROM").to_list()
                    logger.info(f"Found {len(receiver_transaction_vertices)} received transactions")
                    
                    # Combine and deduplicate transaction vertices
                    all_transaction_vertices = list(set(sender_transaction_vertices + receiver_transaction_vertices))
                    total_transactions = len(all_transaction_vertices)
                    logger.info(f"Total unique transactions: {total_transactions}")
                    
                except Exception as e:
                    logger.error(f"Error querying transactions: {e}")
                    all_transaction_vertices = []
                    total_transactions = 0
                
                # Build recent transactions list with full transaction details
                recent_transactions = []
                total_amount_sent = 0.0
                total_amount_received = 0.0
                
                for trans_vertex in all_transaction_vertices[-10:]:  # Get last 10 transactions
                    try:
                        # Get transaction properties
                        trans_props = {}
                        trans_prop_map = self.client.V(trans_vertex).value_map().next()
                        for key, value in trans_prop_map.items():
                            if isinstance(value, list) and len(value) > 0:
                                trans_props[key] = value[0]
                            else:
                                trans_props[key] = value
                        
                        # Determine if this is a sent or received transaction for this user
                        # Check if any of user's accounts are connected via TRANSFERS_TO (sent)
                        user_accounts_sent = self.client.V(user_vertex).out("OWNS").out("TRANSFERS_TO").has("transaction_id", trans_props.get('transaction_id', '')).to_list()
                        is_sent = len(user_accounts_sent) > 0
                        
                        # Get sender and receiver information with user details
                        sender_account_vertices = self.client.V(trans_vertex).in_("TRANSFERS_TO").to_list()
                        receiver_account_vertices = self.client.V(trans_vertex).out("TRANSFERS_FROM").to_list()
                        
                        sender_info = {"account_id": "Unknown", "user_name": "Unknown"}
                        receiver_info = {"account_id": "Unknown", "user_name": "Unknown"}
                        
                        if sender_account_vertices:
                            sender_account_props = self.client.V(sender_account_vertices[0]).value_map().next()
                            sender_account_id = sender_account_props.get('account_id', ['Unknown'])[0] if isinstance(sender_account_props.get('account_id'), list) else sender_account_props.get('account_id', 'Unknown')
                            sender_info["account_id"] = sender_account_id
                            
                            # Get sender user information
                            sender_user_vertices = self.client.V(sender_account_vertices[0]).in_("OWNS").to_list()
                            logger.info(f"Found {len(sender_user_vertices)} sender user vertices for account {sender_account_id}")
                            if sender_user_vertices:
                                sender_user_props = self.client.V(sender_user_vertices[0]).value_map().next()
                                sender_user_name = sender_user_props.get('name', ['Unknown'])[0] if isinstance(sender_user_props.get('name'), list) else sender_user_props.get('name', 'Unknown')
                                sender_info["user_name"] = sender_user_name
                                logger.info(f"Sender user name: {sender_user_name}")
                        
                        if receiver_account_vertices:
                            receiver_account_props = self.client.V(receiver_account_vertices[0]).value_map().next()
                            receiver_account_id = receiver_account_props.get('account_id', ['Unknown'])[0] if isinstance(receiver_account_props.get('account_id'), list) else receiver_account_props.get('account_id', 'Unknown')
                            receiver_info["account_id"] = receiver_account_id
                            
                            # Get receiver user information
                            receiver_user_vertices = self.client.V(receiver_account_vertices[0]).in_("OWNS").to_list()
                            logger.info(f"Found {len(receiver_user_vertices)} receiver user vertices for account {receiver_account_id}")
                            if receiver_user_vertices:
                                receiver_user_props = self.client.V(receiver_user_vertices[0]).value_map().next()
                                receiver_user_name = receiver_user_props.get('name', ['Unknown'])[0] if isinstance(receiver_user_props.get('name'), list) else receiver_user_props.get('name', 'Unknown')
                                receiver_info["user_name"] = receiver_user_name
                                logger.info(f"Receiver user name: {receiver_user_name}")
                        
                        # Check for fraud detection results
                        fraud_results = self.client.V(trans_vertex).out("flagged_by").to_list()
                        is_fraud = len(fraud_results) > 0
                        fraud_score = 0.0
                        fraud_rules = []
                        
                        for fraud_result in fraud_results:
                            fraud_props = self.client.V(fraud_result).value_map().next()
                            score = fraud_props.get('fraud_score', [0.0])
                            if isinstance(score, list) and score:
                                fraud_score = max(fraud_score, score[0])
                            rule = fraud_props.get('rule', ['Unknown'])
                            if isinstance(rule, list) and rule:
                                fraud_rules.append(rule[0])
                        
                        # Create enhanced transaction dictionary with all fields
                        transaction_amount = trans_props.get('amount', 0.0)
                        
                        # For display: negative if user sent money, positive if user received money
                        display_amount = -transaction_amount if is_sent else transaction_amount
                        
                        logger.info(f"Creating transaction with sender_name: {sender_info['user_name']}, receiver_name: {receiver_info['user_name']}, is_sent: {is_sent}, amount: {display_amount}")
                        
                        transaction_dict = {
                            "id": trans_props.get('transaction_id', ''),
                            "sender_id": sender_info["account_id"],
                            "receiver_id": receiver_info["account_id"],
                            "amount": display_amount,  # Use display amount with proper sign
                            "currency": trans_props.get('currency', 'INR'),
                            "timestamp": trans_props.get('timestamp', ''),
                            "location": trans_props.get('location', ''),
                            "status": trans_props.get('status', 'completed'),
                            "fraud_score": fraud_score,
                            # Enhanced fields for frontend
                            "sender_name": sender_info["user_name"],
                            "receiver_name": receiver_info["user_name"],
                            "is_fraud": is_fraud,
                            "fraud_rules": fraud_rules,
                            "direction": "sent" if is_sent else "received",
                            "original_amount": transaction_amount
                        }
                        
                        logger.info(f"Created transaction dict with enhanced fields: {transaction_dict}")
                        
                        # Update totals with original amount (not display amount)
                        if is_sent:
                            total_amount_sent += transaction_amount
                        else:
                            total_amount_received += transaction_amount
                        
                        recent_transactions.append(transaction_dict)
                        
                    except Exception as e:
                        logger.error(f"Error processing transaction vertex: {e}")
                        continue
                
                # Calculate fraud risk level based on risk score
                risk_score = user_props.get('risk_score', 0.0)
                if risk_score < 25:
                    fraud_risk_level = FraudRiskLevel.LOW
                elif risk_score < 50:
                    fraud_risk_level = FraudRiskLevel.MEDIUM
                elif risk_score < 75:
                    fraud_risk_level = FraudRiskLevel.HIGH
                else:
                    fraud_risk_level = FraudRiskLevel.CRITICAL
                
                # For now, we'll set connected users to empty list
                # In a real implementation, you'd find users connected via transactions
                connected_users = []
                
                return UserSummary(
                    user=User(
                        id=user_vertex.id,
                        name=user_props.get('name', ''),
                        email=user_props.get('email', ''),
                        age=user_props.get('age', 0),
                        phone_number=user_props.get('phone', ''),
                        occupation=user_props.get('occupation', ''),
                        location=user_props.get('location', ''),
                        risk_score=user_props.get('risk_score', 0.0),
                        signup_date=user_props.get('signup_date', '')
                    ),
                    accounts=accounts,
                    devices=devices,
                    recent_transactions=recent_transactions,  # This is now a list of dicts with custom fields
                    total_transactions=total_transactions,
                    total_amount_sent=total_amount_sent,
                    total_amount_received=total_amount_received,
                    fraud_risk_level=fraud_risk_level,
                    connected_users=connected_users
                )
            else:
                # Mock mode - return data from loaded users
                user_data = next((u for u in self.users_data if u['id'] == user_id), None)
                if not user_data:
                    return None
                
                accounts = []
                for acc_data in user_data.get('accounts', []):
                    accounts.append(Account(
                        id=acc_data['id'],
                        user_id=user_id,
                        account_type=acc_data['type'],
                        balance=acc_data['balance'],
                        created_date=acc_data['created_date']
                    ))
                
                devices = []
                for device_data in user_data.get('devices', []):
                    devices.append(Device(
                        id=device_data['id'],
                        type=device_data['type'],
                        os=device_data['os'],
                        browser=device_data['browser'],
                        fingerprint=device_data['fingerprint'],
                        first_seen=device_data['first_seen'],
                        last_login=device_data['last_login'],
                        login_count=device_data['login_count']
                    ))
                
                # Calculate fraud risk level based on risk score
                risk_score = user_data.get('risk_score', 0.0)
                if risk_score < 25:
                    fraud_risk_level = FraudRiskLevel.LOW
                elif risk_score < 50:
                    fraud_risk_level = FraudRiskLevel.MEDIUM
                elif risk_score < 75:
                    fraud_risk_level = FraudRiskLevel.HIGH
                else:
                    fraud_risk_level = FraudRiskLevel.CRITICAL
                
                return UserSummary(
                    user=User(
                        id=user_data['id'],
                        name=user_data['name'],
                        email=user_data['email'],
                        age=user_data['age'],
                        location=user_data['location'],
                        risk_score=user_data.get('risk_score', 0.0),
                        signup_date=user_data['signup_date']
                    ),
                    accounts=accounts,
                    devices=devices,
                    recent_transactions=[],  # No transactions in mock mode
                    total_transactions=0,
                    total_amount_sent=0.0,
                    total_amount_received=0.0,
                    fraud_risk_level=fraud_risk_level,
                    connected_users=[]
                )
                
        except Exception as e:
            logger.error(f"Error getting user summary: {e}")
            return None

    async def get_transaction_detail(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed transaction information"""
        try:
            if self.client:
                # Query real graph - look for transaction vertex
                loop = asyncio.get_event_loop()
                
                logger.info(f"Looking for transaction with ID: {transaction_id}")
                
                def get_transaction_vertex():
                    return self.client.V().has_label("transaction").has("transaction_id", transaction_id).to_list()
                
                transaction_vertices = await loop.run_in_executor(None, get_transaction_vertex)
                logger.info(f"Found {len(transaction_vertices)} transaction vertices")
                
                if not transaction_vertices:
                    return None
                
                transaction_vertex = transaction_vertices[0]
                
                def get_transaction_props():
                    try:
                        logger.info(f"Getting properties for transaction vertex: {transaction_vertex}")
                        props = self.client.V(transaction_vertex).value_map().next()
                        logger.info(f"Successfully got transaction properties: {props}")
                        return props
                    except Exception as e:
                        logger.error(f"Error getting transaction properties: {e}")
                        raise e
                
                transaction_props = await loop.run_in_executor(None, get_transaction_props)
                
                # Get source and destination accounts from TRANSFERS_TO and TRANSFERS_FROM edges
                def get_source_account():
                    return self.client.V(transaction_vertex).in_("TRANSFERS_TO").to_list()
                
                def get_dest_account():
                    return self.client.V(transaction_vertex).out("TRANSFERS_FROM").to_list()
                
                source_accounts = await loop.run_in_executor(None, get_source_account)
                dest_accounts = await loop.run_in_executor(None, get_dest_account)
                
                source_account = source_accounts[0] if source_accounts else None
                dest_account = dest_accounts[0] if dest_accounts else None
                
                logger.info(f"Found source accounts: {len(source_accounts)}, dest accounts: {len(dest_accounts)}")
                
               
                
                # Only proceed if we have both accounts AND their users
                if source_account and dest_account:
                    def get_source_props():
                        return self.client.V(source_account).value_map().next()
                    
                    def get_dest_props():
                        return self.client.V(dest_account).value_map().next()
                    
                    source_props = await loop.run_in_executor(None, get_source_props)
                    dest_props = await loop.run_in_executor(None, get_dest_props)
                    
                    # Get user information for source account
                    def get_source_user():
                        return self.client.V(source_account).in_("OWNS").to_list()
                    
                    source_users = await loop.run_in_executor(None, get_source_user)
                    source_user = source_users[0] if source_users else None
                    
                    # Get user information for destination account
                    def get_dest_user():
                        return self.client.V(dest_account).in_("OWNS").to_list()
                    
                    dest_users = await loop.run_in_executor(None, get_dest_user)
                    dest_user = dest_users[0] if dest_users else None
                    
                    # Get user properties
                    source_user_props = {}
                    dest_user_props = {}
                    
                    if source_user:
                        def get_source_user_props():
                            return self.client.V(source_user).value_map().next()
                        source_user_props = await loop.run_in_executor(None, get_source_user_props)
                    
                    if dest_user:
                        def get_dest_user_props():
                            return self.client.V(dest_user).value_map().next()
                        dest_user_props = await loop.run_in_executor(None, get_dest_user_props)
                    
                    # Only return data if we have BOTH users - no mock data
                    if not source_user or not dest_user:
                        logger.warning(f"Transaction {transaction_id} missing source user ({bool(source_user)}) or dest user ({bool(dest_user)}) - returning None")
                        return None
                    
                    # Build transaction data - ONLY from database properties
                    transaction_data = {
                        "id": transaction_props.get('transaction_id', [''])[0],
                        "amount": transaction_props.get('amount', [0.0])[0],
                        "currency": transaction_props.get('currency', [''])[0],
                        "timestamp": transaction_props.get('timestamp', [''])[0],
                        "status": transaction_props.get('status', [''])[0],
                        "transaction_type": transaction_props.get('type', [''])[0],
                        "location_city": transaction_props.get('location', [''])[0]
                    }
                    
                    # Build account data - ONLY from database properties
                    source_account_data = {
                        "id": source_props.get('account_id', [''])[0],
                        "account_type": source_props.get('type', [''])[0],
                        "balance": source_props.get('balance', [0.0])[0],
                        "created_date": source_props.get('created_date', [''])[0],
                        "user_id": source_user.id,
                        "user_name": source_user_props.get('name', [''])[0],
                        "user_email": source_user_props.get('email', [''])[0]
                    }
                    
                    destination_account_data = {
                        "id": dest_props.get('account_id', [''])[0],
                        "account_type": dest_props.get('type', [''])[0],
                        "balance": dest_props.get('balance', [0.0])[0],
                        "created_date": dest_props.get('created_date', [''])[0],
                        "user_id": dest_user.id,
                        "user_name": dest_user_props.get('name', [''])[0],
                        "user_email": dest_user_props.get('email', [''])[0]
                    }
                  
                    # Get fraud results - look for flagged_by edges to fraud check results
                    def get_fraud_results():
                        try:
                            logger.info(f"Looking for fraud results for transaction vertex: {transaction_vertex}")
                            fraud_result_vertices = self.client.V(transaction_vertex).out("flagged_by").to_list()
                            logger.info(f"Found {len(fraud_result_vertices)} fraud result vertices")
                            fraud_results = []
                            
                            for fraud_vertex in fraud_result_vertices:
                                logger.info(f"Processing fraud vertex: {fraud_vertex}")
                                fraud_props = self.client.V(fraud_vertex).value_map().next()
                                logger.info(f"Fraud vertex properties: {fraud_props}")
                                
                                # Extract properties
                                fraud_result = {}
                                for key, value in fraud_props.items():
                                    if isinstance(value, list) and len(value) > 0:
                                        fraud_result[key] = value[0]
                                    else:
                                        fraud_result[key] = value
                                
                                fraud_results.append(fraud_result)
                            
                            logger.info(f"Found {len(fraud_results)} fraud results for transaction {transaction_id}")
                            return fraud_results
                        
                        except Exception as e:
                            logger.error(f"Error getting fraud results for transaction {transaction_id}: {e}")
                            return []
                    
                    fraud_results = await loop.run_in_executor(None, get_fraud_results)
                    
                    return {
                        "transaction": transaction_data,
                        "source_account": source_account_data,
                        "destination_account": destination_account_data,
                        "fraud_results": fraud_results
                    }
                else:
                    # No mock data - return None if we don't have complete real data
                    logger.warning(f"Transaction {transaction_id} found but missing source/destination accounts or users - returning None")
                    return None
            else:
                # Mock mode - no transactions available
                return None
                
        except Exception as e:
            logger.error(f"Error getting transaction detail: {e}")
            return None

    async def get_all_accounts(self) -> List[Dict[str, Any]]:
        """Get all accounts with their associated user information"""
        try:
            if self.client:
                loop = asyncio.get_event_loop()
                
                def get_accounts():
                    return self.client.V().has_label("account").to_list()
                
                account_vertices = await loop.run_in_executor(None, get_accounts)
                accounts = []
                
                for account_vertex in account_vertices:
                    try:
                        # Get account properties
                        def get_account_props():
                            return self.client.V(account_vertex).value_map().next()
                        
                        account_props = await loop.run_in_executor(None, get_account_props)
                        
                        # Get associated user
                        def get_user():
                            return self.client.V(account_vertex).in_("OWNS").to_list()
                        
                        users = await loop.run_in_executor(None, get_user)
                        user_name = "Unknown"
                        
                        if users:
                            def get_user_props():
                                return self.client.V(users[0]).value_map().next()
                            
                            user_props = await loop.run_in_executor(None, get_user_props)
                            user_name = user_props.get('name', ['Unknown'])[0]
                        
                        accounts.append({
                            "account_id": account_props.get('account_id', [''])[0],
                            "account_type": account_props.get('type', [''])[0],
                            "balance": account_props.get('balance', [0.0])[0],
                            "user_name": user_name
                        })
                        
                    except Exception as e:
                        logger.error(f"Error processing account: {e}")
                        continue
                
                return accounts
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error getting all accounts: {e}")
            return []

    def get_dashboard_stats_sync(self) -> DashboardStats:
        """Get dashboard statistics synchronously"""
        try:
            if self.client:
                # Query real graph
                total_users = len(self.client.V().has_label("user").to_list())
                total_transactions = len(self.client.V().has_label("transaction").to_list())
                
                # Get flagged transactions (high risk transactions)
                flagged_transactions = len(self.client.V().has_label("transaction").has("amount", P.gte(10000)).to_list())
                
                # Calculate total amount
                transaction_vertices = self.client.V().has_label("transaction").to_list()
                total_amount = sum(vertex.value_map().next().get('amount', [0.0])[0] for vertex in transaction_vertices)
                
                fraud_rate = (flagged_transactions / total_transactions * 100) if total_transactions > 0 else 0
                
                return DashboardStats(
                    total_users=total_users,
                    total_transactions=total_transactions,
                    flagged_transactions=flagged_transactions,
                    total_amount=total_amount,
                    fraud_detection_rate=fraud_rate,
                    graph_health="connected"
                )
            else:
                # No graph client available
                raise Exception("Graph client not available. Cannot get dashboard stats without graph database connection.")
                
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return DashboardStats(
                total_users=0,
                total_transactions=0,
                flagged_transactions=0,
                total_amount=0.0,
                fraud_detection_rate=0.0,
                graph_health="error"
            )

    async def get_dashboard_stats(self) -> DashboardStats:
        """Get dashboard statistics asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_dashboard_stats_sync)

    async def get_users_paginated(self, page: int, page_size: int) -> Dict[str, Any]:
        """Get paginated list of all users"""
        try:
            if self.client:
                # Get event loop for async operations
                import asyncio
                loop = asyncio.get_event_loop()
                
                # Query real graph using run_in_executor to avoid event loop conflict
                def get_all_users():
                    return self.client.V().has_label("user").to_list()
                
                all_users = await loop.run_in_executor(None, get_all_users)
                
                # Paginate
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paginated_users = all_users[start_idx:end_idx]
                
                users_data = []
                for user_vertex in paginated_users:
                    # Get user properties using run_in_executor
                    user_props = {}
                    try:
                        def get_user_props():
                            props = self.client.V(user_vertex).value_map().next()
                            result = {}
                            for key, value in props.items():
                                if isinstance(value, list) and len(value) > 0:
                                    result[key] = value[0]
                                else:
                                    result[key] = value
                            return result
                        
                        user_props = await loop.run_in_executor(None, get_user_props)
                        
                    except Exception as e:
                        logger.error(f"Error getting user properties: {e}")
                        continue
                    
                    # Get user's accounts using run_in_executor
                    accounts = []
                    try:
                        def get_user_accounts():
                            account_vertices = self.client.V(user_vertex).out("OWNS").to_list()
                            acc_list = []
                            for acc_vertex in account_vertices:
                                try:
                                    acc_prop_map = self.client.V(acc_vertex).value_map().next()
                                    acc_props = {}
                                    for key, value in acc_prop_map.items():
                                        if isinstance(value, list) and len(value) > 0:
                                            acc_props[key] = value[0]
                                        else:
                                            acc_props[key] = value
                                    acc_list.append(acc_props)
                                except Exception as e:
                                    logger.error(f"Error getting account properties: {e}")
                            return acc_list
                        
                        accounts = await loop.run_in_executor(None, get_user_accounts)
                    except Exception as e:
                        logger.error(f"Error getting user accounts: {e}")
                    
                    users_data.append({
                        'id': user_vertex.id,
                        'name': user_props.get('name', ''),
                        'email': user_props.get('email', ''),
                        'age': user_props.get('age', 0),
                        'location': user_props.get('location', ''),
                        'occupation':user_props.get('occupation', ''),
                        'phone_number':user_props.get('phone_number', ''),
                        'risk_score': user_props.get('risk_score', 0.0),
                        'signup_date': user_props.get('signup_date', ''),
                        'accounts': accounts
                    })
                
                return {
                    'users': users_data,
                    'total': len(all_users),
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (len(all_users) + page_size - 1) // page_size
                }
            else:
                # No graph client available
                raise Exception("Graph client not available. Cannot get users without graph database connection.")
                
        except Exception as e:
            logger.error(f"Error getting users paginated: {e}")
            return {
                'users': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0
            }

    async def search_users_paginated(self, query: str, page: int, page_size: int) -> Dict[str, Any]:
        """Search users with pagination"""
        try:
            if self.client:
                # Get event loop for async operations
                import asyncio
                loop = asyncio.get_event_loop()
                
                # Query real graph with search using run_in_executor
                def search_users():
                    logger.info(f"Searching for users with query: {query}")
                    return self.client.V().has_label("user").or_(
                        __.has("name", P.text_contains(query)),
                        __.hasId(P.text_contains(query)),
                        __.has("email", P.text_contains(query))
                    ).to_list()
                
                all_users = await loop.run_in_executor(None, search_users)
                
                # Paginate
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paginated_users = all_users[start_idx:end_idx]
                
                users_data = []
                for user_vertex in paginated_users:
                    def get_user_props():
                        return user_vertex.value_map().next()
                    
                    user_props = await loop.run_in_executor(None, get_user_props)
                        
                    users_data.append({
                        'id': user_vertex.id,
                        'name': user_props.get('name', [''])[0],
                        'email': user_props.get('email', [''])[0],
                        'age': user_props.get('age', [0])[0],
                        'location': user_props.get('location', [''])[0],
                        'risk_score': user_props.get('risk_score', [0.0])[0],
                        'signup_date': user_props.get('signup_date', [''])[0]
                    })
                
                return {
                    'users': users_data,
                    'total': len(all_users),
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (len(all_users) + page_size - 1) // page_size
                }
            else:
                # Mock mode - search in loaded users
                filtered_users = [
                    user for user in self.users_data
                    if query.lower() in user['name'].lower() or 
                       query.lower() in user['id'].lower() or 
                       query.lower() in user['email'].lower()
                ]
                
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paginated_users = filtered_users[start_idx:end_idx]
                
                return {
                    'users': paginated_users,
                    'total': len(filtered_users),
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (len(filtered_users) + page_size - 1) // page_size
                }
                
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return {
                'users': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0
            }

    async def search_users(self, query: str) -> List[SearchResult]:
        """Search users and return simplified results"""
        try:
            if self.client:
                # Query real graph
                users = self.client.V().has_label("user").or_(
                    __.has("name", P.text_contains(query)),
                    __.has("user_id", P.text_contains(query)),
                    __.has("email", P.text_contains(query))
                ).to_list()
                
                results = []
                for user_vertex in users:
                    user_props = user_vertex.value_map().next()
                    results.append(SearchResult(
                        id=user_vertex.id,
                        name=user_props.get('name', [''])[0],
                        type="user",
                        score=user_props.get('risk_score', [0.0])[0]
                    ))
                
                return results
            else:
                # Mock mode
                filtered_users = [
                    user for user in self.users_data
                    if query.lower() in user['name'].lower() or 
                       query.lower() in user['id'].lower() or 
                       query.lower() in user['email'].lower()
                ]
                
                return [
                    SearchResult(
                        id=user['id'],
                        name=user['name'],
                        type="user",
                        score=user.get('risk_score', 0.0)
                    )
                    for user in filtered_users
                ]
                
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return []

    async def search_transactions(self, query: str) -> List[SearchResult]:
        """Search transactions and return simplified results"""
        try:
            if self.client:
                # Query real graph
                transactions = self.client.V().has_label("transaction").has("transaction_id", P.text_contains(query)).to_list()
                
                results = []
                for transaction_vertex in transactions:
                    transaction_props = transaction_vertex.value_map().next()
                    results.append(SearchResult(
                        id=transaction_props.get('transaction_id', [''])[0],
                        name=f"Transaction {transaction_props.get('transaction_id', [''])[0]}",
                        type="transaction",
                        score=0.0
                    ))
                
                return results
            else:
                # Mock mode - no transactions available
                return []
                
        except Exception as e:
            logger.error(f"Error searching transactions: {e}")
            return []

    async def update_transaction_status(self, transaction_id: str, status: str) -> bool:
        """Update transaction status"""
        try:
            if self.client:
                # Update in real graph
                loop = asyncio.get_event_loop()
                
                def update_transaction():
                    vertices = self.client.V().has_label("transaction").has("transaction_id", transaction_id).to_list()
                    if vertices:
                        vertex = vertices[0]
                        vertex.property("status", status).iterate()
                        return True
                    return False
                
                return await loop.run_in_executor(None, update_transaction)
                return False
            else:
                # Mock mode - no transactions to update
                return False
                
        except Exception as e:
            logger.error(f"Error updating transaction status: {e}")
            return False

    def _calculate_risk_level(self, score: float) -> FraudRiskLevel:
        """Calculate fraud risk level based on score"""
        if score >= 80:
            return FraudRiskLevel.HIGH
        elif score >= 50:
            return FraudRiskLevel.MEDIUM
        else:
            return FraudRiskLevel.LOW

    def _convert_timestamp_to_long(self, date_str: str) -> int:
        """Convert timestamp string to long integer"""
        import datetime
        timestamp = datetime.datetime.now().timestamp()
        long_timestamp = int(timestamp)
        return long_timestamp

    async def get_transactions_paginated(self, page: int, page_size: int) -> Dict[str, Any]:
        """Get paginated list of all transactions"""
        try:
            if self.client:
                # Query real graph - use synchronous calls like get_users_paginated
                all_transactions = self.client.V().has_label("transaction").to_list()
                
                # Paginate
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paginated_transactions = all_transactions[start_idx:end_idx]
                
                transactions_data = []
                for transaction_vertex in paginated_transactions:
                    try:
                        # Get transaction properties using the same approach as get_users_paginated
                        transaction_props = {}
                        props = self.client.V(transaction_vertex).value_map().next()
                        for key, value in props.items():
                            if isinstance(value, list) and len(value) > 0:
                                transaction_props[key] = value[0]
                            else:
                                transaction_props[key] = value
                        
                        # Get the sender account that initiated this transaction
                        try:
                            logger.info(f"Looking for sender account that initiated transaction {transaction_props.get('transaction_id', 'unknown')}")
                            
                            # Try to find the sender account using the TRANSFERS_TO edge
                            sender_account_vertices = self.client.V(transaction_vertex).in_("TRANSFERS_TO").to_list()
                            logger.info(f"Found {len(sender_account_vertices)} sender account vertices")
                            
                            if sender_account_vertices:
                                sender_account_vertex = sender_account_vertices[0]
                                logger.info(f"Found sender account vertex: {sender_account_vertex}")
                                
                                sender_account_props = {}
                                sender_acc_prop_map = self.client.V(sender_account_vertex).value_map().next()
                                for key, value in sender_acc_prop_map.items():
                                    if isinstance(value, list) and len(value) > 0:
                                        sender_account_props[key] = value[0]
                                    else:
                                        sender_account_props[key] = value
                                logger.info(f"Sender account properties: {sender_account_props}")
                                sender_id = sender_account_props.get('account_id', 'Unknown')
                                logger.info(f"Sender ID: {sender_id}")
                            else:
                                logger.warning("No sender account vertices found")
                                sender_id = 'Unknown'
                        except Exception as e:
                            # If no sender account found, use a default
                            logger.error(f"Error getting sender account for transaction: {e}")
                            sender_id = 'Unknown'
                        
                        # Get the receiver account that received this transaction
                        try:
                            logger.info(f"Looking for receiver account for transaction {transaction_props.get('transaction_id', 'unknown')}")
                            
                            # Try to find the receiver account using the TRANSFERS_FROM edge
                            receiver_account_vertices = self.client.V(transaction_vertex).out("TRANSFERS_FROM").to_list()
                            logger.info(f"Found {len(receiver_account_vertices)} receiver account vertices")
                            
                            if receiver_account_vertices:
                                receiver_account_vertex = receiver_account_vertices[0]
                                logger.info(f"Found receiver account vertex: {receiver_account_vertex}")
                                
                                receiver_account_props = {}
                                receiver_acc_prop_map = self.client.V(receiver_account_vertex).value_map().next()
                                for key, value in receiver_acc_prop_map.items():
                                    if isinstance(value, list) and len(value) > 0:
                                        receiver_account_props[key] = value[0]
                                    else:
                                        receiver_account_props[key] = value
                                logger.info(f"Receiver account properties: {receiver_account_props}")
                                receiver_id = receiver_account_props.get('account_id', 'Unknown')
                                logger.info(f"Receiver ID: {receiver_id}")
                            else:
                                logger.warning("No receiver account vertices found")
                                receiver_id = 'Unknown'
                        except Exception as e:
                            # If no receiver account found, use a default
                            logger.error(f"Error getting receiver account for transaction: {e}")
                            receiver_id = 'Unknown'
                        
                        # Get fraud check results if any
                        fraud_score = 0.0
                        is_fraud = False
                        fraud_status = None
                        fraud_reason = None
                        try:
                            # Check for fraud check results connected via flagged_by edge
                            fraud_result_vertices = self.client.V(transaction_vertex).out("flagged_by").to_list()
                            if fraud_result_vertices:
                                fraud_result_vertex = fraud_result_vertices[0]  # Get the first fraud result
                                fraud_result_props = {}
                                fraud_props_map = self.client.V(fraud_result_vertex).value_map().next()
                                for key, value in fraud_props_map.items():
                                    if isinstance(value, list) and len(value) > 0:
                                        fraud_result_props[key] = value[0]
                                    else:
                                        fraud_result_props[key] = value
                                
                                fraud_score = fraud_result_props.get('fraud_score', 0.0)
                                fraud_status = fraud_result_props.get('status', 'clean')
                                fraud_reason = fraud_result_props.get('reason', '')
                                is_fraud = fraud_score >= 75  # Consider score >= 75 as fraud
                                
                                logger.info(f"Found fraud result for transaction {transaction_props.get('transaction_id', 'unknown')}: score={fraud_score}, status={fraud_status}")
                        except Exception as e:
                            logger.debug(f"No fraud results found for transaction {transaction_props.get('transaction_id', 'unknown')}: {e}")
                            # No fraud results found, use defaults
                        
                        transactions_data.append({
                            'id': transaction_props.get('transaction_id', ''),
                            'sender_id': sender_id,
                            'receiver_id': receiver_id,
                            'amount': transaction_props.get('amount', 0.0),
                            'currency': 'INR',
                            'timestamp': transaction_props.get('timestamp', ''),
                            'location': transaction_props.get('location', 'Unknown'),
                            'status': transaction_props.get('status', 'completed'),
                            'fraud_score': fraud_score,
                            'transaction_type': transaction_props.get('type', 'transfer'),
                            'is_fraud': is_fraud,
                            'fraud_status': fraud_status,
                            'fraud_reason': fraud_reason,
                            'device_id': None
                        })
                    except Exception as e:
                        logger.error(f"Error processing transaction vertex: {e}")
                        continue
                
                return {
                    'transactions': transactions_data,
                    'total': len(all_transactions),
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (len(all_transactions) + page_size - 1) // page_size
                }
            else:
                # No graph client available
                raise Exception("Graph client not available. Cannot get transactions without graph database connection.")
                
        except Exception as e:
            logger.error(f"Error getting transactions paginated: {e}")
            return {
                'transactions': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0
            }

    async def search_transactions_paginated(self, query: str, page: int, page_size: int) -> Dict[str, Any]:
        """Search transactions with pagination"""
        try:
            if self.client:
                # Query real graph with search using thread pool
                import asyncio
                loop = asyncio.get_event_loop()
                
                def search_transactions():
                    return self.client.V().has_label("transaction").or_(
                        __.has("transaction_id", P.text_contains(query)),
                        __.has("location_city", P.text_contains(query))
                    ).to_list()
                
                all_transactions = await loop.run_in_executor(None, search_transactions)
                
                # Paginate
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paginated_transactions = all_transactions[start_idx:end_idx]
                
                transactions_data = []
                for transaction_vertex in paginated_transactions:
                    try:
                        def get_transaction_props():
                            return transaction_vertex.value_map().next()
                        
                        transaction_props = await loop.run_in_executor(None, get_transaction_props)
                        
                        # Get the account that initiated this transaction
                        def get_account_vertex():
                            return transaction_vertex.in_("INITIATED").next()
                        
                        try:
                            account_vertex = await loop.run_in_executor(None, get_account_vertex)
                            
                            def get_account_props():
                                return account_vertex.value_map().next()
                            
                            account_props = await loop.run_in_executor(None, get_account_props)
                            sender_id = account_props.get('account_id', [''])[0]
                        except:
                            # If no account found, use a default
                            sender_id = 'Unknown'
                        
                        # For now, use the same account as receiver (self-transaction)
                        receiver_id = sender_id
                        
                        transactions_data.append({
                            'id': transaction_props.get('transaction_id', [''])[0],
                            'sender_id': sender_id,
                            'receiver_id': receiver_id,
                            'amount': transaction_props.get('amount', [0.0])[0],
                            'currency': 'INR',
                            'timestamp': transaction_props.get('timestamp', [''])[0],
                            'location': transaction_props.get('location_city', ['Unknown'])[0],
                            'status': transaction_props.get('status', ['completed'])[0],
                            'fraud_score': 0.0,
                            'transaction_type': transaction_props.get('method', ['transfer'])[0],
                            'is_fraud': False,
                            'device_id': None
                        })
                    except Exception as e:
                        logger.error(f"Error processing search transaction vertex: {e}")
                        continue
                
                return {
                    'transactions': transactions_data,
                    'total': len(all_transactions),
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (len(all_transactions) + page_size - 1) // page_size
                }
            else:
                # No graph client available
                raise Exception("Graph client not available. Cannot search transactions without graph database connection.")
                
        except Exception as e:
            logger.error(f"Error searching transactions: {e}")
            return {
                'transactions': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0
            }

    async def get_user_transactions_paginated(self, user_id: str, page: int, page_size: int) -> Dict[str, Any]:
        """Get paginated transactions for a specific user"""
        try:
            if self.client:
                # Query real graph for user's transactions
                # This would need to be implemented to query the graph database
                # For now, return empty result
                return {
                    "transactions": [],
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": 0,
                    "user_id": user_id
                }
            else:
                # No graph client available
                raise Exception("Graph client not available. Cannot get user transactions without graph database connection.")
        except Exception as e:
            logger.error(f"Error in get_user_transactions_paginated: {e}")
            raise Exception(f"Failed to get user transactions: {e}")

    async def get_user_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all accounts for a specific user"""
        try:
            if self.client:
                # Query real graph for user's accounts
                # This would need to be implemented to query the graph database
                # For now, return empty result
                return []
            else:
                # No graph client available
                raise Exception("Graph client not available. Cannot get user accounts without graph database connection.")
        except Exception as e:
            logger.error(f"Error in get_user_accounts: {e}")
            raise Exception(f"Failed to get user accounts: {e}")

    async def delete_all_data(self) -> Dict[str, Any]:
        """Delete all data from the graph database"""
        try:
            if self.client:
                # Delete all vertices and edges using thread pool
                logger.info("Deleting all vertices and edges from graph database...")
                
                import asyncio
                loop = asyncio.get_event_loop()
                
                # Delete all edges first
                def delete_edges():
                    return self.client.E().drop().to_list()
                
                edges_deleted = await loop.run_in_executor(None, delete_edges)
                logger.info(f"Deleted {len(edges_deleted)} edges")
                
                # Delete all vertices
                def delete_vertices():
                    return self.client.V().drop().to_list()
                
                vertices_deleted = await loop.run_in_executor(None, delete_vertices)
                logger.info(f"Deleted {len(vertices_deleted)} vertices")
                
                return {
                    "message": "All data deleted successfully",
                    "edges_deleted": len(edges_deleted),
                    "vertices_deleted": len(vertices_deleted)
                }
            else:
                # Mock mode - clear in-memory data
                logger.info("Mock mode: Clearing in-memory data")
                self.users_data = []
                return {
                    "message": "Mock data cleared successfully",
                    "edges_deleted": 0,
                    "vertices_deleted": 0
                }
        except Exception as e:
            logger.error(f"Error deleting all data: {e}")
            return {"error": str(e)}


    async def flag_account(self, account_id: str, reason: str) -> bool:
        """Flag an account as fraudulent"""
        try:
            if not self.client:
                raise Exception("Graph client not available")
            
            loop = asyncio.get_event_loop()
            
            def flag_account_sync():
                try:
                    # Find and update account
                    accounts = self.client.V().has_label("account").has("account_id", account_id).to_list()
                    if not accounts:
                        return False
                    
                    account_vertex = accounts[0]
                    self.client.V(account_vertex).property("fraud_flag", True).property("flagReason", reason).property("flagTimestamp", datetime.now().isoformat()).iterate()
                    
                    logger.info(f"🚩 Account {account_id} flagged as fraudulent: {reason}")
                    return True
                    
                except Exception as e:
                    logger.error(f"Error flagging account {account_id}: {e}")
                    return False
            
            return await loop.run_in_executor(None, flag_account_sync)
            
        except Exception as e:
            logger.error(f"Error in flag_account: {e}")
            return False

    async def unflag_account(self, account_id: str) -> bool:
        """Remove fraud flag from an account"""
        try:
            if not self.client:
                raise Exception("Graph client not available")
            
            loop = asyncio.get_event_loop()
            
            def unflag_account_sync():
                try:
                    # Find and update account
                    accounts = self.client.V().has_label("account").has("account_id", account_id).to_list()
                    if not accounts:
                        return False
                    
                    account_vertex = accounts[0]
                    self.client.V(account_vertex).property("fraud_flag", False).property("unflagTimestamp", datetime.now().isoformat()).iterate()
                    
                    logger.info(f"✅ Account {account_id} unflagged")
                    return True
                    
                except Exception as e:
                    logger.error(f"Error unflagging account {account_id}: {e}")
                    return False
            
            return await loop.run_in_executor(None, unflag_account_sync)
            
        except Exception as e:
            logger.error(f"Error in unflag_account: {e}")
            return False

    async def get_flagged_accounts(self) -> List[Dict[str, Any]]:
        """Get list of all flagged accounts"""
        try:
            if not self.client:
                raise Exception("Graph client not available")
            
            loop = asyncio.get_event_loop()
            
            def get_flagged_sync():
                try:
                    flagged_accounts = []
                    accounts = self.client.V().has_label("account").has("fraud_flag", True).to_list()
                    
                    for account_vertex in accounts:
                        account_props = {}
                        props = self.client.V(account_vertex).value_map().next()
                        for key, value in props.items():
                            if isinstance(value, list) and len(value) > 0:
                                account_props[key] = value[0]
                            else:
                                account_props[key] = value
                        
                        flagged_accounts.append({
                            "account_id": account_props.get("account_id", ""),
                            "type": account_props.get("type", ""),
                            "balance": account_props.get("balance", 0.0),
                            "flag_reason": account_props.get("flagReason", ""),
                            "flag_timestamp": account_props.get("flagTimestamp", ""),
                            "status": account_props.get("status", "active")
                        })
                    
                    return flagged_accounts
                    
                except Exception as e:
                    logger.error(f"Error getting flagged accounts: {e}")
                    return []
            
            return await loop.run_in_executor(None, get_flagged_sync)
            
        except Exception as e:
            logger.error(f"Error in get_flagged_accounts: {e}")
            return []

    async def get_flagged_transactions_paginated(self, page: int, page_size: int) -> Dict[str, Any]:
        """Get paginated list of transactions that have been flagged by fraud detection"""
        try:
            if not self.client:
                raise Exception("Graph client not available")
            
            loop = asyncio.get_event_loop()
            
            def get_flagged_transactions_sync():
                try:
                    # Get all transactions that have flagged_by edges (connected to FraudCheckResult vertices)
                    flagged_transaction_vertices = self.client.V().has_label("transaction").out("flagged_by").in_("flagged_by").dedup().to_list()
                    
                    # Paginate
                    start_idx = (page - 1) * page_size
                    end_idx = start_idx + page_size
                    paginated_transactions = flagged_transaction_vertices[start_idx:end_idx]
                    
                    transactions_data = []
                    for transaction_vertex in paginated_transactions:
                        # Get transaction properties
                        transaction_props = {}
                        props = self.client.V(transaction_vertex).value_map().next()
                        for key, value in props.items():
                            if isinstance(value, list) and len(value) > 0:
                                transaction_props[key] = value[0]
                            else:
                                transaction_props[key] = value
                        
                        # Get sender account
                        sender_id = 'Unknown'
                        try:
                            sender_account_vertices = self.client.V(transaction_vertex).in_("TRANSFERS_TO").to_list()
                            if sender_account_vertices:
                                sender_account_props = {}
                                sender_acc_prop_map = self.client.V(sender_account_vertices[0]).value_map().next()
                                for key, value in sender_acc_prop_map.items():
                                    if isinstance(value, list) and len(value) > 0:
                                        sender_account_props[key] = value[0]
                                    else:
                                        sender_account_props[key] = value
                                sender_id = sender_account_props.get('account_id', 'Unknown')
                        except Exception as e:
                            logger.debug(f"Error getting sender account: {e}")
                        
                        # Get receiver account
                        receiver_id = 'Unknown'
                        try:
                            receiver_account_vertices = self.client.V(transaction_vertex).out("TRANSFERS_FROM").to_list()
                            if receiver_account_vertices:
                                receiver_account_props = {}
                                receiver_acc_prop_map = self.client.V(receiver_account_vertices[0]).value_map().next()
                                for key, value in receiver_acc_prop_map.items():
                                    if isinstance(value, list) and len(value) > 0:
                                        receiver_account_props[key] = value[0]
                                    else:
                                        receiver_account_props[key] = value
                                receiver_id = receiver_account_props.get('account_id', 'Unknown')
                        except Exception as e:
                            logger.debug(f"Error getting receiver account: {e}")
                        
                        # Get fraud check results
                        fraud_score = 0.0
                        fraud_status = 'unknown'
                        fraud_reason = ''
                        try:
                            fraud_result_vertices = self.client.V(transaction_vertex).out("flagged_by").to_list()
                            if fraud_result_vertices:
                                fraud_result_props = {}
                                fraud_props_map = self.client.V(fraud_result_vertices[0]).value_map().next()
                                for key, value in fraud_props_map.items():
                                    if isinstance(value, list) and len(value) > 0:
                                        fraud_result_props[key] = value[0]
                                    else:
                                        fraud_result_props[key] = value
                                
                                fraud_score = fraud_result_props.get('fraud_score', 0.0)
                                fraud_status = fraud_result_props.get('status', 'unknown')
                                fraud_reason = fraud_result_props.get('reason', '')
                        except Exception as e:
                            logger.debug(f"Error getting fraud results: {e}")
                        
                        transactions_data.append({
                            'id': transaction_props.get('transaction_id', ''),
                            'sender_id': sender_id,
                            'receiver_id': receiver_id,
                            'amount': transaction_props.get('amount', 0.0),
                            'currency': 'INR',
                            'timestamp': transaction_props.get('timestamp', ''),
                            'location': transaction_props.get('location', 'Unknown'),
                            'status': transaction_props.get('status', 'completed'),
                            'fraud_score': fraud_score,
                            'transaction_type': transaction_props.get('type', 'transfer'),
                            'is_fraud': fraud_score >= 75,
                            'fraud_status': fraud_status,
                            'fraud_reason': fraud_reason,
                            'device_id': None
                        })
                    
                    return {
                        'transactions': transactions_data,
                        'total': len(flagged_transaction_vertices),
                        'page': page,
                        'page_size': page_size,
                        'total_pages': (len(flagged_transaction_vertices) + page_size - 1) // page_size
                    }
                    
                except Exception as e:
                    logger.error(f"Error getting flagged transactions: {e}")
                    return {
                        'transactions': [],
                        'total': 0,
                        'page': page,
                        'page_size': page_size,
                        'total_pages': 0
                    }
            
            return await loop.run_in_executor(None, get_flagged_transactions_sync)
            
        except Exception as e:
            logger.error(f"Error in get_flagged_transactions_paginated: {e}")
            return {
                'transactions': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0
            }

    async def create_transfer_relationship(self, from_account_id: str, to_account_id: str, amount: float) -> bool:
        """Create a TRANSFERS_TO edge between accounts"""
        try:
            if not self.client:
                raise Exception("Graph client not available")
            
            loop = asyncio.get_event_loop()
            
            def create_relationship_sync():
                try:
                    # Find both accounts
                    from_accounts = self.client.V().has_label("account").has("account_id", from_account_id).to_list()
                    to_accounts = self.client.V().has_label("account").has("account_id", to_account_id).to_list()
                    
                    if not from_accounts or not to_accounts:
                        return False
                    
                    from_vertex = from_accounts[0]
                    to_vertex = to_accounts[0]
                    
                    # Create TRANSFERS_TO edge
                    self.client.add_e("TRANSFERS_TO").from_(from_vertex).to(to_vertex).property("amount", amount).property("timestamp", datetime.now().isoformat()).property("status", "completed").property("method", "test_transfer").iterate()
                    
                    logger.info(f"💸 Created TRANSFERS_TO edge: {from_account_id} → {to_account_id} (${amount})")
                    return True
                    
                except Exception as e:
                    logger.error(f"Error creating transfer relationship: {e}")
                    return False
            
            return await loop.run_in_executor(None, create_relationship_sync)
            
        except Exception as e:
            logger.error(f"Error in create_transfer_relationship: {e}")
            return False

    async def get_fraud_check_results_paginated(self, page: int, page_size: int) -> Dict[str, Any]:
        """Get paginated list of fraud check results"""
        try:
            if not self.client:
                raise Exception("Graph client not available")
            
            loop = asyncio.get_event_loop()
            
            def get_results_sync():
                try:
                    all_results = self.client.V().has_label("FraudCheckResult").to_list()
                    
                    # Paginate
                    start_idx = (page - 1) * page_size
                    end_idx = start_idx + page_size
                    paginated_results = all_results[start_idx:end_idx]
                    
                    results_data = []
                    for result_vertex in paginated_results:
                        result_props = {}
                        props = self.client.V(result_vertex).value_map().next()
                        for key, value in props.items():
                            if isinstance(value, list) and len(value) > 0:
                                result_props[key] = value[0]
                            else:
                                result_props[key] = value
                        
                        # Get associated transaction
                        transaction_vertices = self.client.V(result_vertex).in_("flagged_by").to_list()
                        transaction_id = ""
                        if transaction_vertices:
                            transaction_props = self.client.V(transaction_vertices[0]).value_map().next()
                            transaction_id = transaction_props.get("transaction_id", [""])[0]
                        
                        results_data.append({
                            "transaction_id": transaction_id,
                            "fraud_score": result_props.get("fraud_score", 0.0),
                            "status": result_props.get("status", ""),
                            "rule": result_props.get("rule", ""),
                            "evaluation_timestamp": result_props.get("evaluation_timestamp", ""),
                            "reason": result_props.get("reason", ""),
                            "details": result_props.get("details", "")
                        })
                    
                    return {
                        "fraud_results": results_data,
                        "total": len(all_results),
                        "page": page,
                        "page_size": page_size,
                        "total_pages": (len(all_results) + page_size - 1) // page_size
                    }
                    
                except Exception as e:
                    logger.error(f"Error getting fraud results: {e}")
                    return {
                        "fraud_results": [],
                        "total": 0,
                        "page": page,
                        "page_size": page_size,
                        "total_pages": 0
                    }
            
            return await loop.run_in_executor(None, get_results_sync)
            
        except Exception as e:
            logger.error(f"Error in get_fraud_check_results_paginated: {e}")
            return {
                "fraud_results": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0
            }

    async def get_transaction_fraud_results(self, transaction_id: str) -> List[Dict[str, Any]]:
        """Get fraud check results for a specific transaction"""
        try:
            if not self.client:
                raise Exception("Graph client not available")
            
            loop = asyncio.get_event_loop()
            
            def get_transaction_results_sync():
                try:
                    results_data = []
                    
                    # Find transaction and its fraud results
                    transaction_vertices = self.client.V().has_label("transaction").has("transaction_id", transaction_id).to_list()
                    if not transaction_vertices:
                        return []
                    
                    transaction_vertex = transaction_vertices[0]
                    result_vertices = self.client.V(transaction_vertex).out("flagged_by").to_list()
                    
                    for result_vertex in result_vertices:
                        result_props = {}
                        props = self.client.V(result_vertex).value_map().next()
                        for key, value in props.items():
                            if isinstance(value, list) and len(value) > 0:
                                result_props[key] = value[0]
                            else:
                                result_props[key] = value
                        
                        results_data.append({
                            "fraud_score": result_props.get("fraud_score", 0.0),
                            "status": result_props.get("status", ""),
                            "rule": result_props.get("rule", ""),
                            "evaluation_timestamp": result_props.get("evaluation_timestamp", ""),
                            "reason": result_props.get("reason", ""),
                            "details": result_props.get("details", "")
                        })
                    
                    return results_data
                    
                except Exception as e:
                    logger.error(f"Error getting transaction fraud results: {e}")
                    return []
            
            return await loop.run_in_executor(None, get_transaction_results_sync)
            
        except Exception as e:
            logger.error(f"Error in get_transaction_fraud_results: {e}")
            return [] 

    async def get_connected_device_users(self, user_id: str) -> List[Dict[str, Any]]:
        """Get users who share devices with the specified user"""
        try:
            if not self.client:
                # Mock mode - find users sharing devices from in-memory data
                if not self.users_data:
                    return []
                
                target_user = next((u for u in self.users_data if u['id'] == user_id), None)
                if not target_user:
                    return []
                
                target_device_ids = {device['id'] for device in target_user.get('devices', [])}
                if not target_device_ids:
                    return []
                
                connected_users = []
                for user in self.users_data:
                    if user['id'] == user_id:
                        continue
                    
                    user_device_ids = {device['id'] for device in user.get('devices', [])}
                    shared_devices = target_device_ids.intersection(user_device_ids)
                    
                    if shared_devices:
                        # Get device details for shared devices
                        shared_device_details = []
                        for device in user.get('devices', []):
                            if device['id'] in shared_devices:
                                shared_device_details.append({
                                    'id': device['id'],
                                    'type': device['type'],
                                    'os': device['os'],
                                    'browser': device['browser']
                                })
                        
                        connected_users.append({
                            'user_id': user['id'],
                            'name': user['name'],
                            'email': user['email'],
                            'risk_score': user.get('risk_score', 0.0),
                            'shared_devices': shared_device_details,
                            'shared_device_count': len(shared_devices)
                        })
                
                return connected_users
            
            # Real graph mode
            import asyncio
            loop = asyncio.get_event_loop()
            
            def find_connected_users():
                # Find all devices used by the target user
                user_devices = self.client.V().has_label("user").has("user_id", user_id).out("USES_DEVICE").to_list()
                
                if not user_devices:
                    return []
                
                connected_users = []
                device_to_users = {}
                
                # For each device, find all users who use it
                for device in user_devices:
                    device_props = self.client.V(device).value_map().next()
                    device_id = device_props.get('device_id', [''])[0]
                    
                    # Find all users who use this device
                    users_with_device = self.client.V(device).in_("USES_DEVICE").has_label("user").to_list()
                    
                    for user_vertex in users_with_device:
                        user_props = self.client.V(user_vertex).value_map().next()
                        current_user_id = user_vertex.id
                        
                        # Skip the target user
                        if current_user_id == user_id:
                            continue
                        
                        if current_user_id not in device_to_users:
                            device_to_users[current_user_id] = {
                                'user_props': user_props,
                                'shared_devices': []
                            }
                        
                        # Add device info
                        device_to_users[current_user_id]['shared_devices'].append({
                            'id': device_id,
                            'type': device_props.get('type', [''])[0],
                            'os': device_props.get('os', [''])[0],
                            'browser': device_props.get('browser', [''])[0]
                        })
                
                # Convert to final format
                for user_id_key, data in device_to_users.items():
                    user_props = data['user_props']
                    connected_users.append({
                        'user_id': user_id_key,
                        'name': user_props.get('name', [''])[0],
                        'email': user_props.get('email', [''])[0],
                        'risk_score': user_props.get('risk_score', [0.0])[0],
                        'shared_devices': data['shared_devices'],
                        'shared_device_count': len(data['shared_devices'])
                    })
                
                return connected_users
            
            return await loop.run_in_executor(None, find_connected_users)
            
        except Exception as e:
            logger.error(f"Error getting connected device users for {user_id}: {e}")
            return [] 