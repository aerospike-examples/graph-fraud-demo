from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime
import urllib.parse

from services.fraud_service import FraudService
from services.graph_service import GraphService
from services.transaction_generator import TransactionGeneratorService
from services.performance_monitor import performance_monitor

from logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger('fraud_detection.api')

# Initialize services
graph_service = GraphService()
fraud_service = FraudService(graph_service)
transaction_generator = TransactionGeneratorService(graph_service, fraud_service)

# Configuration variables
max_generation_rate = 50  # Default max rate, can be changed via API

@asynccontextmanager
async def lifespan(app: FastAPI):
# Startup
    logger.info("Starting Fraud Detection API")
    graph_service.connect()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Fraud Detection API")
    graph_service.close()

app = FastAPI(
    title="Fraud Detection API",
    description="REST API for fraud detection using Aerospike Graph",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------------------------------------------------------
# Health check endpoints
# ----------------------------------------------------------------------------------------------------------


@app.get("/")
def root():
    """Health check endpoint"""
    return {"message": "Fraud Detection API is running", "status": "healthy"}


@app.head("/health")
def docker_health_check():
    """Docker health check endpoint"""
    return True


@app.get("/health")
def health_check():
    """Detailed health check endpoint"""
    graph_status = "connected" if graph_service.client else "error"
    return {
        "status": "healthy",
        "graph_connection": graph_status,
        "timestamp": datetime.now().isoformat()
    }


# ----------------------------------------------------------------------------------------------------------
# Dashboard endpoints
# ----------------------------------------------------------------------------------------------------------


@app.get("/dashboard/stats")
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        return graph_service.get_dashboard_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard stats: {str(e)}")


# ----------------------------------------------------------------------------------------------------------
# User endpoints
# ----------------------------------------------------------------------------------------------------------


@app.get("/users")
def get_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int | None = Query(None, ge=1, le=100, description="Number of users per page"),
    order_by: str = Query('name', description="Field to order results by"),
    order: str = Query('asc', description="Direction to order results"),
    query: str | None = Query(None, description="Search term for user name or ID")
):
    """Get paginated list of all users"""
    try:
        return graph_service.search("user", page, page_size, order_by, order, query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get users: {str(e)}")


@app.get("/users/stats")
def get_users_stats():
    """Get user stats"""
    try:
        return graph_service.get_user_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get users: {str(e)}")


@app.get("/users/{user_id}")
def get_user(user_id: str):
    """Get user's profile, connected accounts, and transaction summary"""
    try:
        user_summary = graph_service.get_user_summary(user_id)
        if not user_summary:
            raise HTTPException(status_code=404, detail="User not found")
        return user_summary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user summary: {str(e)}")


@app.get("/users/{user_id}/accounts")
def get_user_accounts(user_id: str):
    """Get all accounts for a specific user"""
    try:
        accounts = graph_service.get_user_accounts(user_id)
        if not accounts:
            raise HTTPException(status_code=404, detail="User not found")
        return {"user_id": user_id, "accounts": accounts}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user accounts: {str(e)}")


@app.get("/users/{user_id}/devices")
def get_user_devices(user_id: str):
    """Get all devices for a specific user"""
    try:
        devices = graph_service.get_user_devices(user_id)
        if not devices:
            raise HTTPException(status_code=404, detail="User not found")
        return {"user_id": user_id, "devices": devices}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user devices: {str(e)}")


@app.get("/users/{user_id}/transactions")
def get_user_transactions(
    user_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of transactions per page")
):
    """Get paginated list of transactions for a specific user"""
    try:
        transactions = graph_service.get_user_transactions(user_id, page, page_size)
        if not transactions:
            raise HTTPException(status_code=404, detail="User not found")
        return transactions
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user transactions: {str(e)}")


@app.get("/users/{user_id}/connected-devices")
def get_user_connected_devices(user_id: str = Path(..., description="User ID")):
    """Get users who share devices with the specified user"""
    try:
        connected_users = graph_service.get_user_connected_devices(user_id)
        return {
            "user_id": user_id,
            "connected_users": connected_users,
            "total_connections": len(connected_users)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get connected device users: {str(e)}")


# ----------------------------------------------------------------------------------------------------------
# Transaction endpoints
# ----------------------------------------------------------------------------------------------------------


@app.get("/transactions")
def get_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(12, ge=1, le=100, description="Number of transactions per page"),
    order_by: str = Query('name', description="Field to order results by"),
    order: str = Query('asc', description="Direction to order results"),
    query: str | None = Query(None, description="Search term for user name or ID")
):
    """Get paginated list of all transactions"""
    try:
        results = graph_service.search("txns", page, page_size, order_by, order, query)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get transactions: {str(e)}")


@app.delete("/transactions")
def delete_all_transactions():
    """Delete all transactions from the graph"""
    try:
        result = graph_service.drop_all_transactions()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to drop all transactions: {str(e)}")


@app.get("/transactions/stats")
def get_transaction_stats():
    """Get transaction stats"""
    try:
        results = graph_service.get_transaction_stats()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get users: {str(e)}")


@app.get("/transactions/flagged")
def get_flagged_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(12, ge=1, le=100, description="Number of transactions per page")
):
    """Get paginated list of transactions that have been flagged by fraud detection"""
    try:
        results = graph_service.get_flagged_transactions_paginated(page, page_size)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get flagged transactions: {str(e)}")


@app.get("/transaction/{transaction_id}")
def get_transaction_detail(transaction_id: str):
    """Get transaction details and related entities"""
    try:
        transaction_detail = graph_service.get_transaction_summary(urllib.parse.unquote(transaction_id))
        if not transaction_detail:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return transaction_detail
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get transaction detail: {str(e)}")
        

# ----------------------------------------------------------------------------------------------------------
# Transaction generation endpoints
# ----------------------------------------------------------------------------------------------------------


@app.post("/transaction-generation/generate")
def generate_random_transaction():
    try:
        transaction_generator.generate_transaction()
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to generate transaction: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate transaction: {str(e)}")


@app.post("/transaction-generation/start")
def start_transaction_generation(
    rate: int = Query(1, ge=1, description="Generation rate (transactions per second)"),
    start: str = Query("", description="Generation start time")
):
    """Start transaction generation at specified rate"""
    try:
        max_generation_rate = transaction_generator.get_max_transaction_rate()
        
        # Validate rate against dynamic max
        if rate > max_generation_rate:
            raise HTTPException(
                status_code=400,
                detail=f"Generation rate {rate} exceeds maximum allowed rate of {max_generation_rate}"
            )
        
        success = transaction_generator.start_generation(rate, start)
        if success:
            logger.info(f"🎯 Transaction generation started at {rate} transactions/second")
            return {
                "message": f"Transaction generation started at {rate} transactions/second",
                "status": "started",
                "rate": rate,
                "max_rate": max_generation_rate
            }
        else:
            raise HTTPException(status_code=400, detail="Transaction generation is already running")
    except Exception as e:
        logger.error(f"❌ Failed to start transaction generation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start transaction generation: {str(e)}")


@app.post("/transaction-generation/stop")
def stop_transaction_generation():
    """Stop transaction generation"""
    try:
        success = transaction_generator.stop_generation()
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
def create_manual_transaction(
    from_account_id: str = Query(..., description="Source account ID"),
    to_account_id: str = Query(..., description="Destination account ID"), 
    amount: float = Query(..., gt=0, description="Transaction amount"),
    transaction_type: str = Query("transfer", description="Transaction type")
):
    """Create a manual transaction between specific accounts"""
    try:
        logger.info(f"Attempting to create manual transaction from {from_account_id} to {to_account_id} amount {amount}")
        result = transaction_generator.create_manual_transaction(
            from_id=from_account_id,
            to_id=to_account_id,
            amount=amount,
            type=transaction_type,
            gen_type="MANUAL"
        )
        
        if result:
            logger.info(f"✅ Transaction created")
            return {
                "message": "Transaction created successfully",
            }
        else:
            logger.error("❌ Failed to create manual transaction")
            raise HTTPException(status_code=400, detail="Failed to create transaction")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create manual transaction: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create manual transaction: {str(e)}")


# Max Rate Configuration Endpoints
@app.get("/transaction-generation/max-rate")
def get_max_generation_rate():
    """Get the current maximum transaction generation rate"""
    max_generation_rate = transaction_generator.get_max_transaction_rate()
    return {
        "max_rate": max_generation_rate,
        "message": f"Maximum allowed transaction generation rate: {max_generation_rate} transactions/second"
    }


@app.post("/transaction-generation/max-rate")
def set_max_generation_rate(
    new_max_rate: int = Query(..., ge=1, description="New maximum generation rate (minimum 1)")
):
    """Set the maximum transaction generation rate"""
    try:
        success = transaction_generator.set_max_transaction_rate(new_max_rate)
        if success:
            return {
                "max_rate": new_max_rate,
                "message": f"Maximum generation rate updated to {new_max_rate} transactions/second"
            }
        else:
            return {
                "message": f"Maximum generation rate unable to be updated to {new_max_rate} transactions/second"
            }
        
    except Exception as e:
        logger.error(f"❌ Failed to update max generation rate: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update max generation rate: {str(e)}")


@app.get("/transaction-generation/status")
async def get_transaction_generation_status():
    """Get current transaction generation status"""
    try:
        status = transaction_generator.get_status()
        return status
    except Exception as e:
        logger.error(f"❌ Failed to get transaction generation status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


# ----------------------------------------------------------------------------------------------------------
# Account endpoints
# ----------------------------------------------------------------------------------------------------------


@app.get("/accounts")
def get_all_accounts():
    """Get all accounts for manual transaction dropdowns"""
    try:
        accounts = graph_service.get_all_accounts()
        return { "accounts": accounts }
    except Exception as e:
        logger.error(f"❌ Failed to get accounts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get accounts: {str(e)}")


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


# ----------------------------------------------------------------------------------------------------------
# Performance monitoring endpoints
# ----------------------------------------------------------------------------------------------------------


@app.get("/performance/stats")
def get_performance_stats(time_window: int = Query(5, ge=1, le=60, description="Time window in minutes")):
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
def get_performance_timeline(minutes: int = Query(5, ge=1, le=60, description="Timeline window in minutes")):
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


@app.post("/performance/reset")
def reset_performance_metrics():
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


# ----------------------------------------------------------------------------------------------------------
# Bulk loading endpoints
# ----------------------------------------------------------------------------------------------------------


@app.post("/bulk-load-csv")
def bulk_load_csv_data(vertices_path: Optional[str] = None, edges_path: Optional[str] = None):
    """Bulk load data from CSV files using Aerospike Graph bulk loader"""
    try:
        result = graph_service.bulk_load_csv_data(vertices_path, edges_path)
        
        if result["success"]:
            return result
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
def get_bulk_load_status():
    """Get the status of the current bulk load operation"""
    try:
        result = graph_service.get_bulk_load_status()
        
        if result["success"]:
            return result
        else:
            return {
                "message": result["message"],
                "error": result["error"],
                "status": None
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bulk load status: {str(e)}")