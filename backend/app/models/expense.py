import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    amount_cny: Mapped[float] = mapped_column(Numeric(18, 2))
    category: Mapped[str] = mapped_column(String(50))
    direction: Mapped[str] = mapped_column(String(10), default="expense")  # expense/income
    subcategory: Mapped[str | None] = mapped_column(String(50))
    account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    liability_id: Mapped[str | None] = mapped_column(ForeignKey("liabilities.id", ondelete="SET NULL"))
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(20))  # wechat/douyin/alipay/manual
    external_id: Mapped[str | None] = mapped_column(String(64), unique=True)  # 外部交易单号去重
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
