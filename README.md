# 💳 Payment Service

A backend service built with **FastAPI** to ingest payment lifecycle events, maintain transaction state, and provide reconciliation insights.

---

## 📌 Overview

This service processes payment events from multiple upstream systems and maintains a consistent, reliable transaction state.

It exposes APIs for:

- Event ingestion
- Transaction querying
- Reconciliation analysis

### Designed to handle real-world challenges:

- **Duplicate events** — idempotency via unique `event_id`
- **Out-of-order delivery** — timestamp-based event ordering
- **Concurrent updates** — row-level locking to prevent race conditions

---

## 🏗️ Architecture

The system follows a layered architecture:

```
API Layer        →  FastAPI (request validation, routing)
Service Layer    →  Business logic (event processing, reconciliation)
Data Layer       →  SQLAlchemy + PostgreSQL
```

---

## 🧠 Core Design Principles

- **Atomic database transactions** — Event processing is all-or-nothing, preventing partial updates.
- **Idempotent event ingestion** — Duplicate events are safely ignored using a unique `event_id`.
- **Concurrency control (row-level locking)** — Uses `SELECT FOR UPDATE` to prevent race conditions during parallel updates.
- **Immutable event audit trail** — All incoming events are stored permanently, enabling traceability and debugging.

---

## 🗄️ Data Model

### Merchant

Stores merchant metadata.

| Field        | Description                              |
|--------------|------------------------------------------|
| `id`         | Unique merchant identifier (Primary Key) |
| `name`       | Merchant name                            |
| `created_at` | Timestamp when merchant was created      |

---

### Transaction

Represents the current state of a payment lifecycle.

| Field               | Description                                          |
|---------------------|------------------------------------------------------|
| `id`                | Unique transaction ID (Primary Key)                  |
| `merchant_id`       | Associated merchant                                  |
| `amount`            | Transaction amount (`DECIMAL`)                       |
| `currency`          | Currency code (e.g., `INR`)                          |
| `payment_status`    | Enum: `initiated`, `processed`, `failed`             |
| `settlement_status` | Enum: `pending`, `settled`                           |
| `occurred_at`       | Original event occurrence time                       |
| `last_event_at`     | Timestamp of latest valid event (used for ordering)  |
| `ingested_at`       | When transaction was first created                   |
| `updated_at`        | Last update timestamp                                |

---

### Event

Immutable audit log of all incoming events.

| Field             | Description                                                                 |
|-------------------|-----------------------------------------------------------------------------|
| `id`              | Auto-increment internal ID                                                  |
| `event_id`        | Unique external event ID (ensures idempotency)                              |
| `event_type`      | Enum: `payment_initiated`, `payment_processed`, `payment_failed`, `settled` |
| `transaction_id`  | Related transaction                                                         |
| `merchant_id`     | Related merchant                                                            |
| `amount`          | Event amount snapshot                                                       |
| `currency`        | Currency code                                                               |
| `event_timestamp` | Original event timestamp                                                    |
| `ingested_at`     | When event was stored                                                       |

---

### Event Processing Metadata (Audit Layer)

Each event includes processing-level metadata for observability:

| Field               | Description                                    |
|---------------------|------------------------------------------------|
| `processing_status` | Enum: `success`, `duplicate`, `stale`, `invalid_transition`, `terminal_state_blocked`, `error` |
| `error_message`     | Reason for rejection or failure (if any)       |

---

## 📝 Notes on Design

- **Event table is immutable** → ensures full audit trail
- **Transaction is derived state** → built from the event stream
- **`last_event_at`** → prevents out-of-order updates from corrupting state
- **`processing_status`** → provides transparency into system decisions

---

## ✨ Key Features

### 🔁 Idempotent Event Ingestion
Duplicate events are safely ignored using a unique `event_id`.

### 🔒 Concurrency Control
Uses row-level locking (`SELECT FOR UPDATE`) to prevent race conditions.

### ⏱️ Event Ordering
Handles out-of-order events using timestamps — older events are ignored.

### ⚙️ Atomic Processing
Each event is processed within a single database transaction.

### 🚫 Terminal State Protection
Transactions in terminal states (e.g., `settled`, `failed`) cannot be modified.

### 📜 Audit Trail
All events are stored as an immutable log for traceability and debugging.

---

## 📡 API Endpoints

### 1. Ingest Event

```
POST /events
```

**Request Body:**

```json
{
  "event_id": "uuid",
  "event_type": "payment_processed",
  "transaction_id": "txn_123",
  "merchant_id": "merchant_1",
  "merchant_name": "ABC Store",
  "amount": 100.50,
  "currency": "INR",
  "timestamp": "2026-01-01T10:00:00Z"
}
```

---

### 2. List Transactions

```
GET /transactions
```

**Supports:**

- **Filters:** `merchant_id`, `payment_status`, `settlement_status`, `start_date`, `end_date`
- **Pagination:** `limit`, `offset`
- **Sorting:** `timestamp`, `amount`

---

### 3. Transaction Details

```
GET /transactions/{transaction_id}
```

**Returns:**

- Transaction details
- Merchant information
- Full event history (audit trail)

---

### 4. Reconciliation Summary

```
GET /reconciliation/summary
```

**Grouped by:** Merchant · Date · Status

---

### 5. Reconciliation Discrepancies

```
GET /reconciliation/discrepancies
```

**Detects:**

- Processed but not settled
- Failed but settled
- Stale transactions
- Conflicting state mismatches

---

## 📊 Sample Data

A dataset of ~10,000 events is used to simulate:

- Successful transactions
- Failed transactions
- Duplicate events
- Out-of-order events
- Inconsistent states

**Example Event:**

```json
{
  "event_id": "b768e3a7-9eb3-4603-b21c-a54cc95661bc",
  "event_type": "payment_initiated",
  "transaction_id": "2f86e94c-239c-4302-9874-75f28e3474ee",
  "merchant_id": "merchant_2",
  "merchant_name": "FreshBasket",
  "amount": 15248.29,
  "currency": "INR",
  "timestamp": "2026-01-08T12:11:58.085567+00:00"
}
```

---

## ⚙️ Local Setup

### 1. Clone Repository

```bash
git clone <repo_url>
cd payment_service
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

**Windows:**
```bash
venv\Scripts\activate
```

**macOS / Linux:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
export DATABASE_URL=your_database_url
```

### 5. Run the Server

```bash
uvicorn app.main:app --reload
```

Server runs at: `http://127.0.0.1:8000`

---

## 🚀 Deployment

| Property | Value               |
|----------|---------------------|
| Platform | Render              |
| Database | Managed PostgreSQL  |
| Base URL | `<your_render_url>` |

---

## 🧪 Testing

### Postman

Collection available at:

```
/docs/postman
```

### Bulk Event Loader

```bash
python scripts/load_events.py
```

---

## ⚠️ Assumptions

- Events may arrive out of order
- Duplicate events are expected (due to retries)
- Transactions eventually reach a terminal state

---

## ⚖️ Trade-offs

| Decision                     | Pros                  | Cons                                      |
|------------------------------|-----------------------|-------------------------------------------|
| Synchronous Processing       | Simpler architecture  | Less resilient under high traffic spikes  |
| No Retry / Dead Letter Queue | Easier implementation | Risk of dropped events                    |
| Row-Level Locking            | Strong consistency    | Reduced throughput under high concurrency |

---

## 🔮 Future Improvements

- Introduce Kafka / RabbitMQ for async ingestion
- Add retry mechanisms & Dead Letter Queues (DLQ)
- Implement Redis caching
- Add observability (Prometheus metrics, Grafana dashboards)
- Support horizontal scaling

---

## 🚧 Known Gaps

- No authentication or authorization
- No rate limiting
- No schema versioning for events
- No backpressure handling
- No circuit breakers or failover mechanisms

---

## 👤 Author

**Fasil**