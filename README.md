# Fraud Detection Application

A comprehensive fraud detection system built with Springboot backend and Next.js frontend, utilizing Aerospike Graph for real-time graph-based fraud detection.

## 🚀 Quick Start

Follow the **[Local Dev Setup](./docs/local-setup.md)** for quick start


## Data Generator
```bash
python3 ./scripts/generate_user_data_gcp.py \
  --users 20000 --region american \
  --output ./data/graph_csv \
  --workers 16 \
  --gcs-bucket <bucket-name> \
  --gcs-prefix demo/20kUser/ \
  --gcs-delete-local

```

## 🏗️ Architecture

### Backend (Java + Springboot)
- **Framework**: Springboot
- **Graph Database**: Aerospike Graph Service (AGS) via Gremlin queries
- **Features**:
  - RESTful API endpoints for fraud detection
  - Real-time Gremlin query execution
  - Distributed Bulkload Data Seeding
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

- **[Setup Instructions](./docs/setup.md)** - Complete installation and configuration guide
- **[Data Model](./docs/datamodel.md)** - Detailed data structure documentation
- **[Customizing Functionality](./docs/customizing.md)** - Details on extending this app for your unique use case
- **[Deployment Instructions](./docs/deployment.md)** - Complete instructions for deployment on GCP with Caddy
- **[Local Dev Setup](./docs/local-setup.md)** - Short instructions for setting up local development environment

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

