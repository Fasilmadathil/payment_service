from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.db import get_db
from app.models import Transaction, Event, Merchant
from app.schemas import (
    TransactionResponse,
    TransactionDetailResponse,
    EventResponse,
    MerchantResponse
)

router = APIRouter()


@router.get("/")
def list_transactions(
    merchant_id: Optional[str] = None,
    payment_status: Optional[str] = None,
    settlement_status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 10,
    offset: int = 0,
    sort_by: str = "occurred_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db)
):
    query = db.query(Transaction)

    # Filters
    if merchant_id:
        query = query.filter(Transaction.merchant_id == merchant_id)

    if payment_status:
        query = query.filter(Transaction.payment_status == payment_status)

    if settlement_status:
        query = query.filter(Transaction.settlement_status == settlement_status)

    if start_date:
        query = query.filter(Transaction.occurred_at >= start_date)

    if end_date:
        query = query.filter(Transaction.occurred_at <= end_date)

    total = query.count()

    # Sorting
    if not hasattr(Transaction, sort_by):
        sort_by = "occurred_at"
    
    sort_attr = getattr(Transaction, sort_by)
    if sort_order.lower() == "asc":
        query = query.order_by(sort_attr.asc())
    else:
        query = query.order_by(sort_attr.desc())

    results = (
        query.offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [TransactionResponse.model_validate(t) for t in results]
    }


@router.get("/{transaction_id}", response_model=TransactionDetailResponse)
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter_by(id=transaction_id).first()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    merchant = db.query(Merchant).filter_by(id=tx.merchant_id).first()

    events = (
        db.query(Event)
        .filter(Event.transaction_id == transaction_id)
        .order_by(Event.event_timestamp)
        .all()
    )

    return {
        "transaction": TransactionResponse.model_validate(tx),
        "merchant": MerchantResponse.model_validate(merchant),
        "events": [EventResponse.model_validate(e) for e in events]
    }