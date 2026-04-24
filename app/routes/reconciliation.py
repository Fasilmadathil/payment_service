from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.db import get_db
from app.models import Transaction, Event, PaymentStatus, SettlementStatus, EventType

router = APIRouter()

@router.get("/discrepancies")
def get_discrepancies(db: Session = Depends(get_db)):
    discrepancies = []
    now = datetime.utcnow()

    # 1. Processed but not settled
    processed_not_settled = db.query(Transaction).filter(
        (Transaction.payment_status == PaymentStatus.processed) &
        (Transaction.settlement_status != SettlementStatus.settled)
    ).limit(100).all()
    
    for tx in processed_not_settled:
        issue_type = "Delayed Settlement (>6h)" if tx.updated_at < (now - timedelta(hours=6)) else "Processed but not settled"
        discrepancies.append({
            "transaction_id": tx.id,
            "issue": issue_type,
            "details": f"Payment: {tx.payment_status}, Settlement: {tx.settlement_status}, Ingested: {tx.ingested_at}"
        })

    # 2. Failed but settled
    failed_but_settled = db.query(Transaction).filter(
        (Transaction.payment_status == PaymentStatus.failed) &
        (Transaction.settlement_status == SettlementStatus.settled)
    ).limit(100).all()
    for tx in failed_but_settled:
        discrepancies.append({
            "transaction_id": tx.id, "issue": "Failed but Settled (Critical Bug)", "details": "Settled despite failure"
        })

    # 3. Settled without processing
    settled_no_process = db.query(Transaction).filter(
        (Transaction.payment_status == PaymentStatus.initiated) &
        (Transaction.settlement_status == SettlementStatus.settled)
    ).limit(100).all()
    for tx in settled_no_process:
        discrepancies.append({
            "transaction_id": tx.id, "issue": "Settled without Processing", "details": "Skipped processed state"
        })

    # 4. Stale initiated transactions
    stale_cutoff = now - timedelta(hours=24)
    stale_txs = db.query(Transaction).filter(
        (Transaction.payment_status == PaymentStatus.initiated) &
        (Transaction.ingested_at < stale_cutoff)
    ).limit(100).all()
    for tx in stale_txs:
        discrepancies.append({
            "transaction_id": tx.id, "issue": "Stale Initiated Transaction", "details": f"No update since {tx.ingested_at}"
        })

    # 5. Conflicting events
    conflicting_txids = db.query(Event.transaction_id).filter(
        Event.event_type == EventType.payment_processed
    ).group_by(Event.transaction_id).having(func.count(Event.event_id) > 1).limit(100).all()
    for (txid,) in conflicting_txids:
        discrepancies.append({"transaction_id": txid, "issue": "Conflicting Events", "details": "Multiple processed events"})

    # 7. Event-state mismatch
    mismatched_txs = db.query(Transaction).join(
        Event, Transaction.id == Event.transaction_id
    ).filter(
        (Event.event_type == EventType.settled) &
        (Transaction.settlement_status != SettlementStatus.settled)
    ).limit(100).all()
    for tx in mismatched_txs:
        discrepancies.append({"transaction_id": tx.id, "issue": "Event-State Mismatch", "details": "Event says settled, record says pending"})

    return discrepancies

@router.get("/summary")
def reconciliation_summary(db: Session = Depends(get_db)):
    results = db.query(
        Transaction.merchant_id,
        func.date(Transaction.occurred_at).label("date"),
        Transaction.payment_status,
        Transaction.settlement_status,
        func.count().label("count")
    ).group_by(
        Transaction.merchant_id,
        func.date(Transaction.occurred_at),
        Transaction.payment_status,
        Transaction.settlement_status
    ).all()

    return [
        {
            "merchant_id": r.merchant_id,
            "date": r.date,
            "payment_status": r.payment_status,
            "settlement_status": r.settlement_status,
            "count": r.count
        } for r in results
    ]