import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Numeric, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DailySnapshot(Base):
    __tablename__ = "daily_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    total_assets_cny: Mapped[float] = mapped_column(Numeric(18, 2))
    total_liabilities_cny: Mapped[float] = mapped_column(Numeric(18, 2))
    net_worth_cny: Mapped[float] = mapped_column(Numeric(18, 2))
    daily_pnl_cny: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    breakdown: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
