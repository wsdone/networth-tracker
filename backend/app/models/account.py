import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AccountType(str, enum.Enum):
    bank = "bank"
    alipay = "alipay"
    wechat = "wechat"
    broker = "broker"
    overseas_bank = "overseas_bank"
    cash = "cash"
    housing_fund = "housing_fund"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(20))
    institution: Mapped[str | None] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    balance: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    include_in_total: Mapped[bool] = mapped_column(Boolean, default=True)
    group_name: Mapped[str | None] = mapped_column(String(50))
    tags: Mapped[dict | None] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    margin_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    own_capital: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    # Housing fund fields
    monthly_deposit: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)  # 每月到账金额
    monthly_offset_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)  # 月冲金额
    monthly_offset_day: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 月冲日
    offset_target_account_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # 月冲目标账户
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
