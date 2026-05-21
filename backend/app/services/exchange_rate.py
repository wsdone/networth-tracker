import logging
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.exchange_rate import ExchangeRate

logger = logging.getLogger(__name__)

SUPPORTED_CURRENCIES = ["USD", "HKD", "CNY"]


async def fetch_exchange_rates_from_api() -> dict[str, float]:
    """Fetch exchange rates from free API (rates against USD)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = f"{settings.EXCHANGE_RATE_API_URL}/USD"
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            rates = data.get("rates", {})
            return {
                "USD_CNY": float(rates.get("CNY", 7.24)),
                "USD_HKD": float(rates.get("HKD", 7.82)),
            }
    except Exception as e:
        logger.error(f"Failed to fetch exchange rates: {e}")
        return {
            "USD_CNY": 7.24,
            "USD_HKD": 7.82,
        }


async def refresh_exchange_rates(db: AsyncSession) -> int:
    """Refresh exchange rates in database."""
    raw_rates = await fetch_exchange_rates_from_api()

    rates = {
        "USD_CNY": raw_rates["USD_CNY"],
        "HKD_CNY": raw_rates["USD_CNY"] / raw_rates["USD_HKD"],
        "CNY_USD": 1 / raw_rates["USD_CNY"],
        "CNY_HKD": raw_rates["USD_HKD"] / raw_rates["USD_CNY"],
        "USD_HKD": raw_rates["USD_HKD"],
        "HKD_USD": 1 / raw_rates["USD_HKD"],
    }

    count = 0
    for pair, rate in rates.items():
        base, quote = pair.split("_")
        existing = await db.execute(
            select(ExchangeRate).where(
                ExchangeRate.base_currency == base,
                ExchangeRate.quote_currency == quote,
            )
        )
        er = existing.scalar_one_or_none()
        if er:
            er.rate = rate
            er.source = "api"
            er.updated_at = datetime.utcnow()
        else:
            er = ExchangeRate(
                base_currency=base,
                quote_currency=quote,
                rate=rate,
                source="api",
            )
            db.add(er)
        count += 1

    await db.commit()
    return count


async def get_rate(db: AsyncSession, base: str, quote: str = "CNY") -> float:
    """Get exchange rate, returns 1.0 if same currency."""
    if base == quote:
        return 1.0
    result = await db.execute(
        select(ExchangeRate).where(
            ExchangeRate.base_currency == base,
            ExchangeRate.quote_currency == quote,
        )
    )
    er = result.scalar_one_or_none()
    if er:
        return float(er.rate)
    return 1.0
