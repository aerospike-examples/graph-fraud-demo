import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import os
import time
from typing import List, Dict, Any

from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.driver.aiohttp.transport import AiohttpTransport
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __, constant
from gremlin_python.process.traversal import P, T, Order, containing, Scope

# Get logger for graph service
logger = logging.getLogger('fraud_detection.graph')

class GraphService:
    def __init__(self, host: str = os.environ.get('GRAPH_HOST_ADDRESS') or 'localhost', port: int = 8182):
        self.host = host
        self.port = port
        self.client = None
        self.connection = None
        self.users_data = []
    

    # ----------------------------------------------------------------------------------------------------------
    # Connection maintenance
    # ----------------------------------------------------------------------------------------------------------


    def connect(self):
        """Synchronous connection to Aerospike Graph (to be called outside async context)"""
        try:
            url = f'ws://{self.host}:{self.port}/gremlin'
            logger.info(f" Connecting to Aerospike Graph: {url}")
            
            # Use the same approach as the working sample
            self.connection = DriverRemoteConnection(url, "g", transport_factory=lambda:AiohttpTransport(call_from_event_loop=True))
            self.client = traversal().with_remote(self.connection)
            
            # Test connection using the same method as the sample
            test_result = self.client.inject(0).next()
            if test_result != 0:
                raise Exception("Failed to connect to graph instance")
            
            logger.info(" Connected to Aerospike Graph Service")
            return True
                
        except Exception as e:
            logger.error(f" Could not connect to Aerospike Graph: {e}")
            logger.error("Graph database connection is required. Please ensure Aerospike Graph is running on port 8182")
            self.client = None
            self.connection = None
            raise Exception(f"Failed to connect to Aerospike Graph: {e}")

    def close(self):
        """Synchronous close of graph connection"""
        if self.connection:
            try:
                self.connection.close()
                logger.info(" Disconnected from Aerospike Graph")
            except Exception as e:
                logger.warning(f"  Error closing connection: {e}")


    # ----------------------------------------------------------------------------------------------------------
    # Helper functions
    # ----------------------------------------------------------------------------------------------------------


    def get_vertex(self, user_id: str):
        return self.client.V(user_id).to_list()
    
    def get_out_edge(self, vertex, edge_label: str):
        return self.client.V(vertex).out(edge_label).to_list()
    
    def get_out_out_edge(self, vertex, edge_label1: str, edge_label2: str):
        return self.client.V(vertex).out(edge_label1).out(edge_label2).to_list()
    
    def get_out_in_edge(self, vertex, edge_label1: str, edge_label2: str):
        return self.client.V(vertex).out(edge_label1).in_(edge_label2).to_list()
    
    def get_in_edge(self, vertex, edge_label: str):
        return self.client.V(vertex).in_(edge_label).to_list()
    
    def get_property_value(self, vertex, key, default=None):
        """Helper function to get property value from vertex"""
        for prop in vertex.properties:
            if prop.key == key:
                return prop.value
        return default
    
    def _convert_timestamp_to_long(self, date_str: str) -> int:
        """Convert timestamp string to long integer"""
        import datetime
        timestamp = datetime.datetime.now().timestamp()
        long_timestamp = int(timestamp)
        return long_timestamp

    # ----------------------------------------------------------------------------------------------------------
    # Dashboard functions
    # ----------------------------------------------------------------------------------------------------------


    def get_graph_summary(self) -> Dict[str, Any]:
        """Get graph summary using Aerospike Graph admin API - reusable method"""
        try:
            if not self.client:
                logger.warning("No graph client available for summary")
                return {}
                
            logger.info("Getting graph summary using Aerospike Graph admin API")
            summary_result = self.client.call("aerospike.graph.admin.metadata.summary").next()
            logger.debug(f"Raw graph summary result: {summary_result}")
            
            # Parse and structure the summary data
            parsed_summary = {
                'total_vertex_count': summary_result.get('Total vertex count', 0),
                'total_edge_count': summary_result.get('Total edge count', 0),
                'total_supernode_count': summary_result.get('Total supernode count', 0),
                'vertex_counts': summary_result.get('Vertex count by label', {}),
                'edge_counts': summary_result.get('Edge count by label', {}),
                'supernode_counts': summary_result.get('Supernode count by label', {}),
                'vertex_properties': summary_result.get('Vertex properties by label', {}),
                'edge_properties': summary_result.get('Edge properties by label', {}),
                'raw_summary': summary_result  # Include raw data for advanced use cases
            }
            
            logger.info(f"Parsed graph summary - Vertices: {parsed_summary['total_vertex_count']}, Edges: {parsed_summary['total_edge_count']}")
            return parsed_summary
            
        except Exception as e:
            logger.error(f"Error getting graph summary: {e}")
            return {}
        
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics using Aerospike Graph summary API"""
        try:
            if self.client:
                # Get graph summary using the reusable method
                graph_summary = self.get_graph_summary()
                if graph_summary:
                    vertices = graph_summary['vertex_counts']
                    edges = graph_summary['edge_counts']
                    users = vertices.get('user', 0)
                    txns = edges.get('TRANSACTS', 0)
                    accounts = vertices.get('account', 0)
                    devices = vertices.get('device', 0)
                    
                    logger.info(f"Dashboard stats from summary: users={users}, transactions={txns}, accounts={accounts}, devices={devices}")
                else:
                    users = txns = accounts = devices = 0
                
                # For flagged transactions and total amount, we still need separate queries
                # as these require filtering and aggregation
                flagged = 0
                amount = 0.0
                fraud_rate = 0.0

                if txns > 0:
                    try:
                        txn_stats = (self.client.E()
                            .has_label('TRANSACTS').fold()
                            .project('flagged','amount')
                            .by(__.unfold()
                                .has('fraud_score', P.gt(0))
                                .count())
                            .by(__.unfold()
                                .values('amount')
                                .sum_())
                            .next())
                        
                        flagged = txn_stats.get("flagged", 0)
                        amount = txn_stats.get("amount", 0)
                        fraud_rate = (flagged / txns * 100)
                        
                    except Exception as e:
                        logger.warning(f"Error getting detailed transaction stats: {e}")
                        # Continue with basic stats from summary
                
                return {
                    "users": users,
                    "txns": txns,
                    "flagged": flagged,
                    "amount": amount,
                    "fraud_rate": fraud_rate,
                    "health": "connected"
                }
            else:
                # No graph client available
                raise Exception("Graph client not available. Cannot get dashboard stats without graph database connection.")
                
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return {
                "users": 0,
                "txns": 0,
                "flagged": 0,
                "amount": 0.0,
                "fraud_rate": 0.0,
                "health": "error"
            }


    # ----------------------------------------------------------------------------------------------------------
    # Search function
    # ----------------------------------------------------------------------------------------------------------


    def search(self, type: str, page: int, page_size: int | None, order_by: str, order: str, query: str | None) -> Dict[str, Any]:
        """Get paginated list of all users or transactions"""
        try:
            if self.client:
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size if page_size else -1
                # Query real graph using run_in_executor to avoid event loop conflict
                graph_query = self.client.V().has_label("user") if type == 'user' else self.client.E().has_label("TRANSACTS")
                if query:
                    if type == 'user':
                        graph_query = graph_query.or_(
                                __.has("name", containing(query.title())),
                                __.hasId(containing(query.upper())),
                                __.has("email", containing(query.lower())),
                                __.has("location", containing(query.title()))
                            )
                    else:
                        graph_query = graph_query.or_(
                            __.inV().hasId(containing(query.upper())),
                            __.outV().hasId(containing(query.upper())),
                            __.has("txn_id", containing(query.upper())),
                            __.has("location", containing(query.title()))
                        )
                results = (
                    graph_query.elementMap()
                        .order()
                        .by(order_by, Order.asc if order == 'asc' else Order.desc)
                        .fold()
                        .project("total", "results")
                        .by(__.count(Scope.local))
                        .by(__.unfold().range_(start_idx, end_idx).fold())
                        .next())
                        
                for result in results["results"]:
                    result["id"] = result.pop(T.id)
                    result.pop(T.label)

                return {
                    'result': results["results"],
                    'total': results["total"],
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (results["total"] + page_size - 1) // page_size
                }
            else:
                # No graph client available
                raise Exception("Graph client not available. Cannot get users without graph database connection.")
                
        except Exception as e:
            logger.error(f"Error getting search results: {e}")
            return {
                'results': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0
            }
    

    # ----------------------------------------------------------------------------------------------------------
    # User functions
    # ----------------------------------------------------------------------------------------------------------

        
    def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics"""
        try:
            if self.client:
                stats = self.client.V().has_label("user").values('risk_score').to_list()
                return {
                    'total_users': len(stats),
                    'total_low_risk': len(list(filter(lambda x: x < 25, stats))),
                    'total_med_risk': len(list(filter(lambda x: x >= 25 and x < 70, stats))),
                    'total_high_risk': len(list(filter(lambda x: x >= 70, stats)))
                }
            else:
                # No graph client available
                raise Exception("Graph client not available. Cannot get users without graph database connection.")
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {
                'total_users': 0,
                'total_low_risk': 0,
                'total_med_risk': 0,
                'total_high_risk': 0
            }


    def get_user_summary(self, user_id: str) -> Dict[str, Any]:
        """Get user's profile, connected accounts, and transaction summary"""
        try:
            if self.client:
                logger.info(f"Getting user summary for user {user_id}")
                # Get user vertex and properties
                user_summary = (
                    self.client.V(user_id)
                        .project("user", "accounts", "txns", "total_txns", "total_sent", "total_recd", "devices", "connected_users")
                        .by(__.elementMap())
                        .by(__.out("OWNS").elementMap().fold())
                        .by(__.out("OWNS").bothE("TRANSACTS").order().by("timestamp", Order.desc).limit(10)
                            .project("txn", "other_party")
                            .by(__.elementMap())
                            .by(__.bothV().in_("OWNS").where(__.not_(__.has_id(user_id))).elementMap())
                            .fold())
                        .by(__.out("OWNS").bothE("TRANSACTS").count())
                        .by(__.coalesce(__.out("OWNS").inE("TRANSACTS").values("amount").sum_(), constant(0.00)))
                        .by(__.coalesce(__.out("OWNS").outE("TRANSACTS").values("amount").sum_(), constant(0.00)))
                        .by(__.out("USES").elementMap().fold())
                        .by(__.out("USES").in_("USES").not_(__.hasId(user_id)).fold())
                        .next())
                if not user_summary:
                    return None
                
                user_summary["user"]["id"] = user_summary["user"].pop(T.id)
                user_summary["user"].pop(T.label)
                risk_score = user_summary["user"].get('risk_score', 0.0)
                
                # Calculate fraud risk level based on risk score
                user_summary["risk_level"] = "LOW" if risk_score < 25 else "MEDIUM" if risk_score < 50 else "HIGH" if risk_score < 75 else "CRITICAL"
                return user_summary
            else:
                logger.error("No graph client available. Cannot get user summary without graph database connection.")
                return None
                
        except Exception as e:
            logger.error(f"Error getting user summary: {e}")
            return None


    def get_user_devices(self, user_id: str):
        """Get all devices for a specific user"""
        try:
            pass
        except Exception as e:
            logger.error(f"Error getting user devices: {e}")
            return []


    def get_user_accounts(self, user_id: str):
        """Get all accounts for a specific user"""
        try:
            pass
        except Exception as e:
            logger.error(f"Error getting user accounts: {e}")
            return []


    def get_user_transactions(self, user_id: str):
        """Get all transactions for a specific user (both sent and received)"""
        try:
            pass
        except Exception as e:
            logger.error(f"Error getting user transactions: {e}")
            return [], []


    def get_user_connected_devices(self, user_id: str) -> List[Dict[str, Any]]:
        """Get users who share devices with the specified user"""
        try:
            pass
            
        except Exception as e:
            logger.error(f"Error finding connected device users: {e}")
            return [] 


    # ----------------------------------------------------------------------------------------------------------
    # Transaction functions
    # ----------------------------------------------------------------------------------------------------------


    def get_transaction_stats(self) -> Dict[str, Any]:
        """Get transaction stats"""
        try:
            if self.client:
                stats = (self.client.E()
                    .has_label("TRANSACTS")
                    .fold()
                    .project("total", "blocked", "review")
                    .by(__.unfold().count())
                    .by(__.unfold().has("fraud_status", "blocked").count())
                    .by(__.unfold().has("fraud_status", "review").count())
                    .next())
                
                total = stats.get("total", 0)
                blocked = stats.get("blocked", 0)
                review = stats.get("review", 0)
                return {
                    'total_txns': total,
                    'total_blocked': blocked,
                    'total_review': review,
                    'total_clean': total - blocked - review
                }
            else:
                # No graph client available
                raise Exception("Graph client not available. Cannot get transactions without graph database connection.")
            
        except Exception as e:
            logger.error(f"Error getting transaction stats: {e}")
            return {
                'total_txns': 0,
                'total_blocked': 0,
                'total_review': 0,
                'total_clean': 0
            }


    def get_transaction_summary(self, txn_edge_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed transaction information"""
        try:
            if self.client:
                txn_detail = (self.client.E(txn_edge_id)
                    .project("txn", "src", "dest")
                    .by(__.elementMap())
                    .by(__.outV()
                        .project("account", "user")
                        .by(__.elementMap())
                        .by(__.in_("OWNS").elementMap()))
                    .by(__.inV()
                        .project("account", "user")
                        .by(__.elementMap())
                        .by(__.in_("OWNS").elementMap()))
                    .next())

                return {
                    "txn": txn_detail.get("txn"),
                    "src": txn_detail.get("src"),
                    "dest": txn_detail.get("dest")
                }

            else:
                # No graph client available
                raise Exception("Graph client not available. Cannot get transaction detail without graph database connection.")
                
        except Exception as e:
            logger.error(f"Error getting transaction detail: {e}")
            return None


    def drop_all_transactions(self):
        if self.client:
            try:
                self.client.with_('evaluationTimeout', 0).E().has_label("TRANSACTS").drop().iterate()
                
                edges = 1
                while edges > 0:
                    edges = self.client.E().has_label("TRANSACTS").count()
                    time.sleep(.5)
                
                return True
            
            except Exception as e:
                logger.error(f"An error occured while dropping all transactions: {e}")
                return False
        logger.error("No graph client available. Cannot drop all transactions without graph database connection.")
        return False


    # ----------------------------------------------------------------------------------------------------------
    # Account functions
    # ----------------------------------------------------------------------------------------------------------


    def get_all_accounts(self) -> List[Dict[str, Any]]:
        """Get all accounts with their associated user information"""
        try:
            if self.client:
                accounts = self.client.V().has_label("account").project("account_id", "account_type").by(T.id).by("type").to_list()
                logger.info(f"Found {len(accounts)} account vertices")
                return accounts
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error getting all accounts: {e}")
            return []
        
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
                    
                    logger.info(f" Account {account_id} unflagged")
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
                    # Get all transactions that have fraud_status property (indicating fraud detection was performed)
                    flagged_transaction_vertices = self.client.V().has_label("transaction").has("fraud_status").to_list()
                    
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
                        
                        # Get fraud properties directly from transaction vertex
                        fraud_score = 0.0
                        fraud_status = 'clean'
                        fraud_reason = ''
                        try:
                            # Read fraud properties from transaction vertex itself
                            fraud_status = self.get_property_value(transaction_vertex, 'fraud_status', 'clean')
                            fraud_score = self.get_property_value(transaction_vertex, 'fraud_score', 0.0)
                            fraud_reason = self.get_property_value(transaction_vertex, 'reason', '')
                        except Exception as e:
                            logger.debug(f"Error getting fraud properties: {e}")
                        
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
                    # Get all transactions that have fraud properties (fraud detection was performed)
                    all_results = self.client.V().has_label("transaction").has("fraud_status").to_list()
                    
                    # Paginate
                    start_idx = (page - 1) * page_size
                    end_idx = start_idx + page_size
                    paginated_results = all_results[start_idx:end_idx]
                    
                    results_data = []
                    for transaction_vertex in paginated_results:
                        # Get transaction ID
                        transaction_id = str(transaction_vertex.id)
                        
                        # Read fraud properties directly from transaction vertex
                        results_data.append({
                            "transaction_id": transaction_id,
                            "fraud_score": self.get_property_value(transaction_vertex, 'fraud_score', 0.0),
                            "status": self.get_property_value(transaction_vertex, 'fraud_status', ''),
                            "rule": self.get_property_value(transaction_vertex, 'rule', ''),
                            "evaluation_timestamp": self.get_property_value(transaction_vertex, 'evaluation_timestamp', ''),
                            "reason": self.get_property_value(transaction_vertex, 'reason', ''),
                            "details": self.get_property_value(transaction_vertex, 'details', '')
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
                    
                    # Get transaction vertex directly  
                    transaction_vertices = self.client.V(transaction_id).to_list()
                    if not transaction_vertices:
                        logger.warning(f"Transaction {transaction_id} not found")
                        return []
                    
                    transaction_vertex = transaction_vertices[0]
                    
                    # Read fraud properties directly from transaction vertex
                    fraud_status = self.get_property_value(transaction_vertex, 'fraud_status', '')
                    fraud_score = self.get_property_value(transaction_vertex, 'fraud_score', 0.0)
                    
                    # Only return fraud results if fraud detection was performed
                    if fraud_status and fraud_status.strip():
                        results_data.append({
                            "fraud_score": fraud_score,
                            "status": fraud_status,
                            "rule": self.get_property_value(transaction_vertex, 'rule', ''),
                            "evaluation_timestamp": self.get_property_value(transaction_vertex, 'evaluation_timestamp', ''),
                            "reason": self.get_property_value(transaction_vertex, 'reason', ''),
                            "details": self.get_property_value(transaction_vertex, 'details', '')
                        })
                        logger.info(f"Found fraud results for transaction {transaction_id}: status={fraud_status}, score={fraud_score}")
                    else:
                        logger.info(f"No fraud results found for transaction {transaction_id} - transaction is clean")
                    
                    return results_data
                    
                except Exception as e:
                    logger.error(f"Error getting transaction fraud results: {e}")
                    return []
            
            return await loop.run_in_executor(None, get_transaction_results_sync)
            
        except Exception as e:
            logger.error(f"Error in get_transaction_fraud_results: {e}")
            return [] 
        

    # ----------------------------------------------------------------------------------------------------------
    # Utility functions
    # ----------------------------------------------------------------------------------------------------------

    def bulk_load_csv_data(self, vertices_path: str = None, edges_path: str = None) -> Dict[str, Any]:
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
            
            bulk_load_result = {}
            try:
                # Execute bulk load using Aerospike Graph loader
                logger.info("Starting bulk load operation...")
                bulk_load_result["result"] = (self.client
                            .with_("evaluationTimeout", 2000000)
                            .call("aerospike.graphloader.admin.bulk-load.load")
                            .with_("aerospike.graphloader.vertices", vertices_path)
                            .with_("aerospike.graphloader.edges", edges_path)
                            .next())
                
                logger.info("Bulk load operation started successfully")
                bulk_load_result["success"] = True

            except Exception as e:
                logger.error(f"Bulk load failed: {e}")
                bulk_load_result["success"] = False 
                bulk_load_result["error"] = str(e)
                      
            if bulk_load_result["success"]:
                logger.info("Bulk load completed successfully")
                
                # Get statistics about loaded data
                stats = self._get_bulk_load_statistics()
                
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

    def _get_bulk_load_statistics(self) -> Dict[str, Any]:
        """Get statistics about the loaded data after bulk load using Aerospike Graph Summary API"""
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

    def get_bulk_load_status(self) -> Dict[str, Any]:
        """Get the status of the current bulk load operation using Aerospike Graph Status API"""
        try:
            if not self.client:
                raise Exception("Graph client not available. Cannot check bulk load status without graph database connection.")
            logger.info("Checking bulk load status using Aerospike Graph Status API...")

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

    def inspect_indexes(self) -> Dict[str, Any]:
        """Inspect existing indexes in the graph"""
        try:
            if self.client:
                # Get index cardinality information
                cardinality_info = self.client.call("aerospike.graph.admin.index.cardinality").next()

                # Get index list
                try:
                    index_list = self.client.call("aerospike.graph.admin.index.list").next()
                except Exception as e:
                    index_list = f"Error getting index list: {e}"

                logger.info(f"📊 Index cardinality: {cardinality_info}")
                logger.info(f"📋 Index list: {index_list}")
                return {
                    "cardinality": cardinality_info,
                    "index_list": index_list,
                    "status": "success"
                }
            else:
                raise Exception("Graph client not available")

        except Exception as e:
            logger.error(f"❌ Error inspecting indexes: {e}")
            return {"error": str(e), "status": "error"}

    def create_transaction_indexes(self, minimal: bool = False) -> Dict[str, Any]:
        """Create optimized indexes for transaction queries"""
        try:
            if not self.client:
                raise Exception("Graph client not available")

            results = []

            try:
                result1 = (self.client
                           .call("aerospike.graph.admin.index.create")
                           .with_("name", "transacts_timestamp_desc")
                           .with_("elementType", "edge")
                           .with_("label", "TRANSACTS")
                           .with_("properties", ["timestamp"])
                           .with_("order", "desc")
                           .next())
                results.append({"index": "transacts_timestamp_desc", "status": "created", "result": result1})
                logger.info("Created CRITICAL index: transacts_timestamp_desc")
            except Exception as e:
                results.append({"index": "transacts_timestamp_desc", "status": "error", "error": str(e)})
                logger.warning(f"CRITICAL index transacts_timestamp_desc: {e}")

            if not minimal:
                try:
                    result2 = (self.client
                               .call("aerospike.graph.admin.index.create")
                               .with_("name", "transacts_fraud_status")
                               .with_("elementType", "edge")
                               .with_("label", "TRANSACTS")
                               .with_("properties", ["fraud_status"])
                               .next())
                    results.append({"index": "transacts_fraud_status", "status": "created", "result": result2})
                    logger.info("Created index: transacts_fraud_status")
                except Exception as e:
                    results.append({"index": "transacts_fraud_status", "status": "error", "error": str(e)})
                    logger.warning(f"Index transacts_fraud_status: {e}")

            return {
                "status": "completed",
                "results": results,
                "message": f"Created {len([r for r in results if r['status'] == 'created'])} indexes successfully",
                "mode": "minimal" if minimal else "full"
            }

        except Exception as e:
            logger.error(f"Error creating transaction indexes: {e}")
            return {"error": str(e), "status": "error"}