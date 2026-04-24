from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from .models import EventType, PaymentStatus, SettlementStatus

class EventCreate(BaseModel):
    event_id: str
    event_type: EventType
    transaction_id: str
    merchant_id: str
    merchant_name: str
    amount: Decimal = Field(ge=0)
    currency: str
    timestamp: datetime


class TransactionResponse(BaseModel):
    id: str
    merchant_id: str
    amount: Decimal
    currency: str
    payment_status: PaymentStatus
    settlement_status: SettlementStatus
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MerchantResponse(BaseModel):
    id: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class EventResponse(BaseModel):
    event_id: str
    event_type: EventType
    transaction_id: str
    merchant_id: str
    amount: Decimal
    currency: str
    event_timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionDetailResponse(BaseModel):
    transaction: TransactionResponse
    merchant: MerchantResponse
    events: List[EventResponse]

    model_config = ConfigDict(from_attributes=True)