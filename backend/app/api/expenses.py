from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.expense import Expense
from app.schemas.expense import ExpenseCreate, ExpenseOut, ExpenseUpdate
from app.services.exchange_rate import get_rate

router = APIRouter()


async def _convert_to_cny(amount: float, currency: str, db: AsyncSession) -> float:
    if currency == "CNY":
        return amount
    rate = await get_rate(db, currency, "CNY")
    return amount * rate


@router.get("", response_model=list[ExpenseOut])
async def list_expenses(
    start_date: date | None = None,
    end_date: date | None = None,
    category: str | None = None,
    direction: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Expense).order_by(Expense.date.desc(), Expense.created_at.desc())
    if start_date:
        stmt = stmt.where(Expense.date >= start_date)
    if end_date:
        stmt = stmt.where(Expense.date <= end_date)
    if category:
        stmt = stmt.where(Expense.category == category)
    if direction:
        stmt = stmt.where(Expense.direction == direction)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/summary")
async def expense_summary(
    year: int | None = None,
    month: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    y = year or today.year
    m = month or today.month

    stmt = (
        select(
            Expense.direction,
            Expense.category,
            func.sum(Expense.amount_cny).label("total"),
        )
        .where(
            func.strftime("%Y", Expense.date) == str(y),
            func.strftime("%m", Expense.date) == f"{m:02d}",
        )
        .group_by(Expense.direction, Expense.category)
        .order_by(Expense.direction, func.sum(Expense.amount_cny).desc())
    )
    result = await db.execute(stmt)
    return [
        {"direction": row[0], "category": row[1], "total": float(row[2])}
        for row in result.all()
    ]


@router.get("/stats")
async def expense_stats(
    months: int = 6,
    db: AsyncSession = Depends(get_db),
):
    """Expense statistics: monthly trend, category distribution, daily trend."""
    today = date.today()
    start = date(today.year, today.month, 1)
    for _ in range(months - 1):
        if start.month == 1:
            start = date(start.year - 1, 12, 1)
        else:
            start = date(start.year, start.month - 1, 1)

    # Monthly trend (income vs expense)
    monthly_stmt = (
        select(
            func.strftime("%Y-%m", Expense.date).label("month"),
            Expense.direction,
            func.sum(Expense.amount_cny).label("total"),
            func.count().label("count"),
        )
        .where(Expense.date >= start)
        .group_by(func.strftime("%Y-%m", Expense.date), Expense.direction)
        .order_by(func.strftime("%Y-%m", Expense.date))
    )
    monthly_result = await db.execute(monthly_stmt)
    monthly_raw = monthly_result.all()
    months_map: dict[str, dict] = {}
    for r in monthly_raw:
        m = r[0]
        if m not in months_map:
            months_map[m] = {"month": m, "income": 0, "expense": 0, "count": 0}
        months_map[m][r[1]] = round(float(r[2]), 2)
        months_map[m]["count"] += r[3]
    monthly_trend = list(months_map.values())

    # Category distribution (expense only)
    cat_stmt = (
        select(Expense.category, func.sum(Expense.amount_cny).label("total"))
        .where(Expense.date >= start, Expense.direction == "expense")
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount_cny).desc())
    )
    cat_result = await db.execute(cat_stmt)
    category_dist = [
        {"category": r[0], "total": round(float(r[1]), 2)} for r in cat_result.all()
    ]

    # Income category distribution
    inc_cat_stmt = (
        select(Expense.category, func.sum(Expense.amount_cny).label("total"))
        .where(Expense.date >= start, Expense.direction == "income")
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount_cny).desc())
    )
    inc_cat_result = await db.execute(inc_cat_stmt)
    income_dist = [
        {"category": r[0], "total": round(float(r[1]), 2)} for r in inc_cat_result.all()
    ]

    # Source distribution
    source_stmt = (
        select(
            func.coalesce(Expense.source, "manual").label("source"),
            func.sum(Expense.amount_cny).label("total"),
            func.count().label("count"),
        )
        .where(Expense.date >= start)
        .group_by(func.coalesce(Expense.source, "manual"))
    )
    source_result = await db.execute(source_stmt)
    source_dist = [
        {"source": r[0], "total": round(float(r[1]), 2), "count": r[2]}
        for r in source_result.all()
    ]

    # Current month daily trend
    month_start = date(today.year, today.month, 1)
    daily_stmt = (
        select(
            Expense.date,
            Expense.direction,
            func.sum(Expense.amount_cny).label("total"),
        )
        .where(Expense.date >= month_start)
        .group_by(Expense.date, Expense.direction)
        .order_by(Expense.date)
    )
    daily_result = await db.execute(daily_stmt)
    daily_map: dict[str, dict] = {}
    for r in daily_result.all():
        d = str(r[0])
        if d not in daily_map:
            daily_map[d] = {"date": d, "income": 0, "expense": 0}
        daily_map[d][r[1]] = round(float(r[2]), 2)
    daily_trend = list(daily_map.values())

    # Summary for current month
    exp_summary = (
        await db.execute(
            select(func.sum(Expense.amount_cny), func.count())
            .where(Expense.date >= month_start, Expense.direction == "expense")
        )
    ).one()
    inc_summary = (
        await db.execute(
            select(func.sum(Expense.amount_cny), func.count())
            .where(Expense.date >= month_start, Expense.direction == "income")
        )
    ).one()
    exp_total = float(exp_summary[0] or 0)
    inc_total = float(inc_summary[0] or 0)
    total_count = (exp_summary[1] or 0) + (inc_summary[1] or 0)
    days_so_far = (today - month_start).days + 1

    return {
        "monthly_trend": monthly_trend,
        "category_dist": category_dist,
        "income_dist": income_dist,
        "source_dist": source_dist,
        "daily_trend": daily_trend,
        "summary": {
            "month_expense": round(exp_total, 2),
            "month_income": round(inc_total, 2),
            "month_net": round(inc_total - exp_total, 2),
            "month_count": total_count,
            "daily_avg_expense": round(exp_total / days_so_far, 2) if days_so_far > 0 else 0,
            "top_category": category_dist[0]["category"] if category_dist else None,
        },
    }


@router.post("", response_model=ExpenseOut, status_code=201)
async def create_expense(data: ExpenseCreate, db: AsyncSession = Depends(get_db)):
    amount_cny = await _convert_to_cny(data.amount, data.currency, db)
    expense = Expense(
        date=data.date,
        amount=data.amount,
        currency=data.currency,
        amount_cny=amount_cny,
        category=data.category,
        direction=data.direction,
        subcategory=data.subcategory,
        account_id=data.account_id,
        notes=data.notes,
        source=data.source,
        external_id=data.external_id,
    )
    db.add(expense)
    await db.commit()
    await db.refresh(expense)
    return expense


@router.put("/{expense_id}", response_model=ExpenseOut)
async def update_expense(
    expense_id: str,
    data: ExpenseUpdate,
    db: AsyncSession = Depends(get_db),
):
    expense = await db.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(expense, key, value)
    expense.amount_cny = await _convert_to_cny(float(expense.amount), expense.currency, db)
    await db.commit()
    await db.refresh(expense)
    return expense


@router.delete("/{expense_id}", status_code=204)
async def delete_expense(expense_id: str, db: AsyncSession = Depends(get_db)):
    expense = await db.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    await db.delete(expense)
    await db.commit()
