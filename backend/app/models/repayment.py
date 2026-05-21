import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RepaymentPlan(Base):
    __tablename__ = "repayment_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    liability_id: Mapped[str] = mapped_column(String(36), ForeignKey("liabilities.id", ondelete="CASCADE"))
    source_account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"))
    deduction_day: Mapped[int] = mapped_column()
    repayment_type: Mapped[str] = mapped_column(String(20))
    monthly_rate: Mapped[float] = mapped_column(Numeric(12, 10))
    monthly_payment: Mapped[float | None] = mapped_column(Numeric(18, 2))
    monthly_principal: Mapped[float | None] = mapped_column(Numeric(18, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RepaymentItem(Base):
    __tablename__ = "repayment_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("repayment_plans.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date)
    principal: Mapped[float] = mapped_column(Numeric(18, 2))
    interest: Mapped[float] = mapped_column(Numeric(18, 2))
    total: Mapped[float] = mapped_column(Numeric(18, 2))
    status: Mapped[str] = mapped_column(String(10), default="planned")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
