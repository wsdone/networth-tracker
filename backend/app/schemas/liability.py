from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class LiabilityCreate(BaseModel):
    type: str
    name: str
    counterparty: Optional[str] = None
    balance: float = 0
    currency: str = "CNY"
    interest_rate: Optional[float] = None
    monthly_payment: Optional[float] = None
    direction: str = "owe"
    include_in_total: bool = True
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None


class LiabilityUpdate(BaseModel):
    type: Optional[str] = None
    name: Optional[str] = None
    counterparty: Optional[str] = None
    balance: Optional[float] = None
    currency: Optional[str] = None
    interest_rate: Optional[float] = None
    monthly_payment: Optional[float] = None
    direction: Optional[str] = None
    include_in_total: Optional[bool] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None


class LiabilityOut(BaseModel):
    id: str
    type: str
    name: str
    counterparty: Optional[str]
    balance: float
    currency: str
    interest_rate: Optional[float]
    monthly_payment: Optional[float]
    direction: str
    include_in_total: bool
    start_date: Optional[date]
    end_date: Optional[date]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
