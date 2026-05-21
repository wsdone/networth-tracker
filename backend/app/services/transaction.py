from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.account import Account
from app.models.holding import Holding
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionOut, TransactionUpdate

router = APIRouter()


async def _recalc_cost_price(holding_id: str, db: AsyncSession):
    """Recalculate weighted average cost price from all buy transactions."""
    result = await db.execute(
        select(Transaction)
        .where(Transaction.holding_id == holding_id, Transaction.type == "buy")
        .order_by(Transaction.date)
    )
    buy_txs = result.scalars().all()

    if not buy_txs:
        holding = await db.get(Holding, holding_id)
        if holding:
            holding.cost_price = 0
        return

    total_cost = sum(float(tx.price) * float(tx.quantity) + float(tx.fee) for tx in buy_txs)
    total_qty = sum(float(tx.quantity) for tx in buy_txs)

    holding = await db.get(Holding, holding_id)
    if holding:
        total_qty_holding = sum(float(tx.quantity) for tx in buy_txs)
        sell_result = await db.execute(
            select(Transaction)
            .where(Transaction.holding_id == holding_id, Transaction.type == "sell")
            .order_by(Transaction.date)
        )
        sell_txs = sell_result.scalars().all()
        total_sell_qty = sum(float(tx.quantity) for tx in sell_txs)
        current_qty = total_qty_holding - total_sell_qty
        holding.quantity = max(current_qty, 0)
        if total_qty > 0:
            holding.cost_price = total_cost / total_qty
        else:
            holding.cost_price = 0


@router.get("", response_model=list[TransactionOut])
async def list_transactions(
    holding_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Transaction).order_by(Transaction.date.desc(), Transaction.created_at.desc())
    if holding_id:
        stmt = stmt.where(Transaction.holding_id == holding_id)
    if start_date:
        stmt = stmt.where(Transaction.date >= start_date)
    if end_date:
        stmt = stmt.where(Transaction.date <= end_date)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=TransactionOut, status_code=201)
async def create_transaction(data: TransactionCreate, db: AsyncSession = Depends(get_db)):
    holding = await db.get(Holding, data.holding_id)
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")

    amount = data.price * data.quantity
    tx = Transaction(
        holding_id=data.holding_id,
        type=data.type,
        date=data.date,
        price=data.price,
        quantity=data.quantity,
        amount=amount,
        fee=data.fee,
        notes=data.notes,
    )
    db.add(tx)
    await db.flush()

    await _recalc_cost_price(data.holding_id, db)

    # For margin accounts: update balance and own_capital on sell
    if data.type == "sell":
        account = await db.get(Account, holding.account_id)
        if account and account.margin_enabled:
            sell_amount = data.price * data.quantity - data.fee
            profit = (data.price - float(holding.cost_price)) * data.quantity
            # Add proceeds to balance, profit to own_capital
            account.balance = float(account.balance) + sell_amount
            if profit > 0:
                account.own_capital = float(account.own_capital) + profit
    elif data.type == "buy":
        account = await db.get(Account, holding.account_id)
        if account and account.margin_enabled:
            buy_amount = data.price * data.quantity + data.fee
            # Deduct from balance (may go negative if margin)
            account.balance = float(account.balance) - buy_amount

    await db.commit()
    await db.refresh(tx)
    return tx


@router.put("/{tx_id}", response_model=TransactionOut)
async def update_transaction(
    tx_id: str,
    data: TransactionUpdate,
    db: AsyncSession = Depends(get_db),
):
    tx = await db.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(tx, key, value)

    if data.price is not None and data.quantity is not None:
        tx.amount = data.price * data.quantity
    elif data.price is not None:
        tx.amount = data.price * float(tx.quantity)
    elif data.quantity is not None:
        tx.amount = float(tx.price) * data.quantity

    await db.flush()
    await _recalc_cost_price(tx.holding_id, db)
    await db.commit()
    await db.refresh(tx)
    return tx


@router.delete("/{tx_id}", status_code=204)
async def delete_transaction(tx_id: str, db: AsyncSession = Depends(get_db)):
    tx = await db.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    holding_id = tx.holding_id
    holding = await db.get(Holding, holding_id)
    # Rollback margin account changes
    if holding:
        account = await db.get(Account, holding.account_id)
        if account and account.margin_enabled:
            tx_amount = float(tx.price) * float(tx.quantity)
            if tx.type == "sell":
                account.balance = float(account.balance) - (tx_amount - float(tx.fee))
                profit = (float(tx.price) - float(holding.cost_price)) * float(tx.quantity)
                if profit > 0:
                    account.own_capital = float(account.own_capital) - profit
            elif tx.type == "buy":
                account.balance = float(account.balance) + (tx_amount + float(tx.fee))
    await db.delete(tx)
    await _recalc_cost_price(holding_id, db)
    await db.commit()
