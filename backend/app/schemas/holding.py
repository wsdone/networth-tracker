from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class HoldingCreate(BaseModel):
    account_id: str
    symbol: str
    name: str
    asset_type: str
    exchange: Optional[str] = None
    quantity: float = 0
    cost_price: float = 0
    currency: str = "CNY"
    include_in_total: bool = True
    group_name: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    initial_buy_price: Optional[float] = None
    initial_buy_date: Optional[str] = None
    initial_buy_fee: float = 0
    margin_amount: Optional[float] = None
    margin_interest_rate: Optional[float] = None
    multiplier: Optional[float] = None
    margin_deposit: Optional[float] = None


class HoldingUpdate(BaseModel):
    account_id: Optional[str] = None
    name: Optional[str] = None
    asset_type: Optional[str] = None
    exchange: Optional[str] = None
    currency: Optional[str] = None
    include_in_total: Optional[bool] = None
    group_name: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    multiplier: Optional[float] = None
    margin_deposit: Optional[float] = None


class HoldingOut(BaseModel):
    id: str
    account_id: str
    symbol: str
    name: str
    asset_type: str
    exchange: Optional[str]
    quantity: float
    cost_price: float
    currency: str
    include_in_total: bool
    group_name: Optional[str]
    tags: Optional[List[str]]
    notes: Optional[str]
    margin_liability_id: Optional[str] = None
    margin_amount: Optional[float] = None
    margin_interest_rate: Optional[float] = None
    multiplier: Optional[float] = None
    margin_deposit: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    market_price: Optional[float] = None
    market_value: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None

    model_config = {"from_attributes": True}
