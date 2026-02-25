# Fraud Detection Graph Data Model

This document defines the vertices and edges used in a graph database for modeling a fraud detection system.

---

## Vertices

### 1. User

- **Label:** `user`
- **Properties:**
    - `name` (string) - Full name of the user
    - `email` (string) - Email address
    - `phone` (string) - Phone number (optional)
    - `age` (int) - Age of the user
    - `location` (string) - User's location/city
    - `occupation` (string) - User's occupation (default: "Unknown")
    - `risk_score` (float) - Risk assessment score (default: 0.0)
    - `signup_date` (datetime) - Date when user signed up

---

### 2. Account

- **Label:** `account`
- **Properties:**
    - `type` (string) - Account type (e.g., "checking", "savings")
    - `balance` (float) - Current account balance
    - `status` (string) - Account status (default: "active")
    - `bank_name` (string) - Name of the bank (default: "Demo Bank")
    - `created_date` (datetime) - Date when account was created
**NOTE** The following properties are only found if your application has `fraud.auto-flag-enabled=true`
  - `fraud_flag` (boolean) - Whether account is flagged as fraudulent (optional)
  - `flag_reason` (string) - Reason for fraud flag (optional)
  - `flag_timestamp` (datetime) - When account was flagged (optional)

---
{device=[fraud_flag, login_count, first_seen, os, last_login, browser, fingerprint, type],

### 3. Device

- **Label:** `device`
- **Properties:**
    - `login_count` (int) - Amount of times the user has logged in with this device
    - `first_seen` (datetime) - First time the user logged in with this device
    - `os` (string) - OS of the device used to log in
    - `last_login` (datetime) - When the user last logged in
    - `browser` (string) - Name of browser that they logged into this application on
    - `type` (string) - Type of device used (e.g., "tablet", "phone")
    - `fingerprint` (string) - Identifier for the users fingerprint
    - `fraud_flag` (boolean) - Whether this device is flagged as fraudulent
---

## Edges

### 1. OWNS

- **From:** `user`
- **To:** `account`
- **Properties:**
    - `since` (datetime) - Date when ownership relationship started (for seeded data)

**Description:** Represents the ownership relationship between a user and their accounts.

---

### 2. Uses

- **From:** `user`
- **To:** `device`
- **Properties:**
  - `usage_count` (int) - Amount of times the User as used the device its linked to
  - `last_used` (datetime) - Timestamp of when the user last used the device
  - `first_used` (datetime) - Timestamp of when the user first used the device

**Description:** Represents the ownership relationship between a user and their accounts.

---

### 3. Transaction
TRANSACTS=[eval_timestamp, detection_time, type, fraud_score, txn_id,
is_fraud, currency, location, gen_type, status, timestamp]}.
- **Label:** `TRANSACTS`
- **Properties:**
  - `txn_id` (string) - Unique identifier for the transaction
  - `amount` (float) - Transaction amount
  - `currency` (string) - Currency code (e.g., "INR")
  - `eval_timestamp` (datetime) - When the transaction started evaluation for fraud
  - `timestamp` (datetime) - When the transaction was created
  - `location` (string) - Geographic location of the transaction
  - `method` (string) - Payment method (default: "transfer")
  - `gen_type` (string) - Generation Type, one of ("AUTO", "MANUAL")
  - `type` (string) - Transaction type (e.g., "transfer", "payment", "deposit", "withdrawal")
  - `status` (string) - Transaction status (e.g., "completed", "pending")

**NOTE** The following properties will only appear if the transaction is deemed fraudulent by the Fraud runs:
- `is_fraud` (boolean) - Whether this transaction is flagged as fraudulent
- `fraud_score` (float) - Fraud risk score for this transaction
- `rule_name` (string) - Name of the Fraud Rule that triggered the flag
- `fraud_status` (string) - FradStatus Enum values, one of ("review), "blocked", "cleared")
- `detection_time` (datetime) - When the transaction was detected as fraudulent

---


## Data Flow

### Transaction Model

The transaction model uses a vertex-centric approach:

1. **Sender Account** → **Transaction** → **Receiver Account**

This allows for:

- Easy traversal to find all transactions initiated by an account
- Easy traversal to find all transactions received by an account
- Rich transaction properties stored on the transaction vertex
- Support for complex fraud detection patterns

### Query Patterns

- **Find sender of a transaction:** `V(transaction).in('TRANSFERS_TO')`
- **Find receiver of a transaction:** `V(transaction).out('TRANSFERS_FROM')`
- **Find all transactions sent by an account:** `V(account).out('TRANSFERS_TO').has_label('transaction')`
- **Find all transactions received by an account:** `V(account).in('TRANSFERS_FROM')`
- **Find all user's transactions:** `V(user).out('OWNS').both('TRANSFERS_TO', 'TRANSFERS_FROM')`

## RT1 Fraud Detection

### RT1: Transaction to Flagged Account Rule

The RT1 rule checks if a transaction's sender or receiver account has previously transferred money to any flagged
account.

**Detection Flow:**

1. Transaction is generated and stored in graph with TRANSFERS_TO/TRANSFERS_FROM edges
2. RT1 check runs immediately after storage
3. System performs 1-hop lookup: `V(account).out('TRANSFERS_TO').has_label('account').has('fraudFlag', true)`
4. If flagged connections found:
    - Calculate fraud score (90-100 based on number of connections)
    - Assign status ("review" or "blocked")
    - Create `FraudCheckResult` vertex
    - Create `flagged_by` edge from transaction to result

**Test Setup:**

1. Flag accounts: `POST /accounts/{account_id}/flag`
2. Create transfer relationships: `POST /accounts/{from_account_id}/transfers-to/{to_account_id}`
3. Generate transactions involving connected accounts
4. View fraud results: `GET /fraud-results` or `GET /transaction/{id}/fraud-results`

