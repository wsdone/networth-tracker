from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.account import Account
from app.models.expense import Expense
from app.models.holding import Holding
from app.models.liability import Liability
from app.models.market_price import MarketPrice
from app.models.snapshot import DailySnapshot
from app.schemas.dashboard import (
    AssetDistributionItem,
    CurrencyOverviewItem,
    GroupSummaryItem,
    OverviewResponse,
)
from app.services.exchange_rate import get_rate
from app.services.snapshot import calculate_totals, TYPE_CN, CURRENCY_CN, LIAB_TYPE_CN

router = APIRouter()


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(db: AsyncSession = Depends(get_db)):
    totals = await calculate_totals(db)
    return OverviewResponse(
        total_assets_cny=totals["total_assets_cny"],
        total_liabilities_cny=totals["total_liabilities_cny"],
        net_worth_cny=totals["net_worth_cny"],
        daily_pnl_cny=0,
        total_assets_by_currency=totals["assets_by_currency"],
        total_liabilities_by_currency=totals["liabilities_by_currency"],
    )


@router.get("/asset-distribution", response_model=list[AssetDistributionItem])
async def get_asset_distribution(
    by: str = "type",
    db: AsyncSession = Depends(get_db),
):
    totals = await calculate_totals(db)
    if by == "group":
        data = totals["assets_by_group"]
    elif by == "account":
        data = totals["assets_by_account"]
    elif by == "tag":
        data = totals["assets_by_tag"]
    else:
        data = totals["assets_by_type"]

    total = sum(data.values()) or 1
    return [
        AssetDistributionItem(
            name=TYPE_CN.get(k, k) if by == "type" else k,
            value_cny=v,
            percentage=round(v / total * 100, 2),
        )
        for k, v in sorted(data.items(), key=lambda x: -x[1])
    ]


@router.get("/liability-distribution", response_model=list[AssetDistributionItem])
async def get_liability_distribution(db: AsyncSession = Depends(get_db)):
    totals = await calculate_totals(db)
    data = totals["liabilities_by_type"]
    total = sum(data.values()) or 1
    return [
        AssetDistributionItem(
            name=LIAB_TYPE_CN.get(k, k),
            value_cny=v,
            percentage=round(v / total * 100, 2),
        )
        for k, v in sorted(data.items(), key=lambda x: -x[1])
    ]


@router.get("/currency-overview", response_model=list[CurrencyOverviewItem])
async def get_currency_overview(db: AsyncSession = Depends(get_db)):
    totals = await calculate_totals(db)
    result = []
    for currency, amount in totals["assets_by_currency"].items():
        rate = await get_rate(db, currency, "CNY")
        result.append(
            CurrencyOverviewItem(
                currency=currency,
                currency_name=CURRENCY_CN.get(currency, currency),
                assets=amount,
                assets_cny=amount * rate,
                rate=rate if currency != "CNY" else None,
            )
        )
    return sorted(result, key=lambda x: -x.assets_cny)


@router.get("/group-summary", response_model=list[GroupSummaryItem])
async def get_group_summary(db: AsyncSession = Depends(get_db)):
    totals = await calculate_totals(db)
    data = totals["assets_by_group"]
    total = sum(data.values()) or 1
    return [
        GroupSummaryItem(
            group_name=k,
            total_cny=v,
            percentage=round(v / total * 100, 2),
        )
        for k, v in sorted(data.items(), key=lambda x: -x[1])
    ]


@router.get("/trend")
async def get_trend(days: int = 30, db: AsyncSession = Depends(get_db)):
    from datetime import date, timedelta

    start_date = date.today() - timedelta(days=days)
    result = await db.execute(
        select(DailySnapshot)
        .where(DailySnapshot.date >= start_date)
        .order_by(DailySnapshot.date)
    )
    snapshots = result.scalars().all()
    return [
        {
            "date": s.date.isoformat(),
            "total_assets_cny": float(s.total_assets_cny),
            "total_liabilities_cny": float(s.total_liabilities_cny),
            "net_worth_cny": float(s.net_worth_cny),
            "daily_pnl_cny": float(s.daily_pnl_cny),
        }
        for s in snapshots
    ]


@router.get("/expense-trend")
async def get_expense_trend(months: int = 6, db: AsyncSession = Depends(get_db)):
    """Monthly income/expense trend for dashboard."""
    result = await db.execute(
        select(
            func.strftime("%Y-%m", Expense.date).label("month"),
            Expense.direction,
            func.sum(Expense.amount).label("total"),
        )
        .group_by("month", Expense.direction)
        .order_by("month")
    )
    rows = result.all()

    month_data: dict[str, dict] = {}
    for row in rows:
        m = row[0]
        if m not in month_data:
            month_data[m] = {"month": m, "expense": 0, "income": 0}
        month_data[m][row[1]] = round(float(row[2]), 2)

    sorted_months = sorted(month_data.keys())
    if len(sorted_months) > months:
        sorted_months = sorted_months[-months:]

    return [month_data[m] for m in sorted_months]
