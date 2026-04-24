from sqlalchemy import Column, String, Enum, DECIMAL, TIMESTAMP, ForeignKey, Integer, func
from sqlalchemy.orm import relationship
from app.db import Base
import enum

class EventType(str, enum.Enum):
    payment_initiated = "payment_initiated"
    payment_processed = "payment_processed"
    payment_failed = "payment_failed"
    settled = "settled"

class PaymentStatus(str, enum.Enum):
    initiated = "initiated"
    processed = "processed"
    failed = "failed"

class SettlementStatus(str, enum.Enum):
    pending = "pending"
    settled = "settled"

class EventProcessingStatus(str, enum.Enum):
    success = "success"
    duplicate = "duplicate"
    stale = "stale"
    invalid_transition = "invalid_transition"
    terminal_state_blocked = "terminal_state_blocked"
    error = "error"

class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(50), primary_key=True)
    merchant_id = Column(String(50), ForeignKey("merchants.id"), index=True)

    amount = Column(DECIMAL(12, 2))
    currency = Column(String(10))

    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.initiated)
    settlement_status = Column(Enum(SettlementStatus), default=SettlementStatus.pending)

    occurred_at = Column(TIMESTAMP, index=True)
    last_event_at = Column(TIMESTAMP)
    ingested_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)

    event_id = Column(String(100), unique=True, nullable=False)
    event_type = Column(Enum(EventType))

    transaction_id = Column(String(50), index=True)
    merchant_id = Column(String(50), index=True)

    amount = Column(DECIMAL(12, 2))
    currency = Column(String(10))

    event_timestamp = Column(TIMESTAMP, index=True)
    ingested_at = Column(TIMESTAMP, server_default=func.now())
    
    # Auditing
    processing_status = Column(Enum(EventProcessingStatus), default=EventProcessingStatus.success)
    error_message = Column(String(255), nullable=True)