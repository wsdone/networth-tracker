import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.holding import Holding
from app.models.liability import Liability
from app.models.market_price import MarketPrice

TYPE_CN = {
    "bank": "银行卡", "alipay": "支付宝", "wechat": "微信",
    "broker": "券商", "overseas_bank": "境外银行", "cash": "现金",
    "housing_fund": "公积金",
    "stock": "股票", "fund": "基金", "bond": "债券", "etf": "ETF", "money_fund": "货币基金", "futures": "期货",
}
CURRENCY_CN = {"CNY": "人民币", "HKD": "港币", "USD": "美元"}
LIAB_TYPE_CN = {"mortgage": "房贷", "personal_loan": "个人贷款", "credit_card": "信用卡", "other_loan": "其他贷款"}
from app.models.snapshot import DailySnapshot
from app.services.exchange_rate import get_rate

logger = logging.getLogger(__name__)


async def calculate_totals(db: AsyncSession) -> dict:
    """Calculate total assets, liabilities, and net worth in CNY."""
    # Account balances
    accounts_result = await db.execute(select(Account).where(Account.is_active == True))
    accounts = accounts_result.scalars().all()

    # Holdings with market prices
    holdings_result = await db.execute(select(Holding))
    holdings = holdings_result.scalars().all()

    # Liabilities
    liabilities_result = await db.execute(select(Liability))
    liabilities = liabilities_result.scalars().all()

    total_assets_cny = 0.0
    total_liabilities_cny = 0.0
    assets_by_currency: dict[str, float] = {}
    liabilities_by_currency: dict[str, float] = {}
    assets_by_type: dict[str, float] = {}
    assets_by_group: dict[str, float] = {}
    assets_by_account: dict[str, float] = {}
    assets_by_tag: dict[str, float] = {}
    liabilities_by_type: dict[str, float] = {}

    # Build margin account set and account metadata for later use
    margin_account_ids: set[str] = set()
    acc_meta: dict[str, dict] = {}
    for acc in accounts:
        if acc.margin_enabled:
            margin_account_ids.add(acc.id)
        acc_meta[acc.id] = {
            "name": acc.name,
            "group_name": acc.group_name,
            "tags": acc.tags or [],
        }

    # Sum account balances
    for acc in accounts:
        if not acc.include_in_total:
            continue
        rate = await get_rate(db, acc.currency, "CNY")
        if acc.margin_enabled:
            # Margin account: use own_capital as asset (not balance)
            value = float(acc.own_capital) if acc.own_capital else 0
        else:
            value = float(acc.balance)
        cny_value = value * rate
        total_assets_cny += cny_value
        assets_by_currency[acc.currency] = assets_by_currency.get(acc.currency, 0) + value
        assets_by_type[acc.type] = assets_by_type.get(acc.type, 0) + cny_value
        assets_by_account[acc.name] = assets_by_account.get(acc.name, 0) + cny_value
        if acc.group_name:
            assets_by_group[acc.group_name] = assets_by_group.get(acc.group_name, 0) + cny_value
        if acc.tags:
            for tag in acc.tags:
                assets_by_tag[tag] = assets_by_tag.get(tag, 0) + cny_value

    # Sum holdings market values
    for h in holdings:
        if not h.include_in_total:
            continue
        qty = float(h.quantity)
        if qty == 0:
            continue
        mp_result = await db.execute(select(MarketPrice).where(MarketPrice.symbol == h.symbol))
        mp = mp_result.scalar_one_or_none()
        if mp:
            price = float(mp.price)
        else:
            price = float(h.cost_price)
        mult = float(h.multiplier) if h.multiplier else 1
        if h.asset_type == "futures":
            market_value = price * mult * qty
        elif h.asset_type == "money_fund":
            market_value = qty  # principal for money funds
        else:
            market_value = price * qty
        rate = await get_rate(db, h.currency, "CNY")
        cny_value = market_value * rate
        # Find account info for this holding
        meta = acc_meta.get(h.account_id, {})
        acc_name = meta.get("name", "未知账户")
        h_group = h.group_name or meta.get("group_name")
        h_tags = h.tags or meta.get("tags", [])
        is_margin = h.account_id in margin_account_ids
        if is_margin:
            # Margin holding: only count profit (not full market value) as asset
            cost = float(h.cost_price)
            if qty > 0:
                pnl_value = (price - cost) * qty
            else:
                pnl_value = (cost - price) * abs(qty)
            if pnl_value > 0:
                cny_pnl = pnl_value * rate
                total_assets_cny += cny_pnl
                assets_by_currency[h.currency] = assets_by_currency.get(h.currency, 0) + pnl_value
                assets_by_type[h.asset_type] = assets_by_type.get(h.asset_type, 0) + cny_pnl
                assets_by_account[acc_name] = assets_by_account.get(acc_name, 0) + cny_pnl
                if h_group:
                    assets_by_group[h_group] = assets_by_group.get(h_group, 0) + cny_pnl
                for tag in h_tags:
                    assets_by_tag[tag] = assets_by_tag.get(tag, 0) + cny_pnl
            elif pnl_value < 0:
                cny_loss = abs(pnl_value) * rate
                total_liabilities_cny += cny_loss
                liabilities_by_currency[h.currency] = liabilities_by_currency.get(h.currency, 0) + abs(pnl_value)
        elif qty > 0:
            # Long position: asset
            total_assets_cny += cny_value
            assets_by_currency[h.currency] = assets_by_currency.get(h.currency, 0) + market_value
            assets_by_type[h.asset_type] = assets_by_type.get(h.asset_type, 0) + cny_value
            assets_by_account[acc_name] = assets_by_account.get(acc_name, 0) + cny_value
            if h_group:
                assets_by_group[h_group] = assets_by_group.get(h_group, 0) + cny_value
            for tag in h_tags:
                assets_by_tag[tag] = assets_by_tag.get(tag, 0) + cny_value
        else:
            # Short position: liability (owe shares)
            total_liabilities_cny += abs(cny_value)
            liabilities_by_currency[h.currency] = liabilities_by_currency.get(h.currency, 0) + abs(market_value)

    # Sum liabilities
    for liab in liabilities:
        if not liab.include_in_total:
            continue
        balance = float(liab.balance)
        rate = await get_rate(db, liab.currency, "CNY")
        cny_value = balance * rate
        if liab.direction == "owe":
            total_liabilities_cny += cny_value
            liabilities_by_type[liab.type] = liabilities_by_type.get(liab.type, 0) + cny_value
        else:
            total_assets_cny += cny_value
        liabilities_by_currency[liab.currency] = liabilities_by_currency.get(liab.currency, 0) + balance

    net_worth_cny = total_assets_cny - total_liabilities_cny

    return {
        "total_assets_cny": total_assets_cny,
        "total_liabilities_cny": total_liabilities_cny,
        "net_worth_cny": net_worth_cny,
        "assets_by_currency": assets_by_currency,
        "liabilities_by_currency": liabilities_by_currency,
        "assets_by_type": assets_by_type,
        "assets_by_group": assets_by_group,
        "assets_by_account": assets_by_account,
        "assets_by_tag": assets_by_tag,
        "liabilities_by_type": liabilities_by_type,
    }


async def generate_daily_snapshot(db: AsyncSession) -> DailySnapshot:
    """Generate a daily snapshot for today."""
    today = date.today()

    existing = await db.execute(select(DailySnapshot).where(DailySnapshot.date == today))
    snapshot = existing.scalar_one_or_none()

    totals = await calculate_totals(db)

    # Calculate daily PnL
    daily_pnl = 0.0
    if not snapshot:
        yesterday_result = await db.execute(
            select(DailySnapshot)
            .where(DailySnapshot.date < today)
            .order_by(DailySnapshot.date.desc())
            .limit(1)
        )
        yesterday = yesterday_result.scalar_one_or_none()
        if yesterday:
            daily_pnl = totals["net_worth_cny"] - float(yesterday.net_worth_cny)

    breakdown = {
        "assets_by_currency": totals["assets_by_currency"],
        "liabilities_by_currency": totals["liabilities_by_currency"],
        "assets_by_type": totals["assets_by_type"],
        "assets_by_group": totals["assets_by_group"],
    }

    if snapshot:
        snapshot.total_assets_cny = totals["total_assets_cny"]
        snapshot.total_liabilities_cny = totals["total_liabilities_cny"]
        snapshot.net_worth_cny = totals["net_worth_cny"]
        snapshot.daily_pnl_cny = daily_pnl or float(snapshot.daily_pnl_cny)
        snapshot.breakdown = breakdown
    else:
        snapshot = DailySnapshot(
            date=today,
            total_assets_cny=totals["total_assets_cny"],
            total_liabilities_cny=totals["total_liabilities_cny"],
            net_worth_cny=totals["net_worth_cny"],
            daily_pnl_cny=daily_pnl,
            breakdown=breakdown,
        )
        db.add(snapshot)

    await db.commit()
    await db.refresh(snapshot)
    return snapshot
