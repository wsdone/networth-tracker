import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.account import Account
from app.models.expense import Expense
from app.models.liability import Liability
from app.services import bill_parser
from app.services.exchange_rate import get_rate

logger = logging.getLogger(__name__)
router = APIRouter()


def _extract_original_id(external_id: str) -> str:
    """Extract original order ID from a refund's external_id.

    Alipay refund format: original_id*refund_suffix
    Douyin/WeChat: refund ID contains original as prefix or is a separate ID.
    """
    if '*' in external_id:
        return external_id.split('*')[0]
    return external_id


@router.post("/bill")
async def import_bill(
    file: UploadFile = File(...),
    source: str = "auto",
    deduct: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Import bill from WeChat/Douyin/Alipay export file."""
    suffix = Path(file.filename or "").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # Auto-detect source
    if source == "auto":
        fname = (file.filename or "").lower()
        if "微信" in fname or "wechat" in fname:
            source = "wechat"
        elif "抖音" in fname or "douyin" in fname or "dy_" in fname:
            source = "douyin"
        elif "支付宝" in fname or "alipay" in fname:
            source = "alipay"
        elif suffix == ".xlsx":
            source = "wechat"
        elif suffix == ".pdf":
            source = "douyin"
        elif suffix == ".csv":
            source = "alipay"
        else:
            source = "wechat"

    # Parse file
    try:
        if source == "wechat":
            records = bill_parser.parse_wechat_xlsx(tmp_path)
        elif source == "douyin":
            records = bill_parser.parse_douyin_pdf(tmp_path)
        elif source == "alipay":
            records = bill_parser.parse_alipay_csv(tmp_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported source: {source}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parse error: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if not records:
        return {"imported": 0, "skipped": 0, "total": 0, "cancelled": 0, "adjusted": 0, "unmatched": []}

    expenses_list = [r for r in records if r.get("direction") != "income"]
    refunds_list = [r for r in records if r.get("direction") == "income"]

    cancelled = 0
    adjusted = 0
    remaining_expenses = list(expenses_list)

    # Process refunds: match by external_id
    for ref in refunds_list:
        ref_amount = ref["amount"]
        ref_ext_id = ref.get("external_id", "")
        original_id = _extract_original_id(ref_ext_id)
        matched = False

        # 1. Match against existing DB expenses by external_id
        if original_id:
            db_exp = await db.execute(
                select(Expense).where(
                    Expense.external_id == original_id,
                    Expense.direction == "expense",
                )
            )
            db_record = db_exp.scalar_one_or_none()
            if db_record:
                if abs(float(db_record.amount_cny) - ref_amount) < 0.01:
                    # Full refund → delete expense
                    if deduct and db_record.account_id:
                        acc = await db.get(Account, db_record.account_id)
                        if acc:
                            acc.balance = float(acc.balance) + ref_amount
                    if deduct and db_record.liability_id:
                        liab = await db.get(Liability, db_record.liability_id)
                        if liab:
                            liab.balance = float(liab.balance) - ref_amount
                    await db.delete(db_record)
                    cancelled += 1
                else:
                    # Partial refund → reduce expense amount
                    new_amount = float(db_record.amount_cny) - ref_amount
                    if deduct and db_record.account_id:
                        acc = await db.get(Account, db_record.account_id)
                        if acc:
                            acc.balance = float(acc.balance) + ref_amount
                    if deduct and db_record.liability_id:
                        liab = await db.get(Liability, db_record.liability_id)
                        if liab:
                            liab.balance = float(liab.balance) - ref_amount
                    db_record.amount = new_amount
                    db_record.amount_cny = new_amount
                    db_record.notes = (db_record.notes or "") + f" (退款{ref_amount})"
                    adjusted += 1
                matched = True

        # 2. Match within same import batch by external_id
        if not matched and original_id:
            for i, exp in enumerate(remaining_expenses):
                if exp.get("external_id") == original_id:
                    if abs(exp["amount"] - ref_amount) < 0.01:
                        remaining_expenses.pop(i)
                        cancelled += 1
                    else:
                        exp["amount"] = exp["amount"] - ref_amount
                        exp["notes"] = (exp.get("notes", "") + f" (退款{ref_amount})")
                        adjusted += 1
                    matched = True
                    break

        # 3. Fallback: match by same source + same amount (from DB)
        if not matched:
            db_exp = await db.execute(
                select(Expense).where(
                    Expense.source == ref.get("source", source),
                    Expense.direction == "expense",
                    Expense.amount_cny == ref_amount,
                ).order_by(Expense.date.desc())
            )
            db_record = db_exp.scalar_one_or_none()
            if db_record:
                if deduct and db_record.account_id:
                    acc = await db.get(Account, db_record.account_id)
                    if acc:
                        acc.balance = float(acc.balance) + ref_amount
                if deduct and db_record.liability_id:
                    liab = await db.get(Liability, db_record.liability_id)
                    if liab:
                        liab.balance = float(liab.balance) - ref_amount
                await db.delete(db_record)
                cancelled += 1
                matched = True

        # 4. Fallback: match by same source + same amount (from batch)
        if not matched:
            for i, exp in enumerate(remaining_expenses):
                if exp.get("source") == ref.get("source", source) and abs(exp["amount"] - ref_amount) < 0.01:
                    remaining_expenses.pop(i)
                    cancelled += 1
                    matched = True
                    break

        # Still unmatched refund → keep as income record
        if not matched:
            remaining_expenses.append(ref)

    # Load accounts and liabilities for payment method matching
    acc_result = await db.execute(select(Account))
    accounts = [
        {"id": a.id, "name": a.name, "type": a.type, "institution": a.institution or ""}
        for a in acc_result.scalars().all()
    ]
    liab_result = await db.execute(select(Liability))
    liabilities = [
        {"id": l.id, "name": l.name, "type": l.type}
        for l in liab_result.scalars().all()
    ]

    imported = 0
    skipped = 0
    unmatched_methods = set()

    for rec in remaining_expenses:
        # Dedup by external_id
        if rec.get("external_id"):
            existing = await db.execute(
                select(Expense).where(Expense.external_id == rec["external_id"])
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

        match = bill_parser.match_pay_method(rec.get("pay_method", ""), accounts, liabilities)
        account_id = None
        liability_id = None
        if match:
            if match["type"] == "account":
                account_id = match["id"]
            elif match["type"] == "liability":
                liability_id = match["id"]
        if not match and rec.get("pay_method"):
            unmatched_methods.add(rec["pay_method"])

        expense = Expense(
            date=rec["date"],
            amount=rec["amount"],
            currency="CNY",
            amount_cny=rec["amount"],
            category=rec["category"],
            direction=rec.get("direction", "expense"),
            notes=rec.get("notes", ""),
            account_id=account_id,
            liability_id=liability_id,
            source=rec.get("source", source),
            external_id=rec.get("external_id"),
        )
        db.add(expense)

        if deduct and account_id:
            acc = await db.get(Account, account_id)
            if acc:
                acc.balance = float(acc.balance) - rec["amount"]
        if deduct and liability_id:
            liab = await db.get(Liability, liability_id)
            if liab:
                liab.balance = float(liab.balance) + rec["amount"]

        imported += 1

    await db.commit()

    return {
        "imported": imported,
        "skipped": skipped,
        "cancelled": cancelled,
        "adjusted": adjusted,
        "total": len(records),
        "unmatched": list(unmatched_methods),
    }
