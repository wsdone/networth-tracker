from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class TransactionCreate(BaseModel):
    holding_id: str
    type: str
    date: date
    price: float
    quantity: float
    fee: float = 0
    notes: Optional[str] = None


class TransactionUpdate(BaseModel):
    type: Optional[str] = None
    date: Optional[date] = None
    price: Optional[float] = None
    quantity: Optional[float] = None
    fee: Optional[float] = None
    notes: Optional[str] = None


class TransactionOut(BaseModel):
    id: str
    holding_id: str
    type: str
    date: date
    price: float
    quantity: float
    amount: float
    fee: float
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
