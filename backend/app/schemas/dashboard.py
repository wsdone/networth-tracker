from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel


class OverviewResponse(BaseModel):
    total_assets_cny: float
    total_liabilities_cny: float
    net_worth_cny: float
    daily_pnl_cny: float
    total_assets_by_currency: Dict[str, float]
    total_liabilities_by_currency: Dict[str, float]


class AssetDistributionItem(BaseModel):
    name: str
    value_cny: float
    percentage: float


class CurrencyOverviewItem(BaseModel):
    currency: str
    currency_name: str = ""
    assets: float
    assets_cny: float
    rate: Optional[float] = None


class GroupSummaryItem(BaseModel):
    group_name: str
    total_cny: float
    percentage: float
