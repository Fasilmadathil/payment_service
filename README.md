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
- **Out-of-order delivery** — ordering enforced via `last_event_at`; stale events are stored but ignored
- **Concurrent updates** — row-level locking (`SELECT FOR UPDATE`) implemented in the service layer to prevent race conditions

---

## 🏗️ Architecture

The system follows a layered architecture:

```
API Layer        →  FastAPI (request validation, routing)
Service Layer    →  Business logic (event processing, reconciliation)
Data Layer       →  SQLAlchemy + PostgreSQL
```

---

## 🎯 Design Decisions

These are the key technical choices made and the reasoning behind them:

| Decision | Why |
|---|---|
| **FastAPI** | High performance, native async support, and automatic request validation via Pydantic — ideal for event ingestion at volume |
| **PostgreSQL (production)** | ACID compliance, row-level locking (`SELECT FOR UPDATE`), and robust support for concurrent writes |
| **SQLite (local dev)** | Zero-config local setup; same SQLAlchemy ORM layer means no code changes needed between environments |
| **Event sourcing approach** | Transaction state is *derived* from the event stream — never mutated directly. This ensures a full, trustworthy audit trail |
| **Unique constraint on `event_id`** | Database-enforced idempotency. Even if the application layer misses a duplicate, the DB rejects it |
| **Synchronous processing** | Chosen deliberately for simplicity and debuggability at this scope; async queues are listed as a future improvement |

---

## 🗄️ Database Choice

**PostgreSQL** is used in production because:
- Native support for row-level locking (`SELECT FOR UPDATE`) — critical for safe concurrent event processing
- ACID-compliant transactions ensure atomicity across event ingestion and state updates
- Mature indexing and query planner handles high-volume filtering efficiently

**SQLite** is used locally because:
- Zero configuration — no server process required
- The same SQLAlchemy ORM layer is reused, so no code changes are needed between environments

---

## 🔁 Idempotency Strategy

Idempotency is enforced at two levels:

**1. Database constraint (primary enforcement):**
A `UNIQUE` constraint on `event_id` in the `events` table means the database will reject any duplicate outright — even if the application layer fails to catch it.

**2. Application layer (graceful handling):**
When a duplicate is detected, the system:
- Catches the constraint error
- Rolls back the transaction cleanly
- Returns a success response (the event was already processed — retrying is safe)
- Logs the attempt with `processing_status = duplicate` for observability

This means callers can safely retry on network failure without risk of double-processing.

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

## 🔄 State Transition Model

Transactions follow a strict lifecycle. Invalid transitions (e.g., jumping from `initiated` directly to `settled`) are rejected and logged with `processing_status = invalid_transition`.

```
payment_initiated
       │
       ▼
payment_processed ──────────────────┐
       │                            │
       ▼                            ▼
   settled                     payment_failed
  (terminal)                    (terminal)
```

**Rules:**
- `payment_initiated` → `payment_processed` or `payment_failed` only
- `payment_processed` → `settled` or `payment_failed` only
- `settled` and `payment_failed` are **terminal** — no further transitions allowed

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

## 📊 Sample Data & Data Generation

A dataset of ~10,000 events is used to simulate realistic payment scenarios.

### Generation Strategy

Sample data is generated via `scripts/load_events.py`, which deliberately produces:

| Scenario | Purpose |
|---|---|
| Successful flows (`initiated → processed → settled`) | Happy-path validation |
| Failed payments (`initiated → failed`) | Terminal state protection testing |
| Duplicate `event_id`s | Idempotency verification |
| Out-of-order timestamps | Event ordering logic validation |
| Delayed settlements | Reconciliation discrepancy detection |

Run the loader:

```bash
python scripts/load_events.py
```

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

## 🗂️ Database Optimization

Indexes are added to support efficient filtering, lookups, and joins at scale:

| Index | Column | Table | Reason |
|---|---|---|---|
| Unique constraint | `event_id` | `events` | Enforces idempotency at DB level |
| Index | `transaction_id` | `events` | Fast event history lookup per transaction |
| Index | `merchant_id` | `transactions` | Efficient merchant-level filtering and reconciliation |
| Index | `payment_status` | `transactions` | Fast status-based queries |
| Index | `settlement_status` | `transactions` | Efficient discrepancy detection |

> **Note:** `SQLAlchemy create_all` is used instead of Alembic migrations for simplicity in this scope. A production system would use versioned migrations.

---

## 🚨 Error Handling

The API provides structured, predictable error responses across all failure modes:

| Scenario | Behaviour |
|---|---|
| Invalid payload (missing fields, wrong types) | `422 Unprocessable Entity` — FastAPI/Pydantic validation |
| Duplicate `event_id` | Accepted gracefully; logged with `processing_status = duplicate` |
| Out-of-order event (stale timestamp) | Accepted and stored; logged with `processing_status = stale`, transaction not updated |
| Invalid state transition | Stored with `processing_status = invalid_transition`, error message logged |
| Event on terminal transaction | Stored with `processing_status = terminal_state_blocked` |
| Unexpected server error | `500` with error detail; event stored with `processing_status = error` |

All rejection reasons are persisted in the event audit log — nothing is silently dropped.

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
export DATABASE_URL=sqlite:///./dev.db
```

### 5. Run the Server

```bash
uvicorn app.main:app --reload
```

Server runs at: `http://127.0.0.1:8000`

---

## 🚀 Deployment

| Property | Value              |
|----------|--------------------|
| Platform | Render             |
| Database | Managed PostgreSQL |
| Base URL | `https://payment-service-o236.onrender.com` |

---

## ⚡ Quick Test Flow

The fastest way to verify the service end-to-end:

**Option A — Swagger UI (no tooling required):**

1. Open: `https://payment-service-o236.onrender.com/docs`
2. Run `POST /events` with the sample payload from the [Sample Data](#-sample-data--data-generation) section
3. Verify with `GET /transactions` and `GET /transactions/{transaction_id}`
4. Check `GET /reconciliation/summary` and `GET /reconciliation/discrepancies`

**Option B — Postman:**

Import `postman_collection.json` from the root of the repository and run requests sequentially.

> **Tip:** Load bulk test data first with `python scripts/load_events.py` to see reconciliation results populated.

---

## 🧪 Testing

### Postman

Collection available at the root of the repository:

```
postman_collection.json
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

### Architectural Choices

| Decision | Pros | Cons |
|---|---|---|
| Synchronous processing | Simpler architecture, easier to debug | Less resilient under high traffic spikes |
| No retry / Dead Letter Queue | Easier implementation | Risk of dropped events on transient failures |
| Row-level locking | Strong consistency, no dirty reads | Reduced throughput under very high concurrency |
| `create_all` instead of migrations | Fast local setup, no tooling overhead | Not suitable for production schema evolution |
| Limited state transition validation | Keeps system lightweight and fast | Less strict enforcement of business rules |
| No async processing or queues | Simpler codebase, within project scope | Cannot handle burst traffic; no replay capability |

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