from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.holding import Holding
from app.models.liability import Liability
from app.models.market_price import MarketPrice
from app.models.transaction import Transaction
from app.schemas.holding import HoldingCreate, HoldingOut, HoldingUpdate

router = APIRouter()


async def _enrich_holding(holding: Holding, db: AsyncSession) -> dict:
    result = {
        "id": holding.id,
        "account_id": holding.account_id,
        "symbol": holding.symbol,
        "name": holding.name,
        "asset_type": holding.asset_type,
        "exchange": holding.exchange,
        "quantity": float(holding.quantity),
        "cost_price": float(holding.cost_price),
        "currency": holding.currency,
        "include_in_total": holding.include_in_total,
        "group_name": holding.group_name,
        "tags": holding.tags,
        "notes": holding.notes,
        "margin_liability_id": holding.margin_liability_id,
        "margin_amount": None,
        "margin_interest_rate": None,
        "multiplier": float(holding.multiplier) if holding.multiplier else None,
        "margin_deposit": float(holding.margin_amount) if holding.margin_amount else None,
        "created_at": holding.created_at,
        "updated_at": holding.updated_at,
        "market_price": None,
        "market_value": None,
        "pnl": None,
        "pnl_pct": None,
    }
    if holding.margin_liability_id:
        liab = await db.get(Liability, holding.margin_liability_id)
        if liab:
            result["margin_amount"] = float(liab.balance)
            result["margin_interest_rate"] = float(liab.interest_rate) if liab.interest_rate else None
    mp = await db.execute(select(MarketPrice).where(MarketPrice.symbol == holding.symbol))
    market_price = mp.scalar_one_or_none()
    if market_price:
        price = float(market_price.price)
        qty = float(holding.quantity)
        cost = float(holding.cost_price)
        result["market_price"] = price
        if holding.asset_type == "money_fund":
            # Money fund: price is 万份收益, change_pct is 7日年化收益率
            daily_yield = price * qty / 10000
            result["market_value"] = qty  # principal, not accumulated
            result["pnl"] = daily_yield  # daily earnings
            result["pnl_pct"] = float(market_price.change_pct) if market_price.change_pct else None  # 7日年化%
        elif holding.asset_type == "futures":
            # Futures: pnl = (current_price - cost_price) * multiplier * quantity
            mult = float(holding.multiplier) if holding.multiplier else 1
            result["market_value"] = price * mult * qty
            if qty < 0:
                result["pnl"] = (cost - price) * mult * abs(qty)
            else:
                result["pnl"] = (price - cost) * mult * qty
            result["pnl_pct"] = (result["pnl"] / (cost * mult * abs(qty)) * 100) if cost and qty else None
        elif qty < 0:
            # Short: profit when price drops (cost > price)
            result["market_value"] = price * qty
            result["pnl"] = (cost - price) * abs(qty)
            result["pnl_pct"] = ((cost - price) / cost * 100) if cost else None
        else:
            result["market_value"] = price * qty
            result["pnl"] = (price - cost) * qty
            result["pnl_pct"] = ((price - cost) / cost * 100) if cost else None
    return result


@router.get("", response_model=list[HoldingOut])
async def list_holdings(
    account_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Holding).order_by(Holding.created_at)
    if account_id:
        stmt = stmt.where(Holding.account_id == account_id)
    result = await db.execute(stmt)
    holdings = result.scalars().all()
    return [await _enrich_holding(h, db) for h in holdings]


@router.post("", response_model=HoldingOut, status_code=201)
async def create_holding(data: HoldingCreate, db: AsyncSession = Depends(get_db)):
    buy_price = data.initial_buy_price
    buy_date = data.initial_buy_date
    buy_fee = data.initial_buy_fee
    margin_amount = data.margin_amount
    margin_interest_rate = data.margin_interest_rate

    create_data = data.model_dump(exclude={
        "initial_buy_price", "initial_buy_date", "initial_buy_fee",
        "margin_amount", "margin_interest_rate",
    })
    # Map frontend margin_deposit to model's margin_amount
    if data.margin_deposit is not None:
        create_data["margin_amount"] = data.margin_deposit
    else:
        create_data.pop("margin_deposit", None)

    if buy_price and buy_price > 0:
        create_data["quantity"] = data.quantity or 0
        create_data["cost_price"] = buy_price
    else:
        create_data["quantity"] = 0
        create_data["cost_price"] = 0

    holding = Holding(**create_data)
    db.add(holding)
    await db.flush()

    if buy_price and buy_price > 0 and data.quantity and data.quantity > 0:
        tx = Transaction(
            holding_id=holding.id,
            type="buy",
            date=date.fromisoformat(buy_date) if buy_date else date.today(),
            price=buy_price,
            quantity=data.quantity,
            amount=buy_price * data.quantity,
            fee=buy_fee,
        )
        db.add(tx)

    # Create margin liability if specified
    if margin_amount and margin_amount > 0:
        liab = Liability(
            type="other_loan",
            name=f"融资借款 - {data.symbol} {data.name}",
            direction="owe",
            balance=margin_amount,
            currency=data.currency,
            interest_rate=margin_interest_rate,
            include_in_total=True,
            start_date=date.fromisoformat(buy_date) if buy_date else date.today(),
        )
        db.add(liab)
        await db.flush()
        holding.margin_liability_id = liab.id

    await db.commit()
    await db.refresh(holding)
    return await _enrich_holding(holding, db)


@router.put("/{holding_id}", response_model=HoldingOut)
async def update_holding(
    holding_id: str,
    data: HoldingUpdate,
    db: AsyncSession = Depends(get_db),
):
    holding = await db.get(Holding, holding_id)
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        if key == "margin_deposit":
            setattr(holding, "margin_amount", value)
        else:
            setattr(holding, key, value)
    await db.commit()
    await db.refresh(holding)
    return await _enrich_holding(holding, db)


@router.delete("/{holding_id}", status_code=204)
async def delete_holding(holding_id: str, db: AsyncSession = Depends(get_db)):
    holding = await db.get(Holding, holding_id)
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    if holding.margin_liability_id:
        liab = await db.get(Liability, holding.margin_liability_id)
        if liab:
            await db.delete(liab)
    await db.delete(holding)
    await db.commit()
