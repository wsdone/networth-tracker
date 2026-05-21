from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.exchange_rate import ExchangeRate
from app.models.market_price import MarketPrice
from app.services.exchange_rate import refresh_exchange_rates
from app.services.market_data import refresh_market_prices

router = APIRouter()


@router.get("/quotes")
async def get_quotes(
    symbols: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MarketPrice).order_by(MarketPrice.symbol)
    if symbols:
        symbol_list = [s.strip() for s in symbols.split(",")]
        stmt = stmt.where(MarketPrice.symbol.in_(symbol_list))
    result = await db.execute(stmt)
    prices = result.scalars().all()
    return [
        {
            "symbol": p.symbol,
            "name": p.name,
            "price": float(p.price),
            "prev_close": float(p.prev_close) if p.prev_close else None,
            "change": float(p.change) if p.change else None,
            "change_pct": float(p.change_pct) if p.change_pct else None,
            "currency": p.currency,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
        for p in prices
    ]


@router.post("/refresh")
async def refresh_quotes(db: AsyncSession = Depends(get_db)):
    count = await refresh_market_prices(db)
    return {"message": f"Refreshed {count} quotes"}


@router.get("/exchange-rates")
async def get_exchange_rates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ExchangeRate))
    rates = result.scalars().all()
    return [
        {
            "base_currency": r.base_currency,
            "quote_currency": r.quote_currency,
            "rate": float(r.rate),
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rates
    ]


@router.post("/refresh-rates")
async def refresh_rates(db: AsyncSession = Depends(get_db)):
    count = await refresh_exchange_rates(db)
    return {"message": f"Refreshed {count} exchange rates"}
