# Fraud Detection Application

A comprehensive fraud detection system built with FastAPI backend and Next.js frontend, utilizing Aerospike Graph for real-time graph-based fraud detection.

## 🚀 Quick Start

**New to this project?** Check out our detailed [Setup Instructions](./setup.md) for complete installation and configuration guidance.

**Already set up?** Run the application:
```bash
./run_app.sh
```

**Access the application:**
- Frontend: http://localhost:4001
- Backend API: http://localhost:4000
- API Documentation: http://localhost:4000/docs

## 🏗️ Architecture

### Backend (Python + FastAPI)
- **Framework**: FastAPI with async support
- **Graph Database**: Aerospike Graph Service (AGS) via Gremlin queries
- **Features**:
  - RESTful API endpoints for fraud detection
  - Real-time Gremlin query execution
  - Sample data seeding
  - User and transaction management
  - Fraud pattern detection algorithms

### Frontend (Next.js + TailwindCSS)
- **Framework**: Next.js 14 with App Router
- **Styling**: TailwindCSS with dark/light theme support
- **Features**:
  - Modern, responsive dashboard
  - Real-time data visualization
  - User and transaction exploration
  - Fraud pattern analysis
  - Interactive graph visualization (Phase 2)


## 🕵️ Fraud Detection System

The system implements real-time fraud detection using graph-based analysis:

### RT1 - Flagged Account Detection
- **Purpose**: Detects transactions involving previously flagged accounts
- **Method**: 1-hop graph lookup for immediate threat detection
- **Risk Level**: High
- **Use Cases**: Known fraudster connections, blacklisted accounts

### RT2 - Flagged Device Connection  
- **Purpose**: Detects transactions involving accounts connected to flagged devices
- **Method**: Network analysis through transaction history
- **Risk Level**: High
- **Use Cases**: Device-based fraud networks, shared device abuse

### RT3 - Supernode Detection (Future)
- **Purpose**: Identifies accounts with unusually high connectivity
- **Method**: Graph centrality analysis
- **Risk Level**: Medium-High
- **Use Cases**: Money laundering hubs, distribution networks


## 📚 Documentation

- **[Setup Instructions](./setup.md)** - Complete installation and configuration guide
- **[Data Model](./datamodel.md)** - Detailed data structure documentation
- **[RT1 Fraud Detection](./RT1_FRAUD_DETECTION.md)** - RT1 implementation details
- **[Project Plan](./plan.md)** - Development roadmap and milestones

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

