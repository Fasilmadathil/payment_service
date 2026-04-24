import pytest
from datetime import datetime, timedelta
from app import models
from app.models import PaymentStatus, SettlementStatus, EventType

def test_reconciliation_summary_date_grouping(client):
    client.post("/events/", json={
        "event_id": "comp-1",
        "event_type": "payment_processed",
        "transaction_id": "tx-comp-1",
        "merchant_id": "m_comp",
        "merchant_name": "Compliance Merchant",
        "amount": 100.50,
        "currency": "INR",
        "timestamp": "2026-04-23T10:00:00+00:00"
    })
    
    res = client.get("/reconciliation/summary")
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    assert "date" in data[0]

def test_terminal_state_protection(client):
    # Send settled first
    client.post("/events/", json={
        "event_id": "t-term-1", "event_type": "settled", "transaction_id": "tx-term",
        "merchant_id": "m1", "merchant_name": "M1", "amount": 100, "currency": "INR", "timestamp": "2026-04-23T10:00:00+00:00"
    })
    
    # Try to send processed later (should be blocked by terminal state)
    res = client.post("/events/", json={
        "event_id": "t-term-2", "event_type": "payment_processed", "transaction_id": "tx-term",
        "merchant_id": "m1", "merchant_name": "M1", "amount": 100, "currency": "INR", "timestamp": "2026-04-23T11:00:00+00:00"
    })
    
    assert res.status_code == 400
    assert "terminal state" in res.json()["detail"].lower()

def test_out_of_order_non_terminal(client):
    # initiated at 12:00
    client.post("/events/", json={
        "event_id": "t-order-1", "event_type": "payment_initiated", "transaction_id": "tx-order",
        "merchant_id": "m1", "merchant_name": "M1", "amount": 100, "currency": "INR", "timestamp": "2026-04-23T12:00:00+00:00"
    })
    
    # Send another event with OLDER timestamp (11:00) - should be ignored as stale
    res = client.post("/events/", json={
        "event_id": "t-order-2", "event_type": "payment_processed", "transaction_id": "tx-order",
        "merchant_id": "m1", "merchant_name": "M1", "amount": 100, "currency": "INR", "timestamp": "2026-04-23T11:00:00+00:00"
    })
    
    assert res.status_code == 400
    assert "stale" in res.json()["detail"].lower()

def test_stale_initiated(client, db_session):
    # Manually insert a stale initiated transaction
    stale_tx = models.Transaction(
        id="tx-stale", merchant_id="m1", amount=100, currency="INR",
        payment_status=PaymentStatus.initiated, settlement_status=SettlementStatus.pending,
        occurred_at=datetime.utcnow() - timedelta(days=2),
        ingested_at=datetime.utcnow() - timedelta(days=2),
        last_event_at=datetime.utcnow() - timedelta(days=2)
    )
    db_session.add(stale_tx)
    db_session.commit()

    res = client.get("/reconciliation/discrepancies")
    assert res.status_code == 200
    issues = [d["issue"] for d in res.json()]
    assert "Stale Initiated Transaction" in issues

def test_invalid_transition(client):
    # initiated -> processed
    client.post("/events/", json={
        "event_id": "t-trans-1", "event_type": "payment_processed", "transaction_id": "tx-trans",
        "merchant_id": "m1", "merchant_name": "M1", "amount": 100, "currency": "INR", "timestamp": "2026-04-23T10:00:00+00:00"
    })
    
    # processed -> initiated (Invalid transition)
    res = client.post("/events/", json={
        "event_id": "t-trans-2", "event_type": "payment_initiated", "transaction_id": "tx-trans",
        "merchant_id": "m1", "merchant_name": "M1", "amount": 100, "currency": "INR", "timestamp": "2026-04-23T11:00:00+00:00"
    })
    
    assert res.status_code == 400
    assert "invalid transition" in res.json()["detail"].lower()
