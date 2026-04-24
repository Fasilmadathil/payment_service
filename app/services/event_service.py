from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app import models
from app.models import EventType, PaymentStatus, SettlementStatus, EventProcessingStatus
from datetime import datetime

def is_valid_transition(current_status: PaymentStatus, event_type: EventType) -> bool:
    """Validate payment state machine transitions."""
    if current_status == PaymentStatus.failed:
        # Once failed, it cannot be processed or initiated again
        return event_type not in [EventType.payment_processed, EventType.payment_initiated]
    
    if current_status == PaymentStatus.processed:
        # Once processed, it shouldn't go back to initiated
        return event_type != EventType.payment_initiated
        
    return True

def process_event(db: Session, event_data):
    # Use a single transaction block for atomicity
    # Note: The 'db' session from FastAPI Depends(get_db) is already in a transaction 
    # but we will handle the commit/rollback here explicitly for fine-grained auditing.
    
    # 1. Check for Idempotency (Pre-save check is better than just catching error)
    existing_event = db.query(models.Event).filter_by(event_id=event_data.event_id).first()
    if existing_event:
        return {"message": "Duplicate event ignored", "status": "duplicate"}

    # Ensure timestamp is offset-naive for consistent DB comparison
    event_timestamp = event_data.timestamp
    if event_timestamp.tzinfo is not None:
        event_timestamp = event_timestamp.replace(tzinfo=None)

    db_event = models.Event(
        event_id=event_data.event_id,
        event_type=event_data.event_type,
        transaction_id=event_data.transaction_id,
        merchant_id=event_data.merchant_id,
        amount=event_data.amount,
        currency=event_data.currency,
        event_timestamp=event_timestamp
    )
    db.add(db_event)

    try:
        # 3. Fetch Transaction with Row-Level Locking (Concurrency Control)
        tx = db.query(models.Transaction).filter_by(id=event_data.transaction_id).with_for_update().first()

        # 4. Handle Merchant
        merchant = db.query(models.Merchant).filter_by(id=event_data.merchant_id).first()
        if not merchant:
            merchant = models.Merchant(id=event_data.merchant_id, name=event_data.merchant_name)
            db.add(merchant)

        if not tx:
            # First event for this transaction
            tx = models.Transaction(
                id=event_data.transaction_id,
                merchant_id=event_data.merchant_id,
                amount=event_data.amount,
                currency=event_data.currency,
                occurred_at=event_timestamp,
                last_event_at=event_timestamp
            )
            db.add(tx)
        else:
            # 5. Terminal State Protection
            if tx.settlement_status == SettlementStatus.settled or tx.payment_status == PaymentStatus.failed:
                db_event.processing_status = EventProcessingStatus.terminal_state_blocked
                db_event.error_message = f"Transaction in terminal state ({tx.payment_status}/{tx.settlement_status})"
                db.commit()
                return {"message": db_event.error_message, "status": "blocked"}

            # 6. Temporal Ordering (Ignore stale events)
            if tx.last_event_at and event_timestamp < tx.last_event_at:
                db_event.processing_status = EventProcessingStatus.stale
                db_event.error_message = f"Stale event ignored. Current: {tx.last_event_at}, Incoming: {event_timestamp}"
                db.commit()
                return {"message": db_event.error_message, "status": "stale"}

            # 7. State Transition Validation
            if not is_valid_transition(tx.payment_status, event_data.event_type):
                db_event.processing_status = EventProcessingStatus.invalid_transition
                db_event.error_message = f"Invalid transition: {tx.payment_status} -> {event_data.event_type}"
                db.commit()
                return {"message": db_event.error_message, "status": "invalid"}

        # 8. Update Transaction State
        if event_data.event_type == EventType.payment_processed:
            tx.payment_status = PaymentStatus.processed
        elif event_data.event_type == EventType.payment_failed:
            tx.payment_status = PaymentStatus.failed
        elif event_data.event_type == EventType.settled:
            tx.settlement_status = SettlementStatus.settled

        tx.last_event_at = event_timestamp
        db_event.processing_status = EventProcessingStatus.success
        
        # Single Commit at the end
        db.commit()
        return {"message": "Event processed successfully", "status": "success"}

    except Exception as e:
        db.rollback()
        # Log failure on the event record if possible (requires a new transaction)
        # For now, we'll just raise the error to the API layer
        raise e
