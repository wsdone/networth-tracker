from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class AccountCreate(BaseModel):
    name: str
    type: str
    institution: Optional[str] = None
    currency: str = "CNY"
    balance: float = 0
    include_in_total: bool = True
    group_name: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0
    margin_enabled: bool = False
    own_capital: float = 0
    monthly_deposit: Optional[float] = None
    monthly_offset_amount: Optional[float] = None
    monthly_offset_day: Optional[int] = None
    offset_target_account_id: Optional[str] = None


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    institution: Optional[str] = None
    currency: Optional[str] = None
    balance: Optional[float] = None
    include_in_total: Optional[bool] = None
    group_name: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    margin_enabled: Optional[bool] = None
    own_capital: Optional[float] = None
    monthly_deposit: Optional[float] = None
    monthly_offset_amount: Optional[float] = None
    monthly_offset_day: Optional[int] = None
    offset_target_account_id: Optional[str] = None


class AccountOut(BaseModel):
    id: str
    name: str
    type: str
    institution: Optional[str]
    currency: str
    balance: float
    include_in_total: bool
    group_name: Optional[str]
    tags: Optional[List[str]]
    notes: Optional[str]
    is_active: bool
    sort_order: int
    margin_enabled: bool = False
    own_capital: float = 0
    margin_debt: Optional[float] = None
    monthly_deposit: Optional[float] = None
    monthly_offset_amount: Optional[float] = None
    monthly_offset_day: Optional[int] = None
    offset_target_account_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
