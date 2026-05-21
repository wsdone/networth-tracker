from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class RepaymentEntryInput(BaseModel):
    month: str  # "2026-06"
    principal: float
    interest: float


class RepaymentPlanCreate(BaseModel):
    liability_id: str
    source_account_id: str
    deduction_day: int  # 1-28
    annual_interest_rate: Optional[float] = None  # User-provided, e.g. 3.3 means 3.3%
    entries: List[RepaymentEntryInput]  # 2-3 months for calibration


class RepaymentPlanUpdate(BaseModel):
    source_account_id: Optional[str] = None
    deduction_day: Optional[int] = None
    annual_interest_rate: Optional[float] = None
    entries: Optional[List[RepaymentEntryInput]] = None  # Re-calibrate from current balance


class RepaymentItemOut(BaseModel):
    id: str
    plan_id: str
    date: date
    principal: float
    interest: float
    total: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RepaymentPlanOut(BaseModel):
    id: str
    liability_id: str
    source_account_id: str
    deduction_day: int
    repayment_type: str
    monthly_rate: float
    monthly_payment: Optional[float] = None
    monthly_principal: Optional[float] = None
    is_active: bool
    liability_name: Optional[str] = None
    source_account_name: Optional[str] = None
    next_payment: Optional[RepaymentItemOut] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RepaymentPlanDetail(BaseModel):
    plan: RepaymentPlanOut
    items: List[RepaymentItemOut]
    projected_months: int
    total_interest: float
