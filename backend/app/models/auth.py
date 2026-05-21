import uuid
from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuthConfig(Base):
    __tablename__ = "auth_config"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    password_hash: Mapped[str] = mapped_column(String(128))
    enabled: Mapped[bool] = mapped_column(default=False)
    secret_key: Mapped[str] = mapped_column(String(64), default=lambda: str(uuid.uuid4()) + str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
