from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
import asyncio
import time
from datetime import datetime, timedelta
import random
import uuid
import os
import sys
import argparse

from services.graph_service import GraphService
from services.performance_monitor import performance_monitor

from services.transaction_generator import get_transaction_generator
from models.schemas import (
    User, Account, Transaction, UserSummary, 
    TransactionDetail, FraudPattern, FraudResult
)
from logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger('fraud_detection.api')

# Global variables for command line flags
args = None

# Parse command line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description='Fraud Detection API Server')
    parser.add_argument('-d', '--delete', action='store_true', 
                       help='Delete all data from the graph database on startup')
    parser.add_argument('-l', '--load-users', action='store_true',
                       help='Load data from users.json on startup (same as /seed-data endpoint)')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=4000, help='Port to bind to (default: 4000)')
    return parser.parse_args()

# Initialize services
graph_service = GraphService()
transaction_generator = get_transaction_generator(graph_service)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global args
    
    # Startup
    logger.info("Starting Fraud Detection API")
    logger.info(f"Command line arguments: {args}")
    await graph_service.connect()
    
    # Handle command line flags
    if args and args.delete:
        logger.info("🗑️  Deleting all data from graph database...")
        try:
            result = await graph_service.delete_all_data()
            if "error" in result:
                logger.error(f"Failed to delete data: {result['error']}")
            else:
                logger.info("✅ All data deleted successfully")
        except Exception as e:
            logger.error(f"Error during data deletion: {e}")
    
    if args and args.load_users:
        logger.info("📂 Bulk loading data from CSV files...")
        try:
            result = await graph_service.bulk_load_csv_data()
            if not result["success"]:
                logger.error(f"Failed to load data: {result['error']}")
            else:
                stats = result["statistics"]
                logger.info(f"✅ Data bulk loaded successfully: {stats['users']} users, {stats['accounts']} accounts, {stats['devices']} devices, {stats['total_edges']} edges")
        except Exception as e:
            logger.error(f"Error during data loading: {e}")
    
    # Only automatically load CSV data if AUTO_LOAD_DATA is set to true and no flags are specified
    auto_load_data = os.getenv('AUTO_LOAD_DATA', 'false').lower() == 'true'
    logger.info(f"AUTO_LOAD_DATA environment variable: {auto_load_data}")
    
    if auto_load_data and (not args or (not args.delete and not args.load_users)):
        logger.info("Bulk loading CSV data into graph database...")
        try:
            result = await graph_service.bulk_load_csv_data()
            if not result["success"]:
                logger.error(f"Failed to load data: {result['error']}")
            else:
                stats = result["statistics"]
                logger.info(f"✅ Data bulk loaded successfully: {stats['users']} users, {stats['accounts']} accounts, {stats['devices']} devices, {stats['total_edges']} edges")
        except Exception as e:
            logger.error(f"Error during data loading: {e}")
    elif not args or (not args.delete and not args.load_users):
        logger.info("Skipping automatic data loading (no flags specified and AUTO_LOAD_DATA=false)")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Fraud Detection API")
    await graph_service.close()

app = FastAPI(
    title="Fraud Detection API",
    description="REST API for fraud detection using Aerospike Graph",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4001", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Fraud Detection API is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    graph_status = "connected" if graph_service.client else "error"
    return {
        "status": "healthy",
        "graph_connection": graph_status,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/bulk-load-csv")
async def bulk_load_csv_data(vertices_path: Optional[str] = None, edges_path: Optional[str] = None):
    """Bulk load data from CSV files using Aerospike Graph bulk loader"""
    try:
        result = await graph_service.bulk_load_csv_data(vertices_path, edges_path)
        
        if result["success"]:
            return {
                "message": result["message"],
                "vertices_path": result["vertices_path"],
                "edges_path": result["edges_path"],
                "statistics": result["statistics"],
                "bulk_load_result": result.get("bulk_load_result")
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail={
                    "error": result["error"],
                    "vertices_path": result["vertices_path"],
                    "edges_path": result["edges_path"]
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to bulk load CSV data: {str(e)}")

@app.get("/bulk-load-status")
async def get_bulk_load_status():
    """Get the status of the current bulk load operation"""
    try:
        result = await graph_service.get_bulk_load_status()
        
        if result["success"]:
            return {
                "message": result["message"],
                "status": result["status"]
            }
        else:
            return {
                "message": result["message"],
                "error": result["error"],
                "status": None
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bulk load status: {str(e)}")



@app.get("/user/{user_id}/summary")
async def get_user_summary(user_id: str):
    """Get user's profile, connected accounts, and transaction summary"""
    try:
        user_summary = await graph_service.get_user_summary(user_id)
        if not user_summary:
            raise HTTPException(status_code=404, detail="User not found")
        return user_summary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user summary: {str(e)}")

@app.get("/user/{user_id}/transactions")
async def get_user_transactions(
    user_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of transactions per page")
):
    """Get paginated list of transactions for a specific user"""
    try:
        transactions = await graph_service.get_user_transactions_paginated(user_id, page, page_size)
        if not transactions:
            raise HTTPException(status_code=404, detail="User not found")
        return transactions
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user transactions: {str(e)}")

@app.get("/user/{user_id}/accounts")
async def get_user_accounts(user_id: str):
    """Get all accounts for a specific user"""
    try:
        accounts = await graph_service.get_user_accounts(user_id)
        if not accounts:
            raise HTTPException(status_code=404, detail="User not found")
        return {"user_id": user_id, "accounts": accounts}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user accounts: {str(e)}")

@app.get("/transaction/{transaction_id}")
async def get_transaction_detail(transaction_id: str):
    """Get transaction details and related entities"""
    try:
        transaction_detail = await graph_service.get_transaction_detail(transaction_id)
        if not transaction_detail:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return transaction_detail
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get transaction detail: {str(e)}")

@app.get("/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        stats = await graph_service.get_dashboard_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard stats: {str(e)}")

@app.get("/users")
async def get_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(12, ge=1, le=100, description="Number of users per page")
):
    """Get paginated list of all users"""
    try:
        results = await graph_service.get_users_paginated(page, page_size)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get users: {str(e)}")

@app.get("/users/search")
async def search_users(
    query: str = Query(..., description="Search term for user name or ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(12, ge=1, le=100, description="Number of users per page")
):
    """Search users by name or ID with pagination"""
    try:
        results = await graph_service.search_users_paginated(query, page, page_size)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search users: {str(e)}")

@app.get("/transactions")
async def get_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(12, ge=1, le=100, description="Number of transactions per page")
):
    """Get paginated list of all transactions"""
    try:
        results = await graph_service.get_transactions_paginated(page, page_size)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get transactions: {str(e)}")

@app.get("/transactions/search")
async def search_transactions(
    query: str = Query(..., description="Transaction ID to search for"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(12, ge=1, le=100, description="Number of transactions per page")
):
    """Search transactions by exact transaction ID"""
    try:
        # Get the single transaction detail
        transaction_detail = await graph_service.get_transaction_detail(query)
        
        if transaction_detail:
            # Flatten the nested structure to match frontend expectations
            transaction = transaction_detail.get("transaction", {})
            source_account = transaction_detail.get("source_account", {})
            destination_account = transaction_detail.get("destination_account", {})
            
            flattened_transaction = {
                "id": transaction.get("id", ""),
                "sender_id": source_account.get("id", ""),
                "receiver_id": destination_account.get("id", ""),
                "amount": transaction.get("amount", 0.0),
                "currency": transaction.get("currency", "INR"),
                "timestamp": transaction.get("timestamp", ""),
                "location": transaction.get("location_city", ""),
                "status": transaction.get("status", "completed"),
                "fraud_score": 0.0,  # TODO: Needs to be updated when fraud results are enabled
                "transaction_type": transaction.get("transaction_type", "transfer"),
                "is_fraud": False,   # TODO: Needs to be updated when fraud results are enabled
                "fraud_status": "CLEAN",
                "fraud_reason": "",
                "device_id": None
            }
            
            # Return in the same paginated format expected by frontend
            return {
                "transactions": [flattened_transaction],
                "total_transactions": 1,
                "current_page": 1,
                "total_pages": 1
            }
        else:
            # No transaction found
            return {
                "transactions": [],
                "total_transactions": 0,
                "current_page": 1,
                "total_pages": 0
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search transactions: {str(e)}")

@app.get("/transactions/flagged")
async def get_flagged_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(12, ge=1, le=100, description="Number of transactions per page")
):
    """Get paginated list of transactions that have been flagged by fraud detection"""
    try:
        results = await graph_service.get_flagged_transactions_paginated(page, page_size)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get flagged transactions: {str(e)}")



@app.put("/transaction/{transaction_id}/status")
async def update_transaction_status(
    transaction_id: str,
    status: str = Query(..., description="New status: reviewed, safe, suspicious")
):
    """Update transaction review status"""
    try:
        result = await graph_service.update_transaction_status(transaction_id, status)
        return {"message": "Transaction status updated", "transaction_id": transaction_id, "status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update transaction status: {str(e)}")

# Transaction Generation Endpoints
@app.post("/transaction-generation/start")
async def start_transaction_generation(rate: int = Query(1, ge=1, le=50, description="Generation rate (1-50 transactions per second)")):
    """Start transaction generation at specified rate"""
    try:
        success = await transaction_generator.start_generation(rate)
        if success:
            logger.info(f"🎯 Transaction generation started at {rate} transactions/second")
            return {
                "message": f"Transaction generation started at {rate} transactions/second",
                "status": "started",
                "rate": rate
            }
        else:
            raise HTTPException(status_code=400, detail="Transaction generation is already running")
    except Exception as e:
        logger.error(f"❌ Failed to start transaction generation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start transaction generation: {str(e)}")

@app.post("/transaction-generation/stop")
async def stop_transaction_generation():
    """Stop transaction generation"""
    try:
        success = await transaction_generator.stop_generation()
        if success:
            logger.info("🛑 Transaction generation stopped")
            return {
                "message": "Transaction generation stopped",
                "status": "stopped"
            }
        else:
            raise HTTPException(status_code=400, detail="Transaction generation is not running")
    except Exception as e:
        logger.error(f"❌ Failed to stop transaction generation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop transaction generation: {str(e)}")

@app.post("/transaction-generation/manual")
async def create_manual_transaction(
    from_account_id: str = Query(..., description="Source account ID"),
    to_account_id: str = Query(..., description="Destination account ID"), 
    amount: float = Query(..., gt=0, description="Transaction amount"),
    transaction_type: str = Query("transfer", description="Transaction type")
):
    """Create a manual transaction between specific accounts"""
    try:
        logger.info(f"Attempting to create manual transaction from {from_account_id} to {to_account_id} amount {amount}")
        result = await transaction_generator.create_manual_transaction(
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            amount=amount,
            transaction_type=transaction_type,
            generation_type="MANUAL"
        )
        
        if result:
            logger.info(f"✅ Transaction created: {result['id']}")
            return {
                "message": "Transaction created successfully",
                "transaction_id": result["id"],
                "from_account": result["account_id"],
                "to_account": result["receiver_account_id"],
                "amount": result["amount"],
                "type": result["transaction_type"]
            }
        else:
            logger.error("❌ Failed to create manual transaction")
            raise HTTPException(status_code=400, detail="Failed to create transaction")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create manual transaction: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create manual transaction: {str(e)}")

@app.get("/accounts")
async def get_all_accounts():
    """Get all accounts for manual transaction dropdowns"""
    try:
        accounts = await graph_service.get_all_accounts()
        return {"accounts": accounts}
    except Exception as e:
        logger.error(f"❌ Failed to get accounts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get accounts: {str(e)}")

@app.get("/transaction-generation/status")
async def get_transaction_generation_status():
    """Get current transaction generation status"""
    try:
        status = transaction_generator.get_status()
        return status
    except Exception as e:
        logger.error(f"❌ Failed to get transaction generation status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@app.get("/transaction-generation/recent")
async def get_recent_transactions(limit: int = Query(10, ge=1, le=100, description="Number of recent transactions to return")):
    """Get recent transactions generated by the service"""
    try:
        recent_transactions = transaction_generator.get_recent_transactions(limit)
        return {
            "transactions": recent_transactions,
            "count": len(recent_transactions)
        }
    except Exception as e:
        logger.error(f"❌ Failed to get recent transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recent transactions: {str(e)}")

@app.post("/accounts/{account_id}/flag")
async def flag_account(account_id: str, reason: str = "Manual flag for testing"):
    """Flag an account as fraudulent for RT1 testing"""
    try:
        result = await graph_service.flag_account(account_id, reason)
        if result:
            return {
                "message": f"Account {account_id} flagged successfully",
                "account_id": account_id,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="Account not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to flag account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to flag account: {str(e)}")

@app.delete("/accounts/{account_id}/flag")
async def unflag_account(account_id: str):
    """Remove fraud flag from an account"""
    try:
        result = await graph_service.unflag_account(account_id)
        if result:
            return {
                "message": f"Account {account_id} unflagged successfully",
                "account_id": account_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="Account not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to unflag account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to unflag account: {str(e)}")

@app.get("/accounts/flagged")
async def get_flagged_accounts():
    """Get list of all flagged accounts"""
    try:
        flagged_accounts = await graph_service.get_flagged_accounts()
        return {
            "flagged_accounts": flagged_accounts,
            "count": len(flagged_accounts)
        }
    except Exception as e:
        logger.error(f"❌ Failed to get flagged accounts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get flagged accounts: {str(e)}")

@app.get("/fraud-results")
async def get_fraud_results(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    """Get paginated list of fraud check results"""
    try:
        results = await graph_service.get_fraud_check_results_paginated(page, page_size)
        return results
    except Exception as e:
        logger.error(f"❌ Failed to get fraud results: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get fraud results: {str(e)}")

@app.get("/transaction/{transaction_id}/fraud-results")
async def get_transaction_fraud_results(transaction_id: str):
    """Get fraud check results for a specific transaction"""
    try:
        results = await graph_service.get_transaction_fraud_results(transaction_id)
        return {
            "transaction_id": transaction_id,
            "fraud_results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"❌ Failed to get fraud results for transaction {transaction_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get transaction fraud results: {str(e)}")

@app.post("/accounts/{from_account_id}/transfers-to/{to_account_id}")
async def create_transfer_relationship(from_account_id: str, to_account_id: str, amount: float = 1000.0):
    """Create a TRANSFERS_TO edge between accounts for testing RT1"""
    try:
        result = await graph_service.create_transfer_relationship(from_account_id, to_account_id, amount)
        if result:
            return {
                "message": f"Transfer relationship created: {from_account_id} → {to_account_id}",
                "from_account": from_account_id,
                "to_account": to_account_id,
                "amount": amount,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="One or both accounts not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create transfer relationship: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create transfer relationship: {str(e)}")

@app.get("/user/{user_id}/connected-devices")
async def get_user_connected_devices(user_id: str = Path(..., description="User ID")):
    """Get users who share devices with the specified user"""
    try:
        connected_users = await graph_service.get_connected_device_users(user_id)
        return {
            "user_id": user_id,
            "connected_users": connected_users,
            "total_connections": len(connected_users)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get connected device users: {str(e)}")

# Performance Monitoring Endpoints
@app.get("/performance/stats")
async def get_performance_stats(time_window: int = Query(5, ge=1, le=60, description="Time window in minutes")):
    """Get performance statistics for all fraud detection methods"""
    try:
        stats = performance_monitor.get_all_stats(time_window)
        return {
            "performance_stats": stats,
            "time_window_minutes": time_window,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Failed to get performance stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance stats: {str(e)}")

@app.get("/performance/timeline")
async def get_performance_timeline(minutes: int = Query(5, ge=1, le=60, description="Timeline window in minutes")):
    """Get timeline data for performance charts"""
    try:
        timeline_data = performance_monitor.get_recent_timeline_data(minutes)
        return {
            "timeline_data": timeline_data,
            "time_window_minutes": minutes,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Failed to get performance timeline: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance timeline: {str(e)}")

@app.post("/performance/test/rt1")
async def test_rt1_performance(transaction_count: int = Query(10, ge=1, le=100, description="Number of test transactions")):
    """Test RT1 performance with sample transactions"""
    try:
        # Generate test transactions and measure RT1 performance
        test_results = []
        for i in range(transaction_count):
            # Create a mock transaction for testing
            test_transaction = {
                "id": f"test_rt1_{i}_{uuid.uuid4().hex[:8]}",
                "account_id": f"test_account_{i}",
                "receiver_account_id": f"test_receiver_{i}",
                "amount": random.uniform(10, 1000),
                "timestamp": datetime.now().isoformat()
            }
            
            # Get RT1 service and test it
            rt1_service = transaction_generator.rt1_service
            start_time = time.time()
            result = await rt1_service.check_transaction(test_transaction)
            execution_time = (time.time() - start_time) * 1000
            
            test_results.append({
                "transaction_id": test_transaction["id"],
                "execution_time_ms": round(execution_time, 2),
                "success": result.get("is_fraud") is not None,
                "fraud_detected": result.get("is_fraud", False)
            })
        
        avg_time = sum(r["execution_time_ms"] for r in test_results) / len(test_results)
        
        return {
            "test_type": "RT1",
            "transaction_count": transaction_count,
            "results": test_results,
            "average_execution_time_ms": round(avg_time, 2),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Failed to test RT1 performance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test RT1 performance: {str(e)}")

@app.post("/performance/test/rt2")
async def test_rt2_performance(transaction_count: int = Query(10, ge=1, le=100, description="Number of test transactions")):
    """Test RT2 performance with sample transactions"""
    try:
        # Generate test transactions and measure RT2 performance
        test_results = []
        for i in range(transaction_count):
            # Create a mock transaction for testing
            test_transaction = {
                "id": f"test_rt2_{i}_{uuid.uuid4().hex[:8]}",
                "account_id": f"test_account_{i}",
                "receiver_account_id": f"test_receiver_{i}",
                "amount": random.uniform(10, 1000),
                "timestamp": datetime.now().isoformat()
            }
            
            # Get RT2 service and test it
            rt2_service = transaction_generator.rt2_service
            start_time = time.time()
            result = await rt2_service.check_transaction_fraud(test_transaction)
            execution_time = (time.time() - start_time) * 1000
            
            test_results.append({
                "transaction_id": test_transaction["id"],
                "execution_time_ms": round(execution_time, 2),
                "success": result.get("is_fraud") is not None,
                "fraud_detected": result.get("is_fraud", False)
            })
        
        avg_time = sum(r["execution_time_ms"] for r in test_results) / len(test_results)
        
        return {
            "test_type": "RT2",
            "transaction_count": transaction_count,
            "results": test_results,
            "average_execution_time_ms": round(avg_time, 2),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Failed to test RT2 performance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test RT2 performance: {str(e)}")

@app.post("/performance/test/rt3")
async def test_rt3_performance(transaction_count: int = Query(10, ge=1, le=100, description="Number of test transactions")):
    """Test RT3 performance with sample transactions"""
    try:
        # Generate test transactions and measure RT3 performance
        test_results = []
        for i in range(transaction_count):
            # Create a mock transaction for testing
            test_transaction = {
                "id": f"test_rt3_{i}_{uuid.uuid4().hex[:8]}",
                "account_id": f"test_account_{i}",
                "receiver_account_id": f"test_receiver_{i}",
                "amount": random.uniform(10, 1000),
                "timestamp": datetime.now().isoformat()
            }
            
            # Get RT3 service and test it
            rt3_service = transaction_generator.rt3_service
            start_time = time.time()
            result = await rt3_service.check_transaction(test_transaction)
            execution_time = (time.time() - start_time) * 1000
            
            test_results.append({
                "transaction_id": test_transaction["id"],
                "execution_time_ms": round(execution_time, 2),
                "success": result.get("is_fraud") is not None,
                "fraud_detected": result.get("is_fraud", False)
            })
        
        avg_time = sum(r["execution_time_ms"] for r in test_results) / len(test_results)
        
        return {
            "test_type": "RT3",
            "transaction_count": transaction_count,
            "results": test_results,
            "average_execution_time_ms": round(avg_time, 2),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Failed to test RT3 performance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test RT3 performance: {str(e)}")

@app.post("/performance/reset")
async def reset_performance_metrics():
    """Reset all performance metrics"""
    try:
        performance_monitor.reset_metrics()
        return {
            "message": "Performance metrics reset successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Failed to reset performance metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset performance metrics: {str(e)}")

if __name__ == "__main__":
    args = parse_arguments() # Parse arguments here
    logger.info(f"Parsed arguments: delete={args.delete}, load_users={args.load_users}, host={args.host}, port={args.port}")
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port) 