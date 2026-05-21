from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.account import Account
from app.models.holding import Holding
from app.models.market_price import MarketPrice
from app.schemas.account import AccountCreate, AccountOut, AccountUpdate

router = APIRouter()


async def _enrich_account(account: Account, db: AsyncSession) -> dict:
    result = {
        "id": account.id,
        "name": account.name,
        "type": account.type,
        "institution": account.institution,
        "currency": account.currency,
        "balance": float(account.balance),
        "include_in_total": account.include_in_total,
        "group_name": account.group_name,
        "tags": account.tags,
        "notes": account.notes,
        "is_active": account.is_active,
        "sort_order": account.sort_order,
        "margin_enabled": account.margin_enabled,
        "own_capital": float(account.own_capital) if account.own_capital else 0,
        "margin_debt": None,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
    }

    if account.margin_enabled:
        # Calculate total holdings market value for this account
        holdings_result = await db.execute(
            select(Holding).where(Holding.account_id == account.id)
        )
        holdings = holdings_result.scalars().all()

        total_holdings_value = 0.0
        for h in holdings:
            qty = float(h.quantity)
            if qty <= 0:
                continue
            mp_result = await db.execute(
                select(MarketPrice).where(MarketPrice.symbol == h.symbol)
            )
            mp = mp_result.scalar_one_or_none()
            price = float(mp.price) if mp else float(h.cost_price)
            total_holdings_value += price * qty

        # margin_debt = holdings_value - (own_capital - cash_balance)
        own = float(account.own_capital) if account.own_capital else 0
        cash = float(account.balance)
        invested_own = own - cash  # own money that's already in stocks
        margin_debt = max(0.0, total_holdings_value - invested_own)
        result["margin_debt"] = round(margin_debt, 2)

    return result


@router.get("", response_model=list[AccountOut])
async def list_accounts(
    type: str | None = None,
    group: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Account).order_by(Account.sort_order, Account.created_at)
    if type:
        stmt = stmt.where(Account.type == type)
    if group:
        stmt = stmt.where(Account.group_name == group)
    result = await db.execute(stmt)
    accounts = result.scalars().all()
    return [await _enrich_account(a, db) for a in accounts]


@router.post("", response_model=AccountOut, status_code=201)
async def create_account(data: AccountCreate, db: AsyncSession = Depends(get_db)):
    account = Account(**data.model_dump())
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return await _enrich_account(account, db)


@router.put("/{account_id}", response_model=AccountOut)
async def update_account(
    account_id: str,
    data: AccountUpdate,
    db: AsyncSession = Depends(get_db),
):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(account, key, value)
    await db.commit()
    await db.refresh(account)
    return await _enrich_account(account, db)


@router.delete("/{account_id}", status_code=204)
async def delete_account(account_id: str, db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.delete(account)
    await db.commit()


@router.get("/groups", response_model=list[str])
async def list_groups(db: AsyncSession = Depends(get_db)):
    stmt = select(Account.group_name).distinct().where(Account.group_name.isnot(None))
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]
