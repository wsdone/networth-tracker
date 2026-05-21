from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.account import Account
from app.models.expense import Expense
from app.models.liability import Liability
from app.schemas.liability import LiabilityCreate, LiabilityOut, LiabilityUpdate

router = APIRouter()


class RepayRequest(BaseModel):
    account_id: str
    principal: float
    interest: float = 0


class CollectRequest(BaseModel):
    account_id: str
    amount: float


@router.post("/{liability_id}/repay")
async def repay_liability(
    liability_id: str,
    data: RepayRequest,
    db: AsyncSession = Depends(get_db),
):
    """Repay a liability: principal reduces debt, interest recorded as expense."""
    liability = await db.get(Liability, liability_id)
    if not liability:
        raise HTTPException(status_code=404, detail="Liability not found")

    account = await db.get(Account, data.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    total = data.principal + data.interest
    if float(account.balance) < total:
        raise HTTPException(status_code=400, detail="账户余额不足")

    # Deduct from account
    account.balance = float(account.balance) - total

    # Reduce liability balance
    liability.balance = float(liability.balance) - data.principal
    if float(liability.balance) < 0:
        liability.balance = 0

    # Interest as expense
    if data.interest > 0:
        expense = Expense(
            date=date.today(),
            amount=data.interest,
            currency=liability.currency or "CNY",
            amount_cny=data.interest,
            category="利息",
            direction="expense",
            notes=f"{liability.name} 利息",
            account_id=data.account_id,
            liability_id=liability_id,
        )
        db.add(expense)

    await db.commit()
    return {
        "principal": data.principal,
        "interest": data.interest,
        "total": total,
        "remaining_debt": float(liability.balance),
    }


@router.post("/{liability_id}/collect")
async def collect_lent(
    liability_id: str,
    data: CollectRequest,
    db: AsyncSession = Depends(get_db),
):
    """Collect money back from a lent liability (别人欠我)."""
    liability = await db.get(Liability, liability_id)
    if not liability:
        raise HTTPException(status_code=404, detail="Liability not found")
    if liability.direction != "lent":
        raise HTTPException(status_code=400, detail="Only lent liabilities can be collected")

    account = await db.get(Account, data.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    amount = min(data.amount, float(liability.balance))

    # Add to account balance
    account.balance = float(account.balance) + amount

    # Reduce liability balance
    liability.balance = float(liability.balance) - amount
    if float(liability.balance) < 0:
        liability.balance = 0

    # Record as income
    expense = Expense(
        date=date.today(),
        amount=amount,
        currency=liability.currency or "CNY",
        amount_cny=amount,
        category="收回欠款",
        direction="income",
        notes=f"{liability.name} 收回",
        account_id=data.account_id,
        liability_id=liability_id,
    )
    db.add(expense)

    await db.commit()
    return {
        "amount": amount,
        "remaining": float(liability.balance),
    }


@router.get("", response_model=list[LiabilityOut])
async def list_liabilities(
    type: str | None = None,
    direction: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Liability).order_by(Liability.type, Liability.created_at)
    if type:
        stmt = stmt.where(Liability.type == type)
    if direction:
        stmt = stmt.where(Liability.direction == direction)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=LiabilityOut, status_code=201)
async def create_liability(data: LiabilityCreate, db: AsyncSession = Depends(get_db)):
    liability = Liability(**data.model_dump())
    db.add(liability)
    await db.commit()
    await db.refresh(liability)
    return liability


@router.put("/{liability_id}", response_model=LiabilityOut)
async def update_liability(
    liability_id: str,
    data: LiabilityUpdate,
    db: AsyncSession = Depends(get_db),
):
    liability = await db.get(Liability, liability_id)
    if not liability:
        raise HTTPException(status_code=404, detail="Liability not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(liability, key, value)
    await db.commit()
    await db.refresh(liability)
    return liability


@router.delete("/{liability_id}", status_code=204)
async def delete_liability(liability_id: str, db: AsyncSession = Depends(get_db)):
    liability = await db.get(Liability, liability_id)
    if not liability:
        raise HTTPException(status_code=404, detail="Liability not found")
    await db.delete(liability)
    await db.commit()
