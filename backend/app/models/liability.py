import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LiabilityType(str, enum.Enum):
    mortgage = "mortgage"
    personal_loan = "personal_loan"
    credit_card = "credit_card"
    other_loan = "other_loan"


class Direction(str, enum.Enum):
    owe = "owe"
    lent = "lent"


class Liability(Base):
    __tablename__ = "liabilities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(100))
    counterparty: Mapped[str | None] = mapped_column(String(100))
    balance: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    interest_rate: Mapped[float | None] = mapped_column(Numeric(6, 4))
    monthly_payment: Mapped[float | None] = mapped_column(Numeric(18, 2))
    direction: Mapped[str] = mapped_column(String(10), default="owe")
    include_in_total: Mapped[bool] = mapped_column(Boolean, default=True)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
