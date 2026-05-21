from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class ExpenseCreate(BaseModel):
    date: date
    amount: float
    currency: str = "CNY"
    category: str
    direction: str = "expense"  # expense/income
    subcategory: Optional[str] = None
    account_id: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = None
    external_id: Optional[str] = None


class ExpenseUpdate(BaseModel):
    date: Optional[date] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    category: Optional[str] = None
    direction: Optional[str] = None
    subcategory: Optional[str] = None
    account_id: Optional[str] = None
    notes: Optional[str] = None


class ExpenseOut(BaseModel):
    id: str
    date: date
    amount: float
    currency: str
    amount_cny: float
    category: str
    direction: str = "expense"
    subcategory: Optional[str]
    account_id: Optional[str]
    liability_id: Optional[str] = None
    notes: Optional[str]
    source: Optional[str] = None
    external_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
