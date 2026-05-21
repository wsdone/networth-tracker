import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MarketPrice(Base):
    __tablename__ = "market_prices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(100))
    price: Mapped[float] = mapped_column(Numeric(18, 4))
    prev_close: Mapped[float | None] = mapped_column(Numeric(18, 4))
    change: Mapped[float | None] = mapped_column(Numeric(18, 4))
    change_pct: Mapped[float | None] = mapped_column(Numeric(8, 4))
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    source: Mapped[str | None] = mapped_column(String(50))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
