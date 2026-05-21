import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TransactionType(str, enum.Enum):
    buy = "buy"
    sell = "sell"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    holding_id: Mapped[str] = mapped_column(ForeignKey("holdings.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(10))
    date: Mapped[date] = mapped_column(Date)
    price: Mapped[float] = mapped_column(Numeric(18, 4))
    quantity: Mapped[float] = mapped_column(Numeric(18, 4))
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    fee: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
