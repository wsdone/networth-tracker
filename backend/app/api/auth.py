import bcrypt
import jwt
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.auth import AuthConfig

router = APIRouter()

TOKEN_EXPIRE_HOURS = 72


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


async def _get_config(db: AsyncSession) -> AuthConfig | None:
    result = await db.execute(select(AuthConfig).limit(1))
    return result.scalar_one_or_none()


async def _ensure_config(db: AsyncSession) -> AuthConfig:
    config = await _get_config(db)
    if not config:
        config = AuthConfig(password_hash="", enabled=False)
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config


class LoginRequest(BaseModel):
    password: str


class SetPasswordRequest(BaseModel):
    password: str
    old_password: str = ""


@router.get("/status")
async def auth_status(db: AsyncSession = Depends(get_db)):
    config = await _get_config(db)
    enabled = config.enabled if config else False
    return {"enabled": enabled}


@router.post("/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    config = await _get_config(db)
    if not config or not config.enabled:
        return {"token": None, "enabled": False}

    if not _verify_password(data.password, config.password_hash):
        raise HTTPException(status_code=401, detail="密码错误")

    payload = {
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, config.secret_key, algorithm="HS256")
    return {"token": token, "enabled": True}


@router.post("/setup")
async def setup_password(data: SetPasswordRequest, db: AsyncSession = Depends(get_db)):
    config = await _ensure_config(db)

    # If password already set, require old password
    if config.enabled and config.password_hash:
        if not data.old_password or not _verify_password(data.old_password, config.password_hash):
            raise HTTPException(status_code=401, detail="原密码错误")

    config.password_hash = _hash_password(data.password)
    config.enabled = True
    await db.commit()
    return {"message": "密码已设置"}


@router.post("/disable")
async def disable_password(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    config = await _get_config(db)
    if not config or not config.enabled:
        return {"message": "密码保护未开启"}

    if not _verify_password(data.password, config.password_hash):
        raise HTTPException(status_code=401, detail="密码错误")

    config.enabled = False
    await db.commit()
    return {"message": "密码保护已关闭"}


@router.post("/verify")
async def verify_token(token: str, db: AsyncSession = Depends(get_db)):
    """Verify a JWT token is valid."""
    config = await _get_config(db)
    if not config or not config.enabled:
        return {"valid": True}
    try:
        jwt.decode(token, config.secret_key, algorithms=["HS256"])
        return {"valid": True}
    except jwt.PyJWTError:
        return {"valid": False}
