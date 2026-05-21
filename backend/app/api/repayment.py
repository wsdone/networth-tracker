import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.account import Account
from app.models.expense import Expense
from app.models.liability import Liability
from app.models.repayment import RepaymentItem, RepaymentPlan
from app.schemas.repayment import (
    RepaymentEntryInput,
    RepaymentPlanCreate,
    RepaymentPlanDetail,
    RepaymentPlanOut,
    RepaymentPlanUpdate,
    RepaymentItemOut,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _next_month(d: date) -> date:
    m = d.month + 1
    y = d.year
    if m > 12:
        m -= 12
        y += 1
    return date(y, m, min(d.day, 28))


def _calibrate(balance: float, entries: list[RepaymentEntryInput], annual_rate: float | None = None) -> dict:
    """Calibrate repayment type and monthly rate from user-entered entries.

    If annual_rate is provided, use it directly (more accurate for complex loans).
    Otherwise, derive monthly_rate from the first entry's interest / balance.
    """
    if not entries:
        raise ValueError("Need at least 1 entry")

    # Monthly rate: prefer user-provided annual rate, else derive from first entry
    if annual_rate and annual_rate > 0:
        monthly_rate = annual_rate / 100 / 12
    else:
        monthly_rate = entries[0].interest / balance if balance > 0 else 0

    totals = [e.principal + e.interest for e in entries]
    principals = [e.principal for e in entries]

    if len(entries) >= 2:
        avg_total = sum(totals) / len(totals)
        avg_principal = sum(principals) / len(principals)

        # Equal payment: total ~constant
        if all(abs(t - avg_total) / max(avg_total, 1) < 0.05 for t in totals):
            return {
                "repayment_type": "equal_payment",
                "monthly_rate": monthly_rate,
                "monthly_payment": round(avg_total, 2),
                "monthly_principal": None,
            }

        # Equal principal: principal ~constant
        if all(abs(p - avg_principal) / max(avg_principal, 1) < 0.05 for p in principals):
            return {
                "repayment_type": "equal_principal",
                "monthly_rate": monthly_rate,
                "monthly_payment": None,
                "monthly_principal": round(avg_principal, 2),
            }

    # Fallback: treat as equal payment using last total
    return {
        "repayment_type": "equal_payment",
        "monthly_rate": monthly_rate,
        "monthly_payment": round(totals[-1], 2),
        "monthly_principal": None,
    }


def _project_items(balance: float, params: dict, deduction_day: int, start_date: date) -> list[dict]:
    """Project all repayment items until balance reaches 0."""
    items = []
    current_balance = balance
    current_date = start_date

    for _ in range(600):
        if current_balance <= 0.01:
            break

        interest = round(current_balance * params["monthly_rate"], 2)

        if params["repayment_type"] == "equal_principal" and params["monthly_principal"]:
            principal = min(params["monthly_principal"], current_balance)
            total = principal + interest
        else:
            total = params.get("monthly_payment") or 0
            principal = total - interest
            if principal > current_balance:
                principal = current_balance
                total = principal + interest
            elif principal <= 0:
                principal = min(current_balance, total * 0.1)
                total = principal + interest

        items.append({
            "date": current_date,
            "principal": round(principal, 2),
            "interest": round(interest, 2),
            "total": round(total, 2),
        })

        current_balance -= principal
        current_date = _next_month(current_date)

    return items


async def _enrich_plan(plan: RepaymentPlan, db: AsyncSession) -> RepaymentPlanOut:
    liability = await db.get(Liability, plan.liability_id)
    account = await db.get(Account, plan.source_account_id)

    next_payment = None
    result = await db.execute(
        select(RepaymentItem)
        .where(RepaymentItem.plan_id == plan.id, RepaymentItem.status == "planned")
        .order_by(RepaymentItem.date)
        .limit(1)
    )
    next_item = result.scalar_one_or_none()
    if next_item:
        next_payment = RepaymentItemOut.model_validate(next_item)

    return RepaymentPlanOut(
        id=plan.id,
        liability_id=plan.liability_id,
        source_account_id=plan.source_account_id,
        deduction_day=plan.deduction_day,
        repayment_type=plan.repayment_type,
        monthly_rate=float(plan.monthly_rate),
        monthly_payment=float(plan.monthly_payment) if plan.monthly_payment else None,
        monthly_principal=float(plan.monthly_principal) if plan.monthly_principal else None,
        is_active=plan.is_active,
        liability_name=liability.name if liability else None,
        source_account_name=account.name if account else None,
        next_payment=next_payment,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.post("", response_model=RepaymentPlanDetail, status_code=201)
async def create_plan(data: RepaymentPlanCreate, db: AsyncSession = Depends(get_db)):
    liability = await db.get(Liability, data.liability_id)
    if not liability:
        raise HTTPException(status_code=404, detail="Liability not found")

    account = await db.get(Account, data.source_account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if not (1 <= data.deduction_day <= 28):
        raise HTTPException(status_code=400, detail="Deduction day must be 1-28")

    if len(data.entries) < 2:
        raise HTTPException(status_code=400, detail="Please enter at least 2 months of data")

    balance = float(liability.balance)

    # Check if plan already exists
    existing = await db.execute(
        select(RepaymentPlan).where(RepaymentPlan.liability_id == data.liability_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Repayment plan already exists for this liability")

    # Calibrate
    params = _calibrate(balance, data.entries, data.annual_interest_rate)

    # First entry date
    year, month = map(int, data.entries[0].month.split("-"))
    start_date = date(year, month, min(data.deduction_day, 28))

    # Create plan
    plan = RepaymentPlan(
        liability_id=data.liability_id,
        source_account_id=data.source_account_id,
        deduction_day=data.deduction_day,
        repayment_type=params["repayment_type"],
        monthly_rate=params["monthly_rate"],
        monthly_payment=params.get("monthly_payment"),
        monthly_principal=params.get("monthly_principal"),
    )
    db.add(plan)
    await db.flush()

    # Project all items
    projected = _project_items(balance, params, data.deduction_day, start_date)

    total_interest = 0.0
    for item_data in projected:
        item = RepaymentItem(
            plan_id=plan.id,
            date=item_data["date"],
            principal=item_data["principal"],
            interest=item_data["interest"],
            total=item_data["total"],
        )
        db.add(item)
        total_interest += item_data["interest"]

    await db.commit()
    await db.refresh(plan)

    plan_out = await _enrich_plan(plan, db)

    items_result = await db.execute(
        select(RepaymentItem)
        .where(RepaymentItem.plan_id == plan.id)
        .order_by(RepaymentItem.date)
    )
    items = [RepaymentItemOut.model_validate(i) for i in items_result.scalars().all()]

    return RepaymentPlanDetail(
        plan=plan_out,
        items=items,
        projected_months=len(items),
        total_interest=round(total_interest, 2),
    )


@router.put("/{plan_id}", response_model=RepaymentPlanDetail)
async def update_plan(plan_id: str, data: RepaymentPlanUpdate, db: AsyncSession = Depends(get_db)):
    plan = await db.get(RepaymentPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    liability = await db.get(Liability, plan.liability_id)
    if not liability:
        raise HTTPException(status_code=404, detail="Liability not found")

    # Update basic fields
    if data.source_account_id:
        account = await db.get(Account, data.source_account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        plan.source_account_id = data.source_account_id

    if data.deduction_day is not None:
        if not (1 <= data.deduction_day <= 28):
            raise HTTPException(status_code=400, detail="Deduction day must be 1-28")
        plan.deduction_day = data.deduction_day

    # Re-calibrate and re-project if entries or rate provided
    if data.entries and len(data.entries) >= 2:
        balance = float(liability.balance)
        params = _calibrate(balance, data.entries, data.annual_interest_rate)
        plan.monthly_rate = params["monthly_rate"]
        plan.repayment_type = params["repayment_type"]
        plan.monthly_payment = params.get("monthly_payment")
        plan.monthly_principal = params.get("monthly_principal")

        # Delete all unpaid items and re-project
        unpaid = await db.execute(
            select(RepaymentItem).where(
                RepaymentItem.plan_id == plan_id,
                RepaymentItem.status == "planned",
            )
        )
        for item in unpaid.scalars().all():
            await db.delete(item)

        # Find start date: next month after the last paid item, or first entry date
        paid_result = await db.execute(
            select(RepaymentItem)
            .where(RepaymentItem.plan_id == plan_id, RepaymentItem.status == "paid")
            .order_by(RepaymentItem.date.desc())
            .limit(1)
        )
        last_paid = paid_result.scalar_one_or_none()
        if last_paid:
            start_date = _next_month(last_paid.date)
        else:
            year, month = map(int, data.entries[0].month.split("-"))
            start_date = date(year, month, min(plan.deduction_day, 28))

        projected = _project_items(balance, params, plan.deduction_day, start_date)
        for item_data in projected:
            item = RepaymentItem(
                plan_id=plan.id,
                date=item_data["date"],
                principal=item_data["principal"],
                interest=item_data["interest"],
                total=item_data["total"],
            )
            db.add(item)

    elif data.annual_interest_rate is not None and data.annual_interest_rate > 0:
        # Rate changed but no new entries: re-project using new rate
        monthly_rate = data.annual_interest_rate / 100 / 12
        plan.monthly_rate = monthly_rate

        # Delete unpaid items
        unpaid = await db.execute(
            select(RepaymentItem).where(
                RepaymentItem.plan_id == plan_id,
                RepaymentItem.status == "planned",
            )
        )
        for item in unpaid.scalars().all():
            await db.delete(item)

        # Find start date from last paid or now
        paid_result = await db.execute(
            select(RepaymentItem)
            .where(RepaymentItem.plan_id == plan_id, RepaymentItem.status == "paid")
            .order_by(RepaymentItem.date.desc())
            .limit(1)
        )
        last_paid = paid_result.scalar_one_or_none()
        if last_paid:
            start_date = _next_month(last_paid.date)
        else:
            today = date.today()
            start_date = date(today.year, today.month, min(plan.deduction_day, 28))

        params = {
            "repayment_type": plan.repayment_type,
            "monthly_rate": monthly_rate,
            "monthly_payment": float(plan.monthly_payment) if plan.monthly_payment else None,
            "monthly_principal": float(plan.monthly_principal) if plan.monthly_principal else None,
        }

        balance = float(liability.balance)
        projected = _project_items(balance, params, plan.deduction_day, start_date)
        for item_data in projected:
            item = RepaymentItem(
                plan_id=plan.id,
                date=item_data["date"],
                principal=item_data["principal"],
                interest=item_data["interest"],
                total=item_data["total"],
            )
            db.add(item)

    await db.commit()
    await db.refresh(plan)

    # Return full detail
    plan_out = await _enrich_plan(plan, db)
    items_result = await db.execute(
        select(RepaymentItem)
        .where(RepaymentItem.plan_id == plan.id)
        .order_by(RepaymentItem.date)
    )
    items = [RepaymentItemOut.model_validate(i) for i in items_result.scalars().all()]
    total_interest = sum(float(i.interest) for i in items if i.status == "planned")

    return RepaymentPlanDetail(
        plan=plan_out,
        items=items,
        projected_months=len([i for i in items if i.status == "planned"]),
        total_interest=round(total_interest, 2),
    )


@router.get("", response_model=list[RepaymentPlanOut])
async def list_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RepaymentPlan).where(RepaymentPlan.is_active == True))
    plans = result.scalars().all()
    return [await _enrich_plan(p, db) for p in plans]


@router.get("/{plan_id}", response_model=RepaymentPlanDetail)
async def get_plan(plan_id: str, db: AsyncSession = Depends(get_db)):
    plan = await db.get(RepaymentPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan_out = await _enrich_plan(plan, db)

    items_result = await db.execute(
        select(RepaymentItem)
        .where(RepaymentItem.plan_id == plan.id)
        .order_by(RepaymentItem.date)
    )
    items = [RepaymentItemOut.model_validate(i) for i in items_result.scalars().all()]

    total_interest = sum(float(i.interest) for i in items if i.status == "planned")

    return RepaymentPlanDetail(
        plan=plan_out,
        items=items,
        projected_months=len([i for i in items if i.status == "planned"]),
        total_interest=round(total_interest, 2),
    )


@router.post("/{plan_id}/execute")
async def execute_payment(plan_id: str, db: AsyncSession = Depends(get_db)):
    plan = await db.get(RepaymentPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Find next unpaid item
    result = await db.execute(
        select(RepaymentItem)
        .where(RepaymentItem.plan_id == plan.id, RepaymentItem.status == "planned")
        .order_by(RepaymentItem.date)
        .limit(1)
    )
    item = result.scalar_one_or_none()
    if not item:
        return {"message": "No pending payments", "executed": False}

    # Check source account balance
    account = await db.get(Account, plan.source_account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Source account not found")

    total = float(item.total)
    if float(account.balance) < total:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance in {account.name}: {float(account.balance):.2f} < {total:.2f}",
        )

    liability = await db.get(Liability, plan.liability_id)

    # Deduct from source account
    account.balance = float(account.balance) - total

    # Reduce liability balance
    if liability:
        liability.balance = float(liability.balance) - float(item.principal)

    # Record interest as expense
    interest_amount = float(item.interest)
    if interest_amount > 0:
        expense = Expense(
            date=item.date,
            amount=interest_amount,
            currency=account.currency,
            amount_cny=interest_amount,
            category="住房",
            subcategory="贷款利息",
            account_id=plan.source_account_id,
            notes=f"{liability.name if liability else '贷款'}利息",
        )
        db.add(expense)

    item.status = "paid"
    await db.commit()

    return {
        "message": "Payment executed",
        "executed": True,
        "principal": float(item.principal),
        "interest": float(item.interest),
        "total": float(item.total),
        "remaining_balance": float(liability.balance) if liability else 0,
    }


@router.post("/check-due")
async def check_due_payments(db: AsyncSession = Depends(get_db)):
    today = date.today()
    result = await db.execute(select(RepaymentPlan).where(RepaymentPlan.is_active == True))
    plans = result.scalars().all()

    executed = []
    skipped = []

    for plan in plans:
        item_result = await db.execute(
            select(RepaymentItem)
            .where(RepaymentItem.plan_id == plan.id, RepaymentItem.status == "planned")
            .order_by(RepaymentItem.date)
            .limit(1)
        )
        item = item_result.scalar_one_or_none()
        if not item:
            continue

        if item.date <= today:
            try:
                # Inline execution logic (can't call route directly)
                account = await db.get(Account, plan.source_account_id)
                liability = await db.get(Liability, plan.liability_id)
                total = float(item.total)

                if account and float(account.balance) >= total:
                    account.balance = float(account.balance) - total
                    if liability:
                        liability.balance = float(liability.balance) - float(item.principal)

                    interest_amount = float(item.interest)
                    if interest_amount > 0:
                        expense = Expense(
                            date=item.date,
                            amount=interest_amount,
                            currency=account.currency,
                            amount_cny=interest_amount,
                            category="住房",
                            subcategory="贷款利息",
                            account_id=plan.source_account_id,
                            notes=f"{liability.name if liability else '贷款'}利息",
                        )
                        db.add(expense)

                    item.status = "paid"
                    executed.append({
                        "plan_id": plan.id,
                        "liability": liability.name if liability else "",
                        "total": total,
                    })
                else:
                    skipped.append({
                        "plan_id": plan.id,
                        "reason": "余额不足",
                    })
            except Exception as e:
                logger.error(f"Failed to execute payment for plan {plan.id}: {e}")
                skipped.append({"plan_id": plan.id, "reason": str(e)})

    if executed:
        await db.commit()

    return {"executed": executed, "skipped": skipped}


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(plan_id: str, db: AsyncSession = Depends(get_db)):
    plan = await db.get(RepaymentPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Delete items first
    items_result = await db.execute(
        select(RepaymentItem).where(RepaymentItem.plan_id == plan_id)
    )
    for item in items_result.scalars().all():
        await db.delete(item)

    await db.delete(plan)
    await db.commit()
