import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AssetType(str, enum.Enum):
    stock = "stock"
    fund = "fund"
    bond = "bond"
    etf = "etf"
    money_fund = "money_fund"
    futures = "futures"


class Exchange(str, enum.Enum):
    SSE = "SSE"
    SZSE = "SZSE"
    HKSE = "HKSE"
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    OTC = "OTC"
    SHFE = "SHFE"
    DCE = "DCE"
    CZCE = "CZCE"
    CFFEX = "CFFEX"
    INE = "INE"
    GFEX = "GFEX"


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    symbol: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(100))
    asset_type: Mapped[str] = mapped_column(String(20))
    exchange: Mapped[str | None] = mapped_column(String(20))
    quantity: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    cost_price: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    include_in_total: Mapped[bool] = mapped_column(Boolean, default=True)
    group_name: Mapped[str | None] = mapped_column(String(50))
    tags: Mapped[dict | None] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text)
    margin_liability_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    multiplier: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    margin_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
