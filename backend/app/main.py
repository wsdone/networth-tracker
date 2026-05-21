import asyncio
import logging
from contextlib import asynccontextmanager

import jwt
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.config import settings
from app.database import engine, async_session
from app.models import Base
from app.models.auth import AuthConfig

logger = logging.getLogger(__name__)


async def _create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _startup_snapshot():
    """Generate daily snapshot on startup."""
    try:
        async with async_session() as db:
            from app.services.snapshot import generate_daily_snapshot
            await generate_daily_snapshot(db)
            await db.commit()
            logger.info("Startup snapshot generated")
    except Exception as e:
        logger.warning(f"Startup snapshot failed: {e}")


async def _daily_snapshot_loop():
    """Generate snapshot every day at 00:30."""
    while True:
        now = asyncio.get_event_loop().time()
        import datetime
        t = datetime.datetime.now()
        # Sleep until next 00:30
        target = t.replace(hour=0, minute=30, second=0, microsecond=0)
        if t >= target:
            target = target.replace(day=t.day + 1)
        delay = (target - t).total_seconds()
        await asyncio.sleep(delay)
        try:
            async with async_session() as db:
                from app.services.snapshot import generate_daily_snapshot
                await generate_daily_snapshot(db)
                await db.commit()
                logger.info("Daily snapshot generated")
        except Exception as e:
            logger.warning(f"Daily snapshot failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _create_tables()
    # Generate snapshot on startup and schedule daily
    asyncio.create_task(_startup_snapshot())
    asyncio.create_task(_daily_snapshot_loop())
    yield


app = FastAPI(title="Wallet API", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    # Skip auth for non-API paths, auth endpoints, and docs
    if not path.startswith("/api/v1/") or path.startswith("/api/v1/auth/"):
        return await call_next(request)

    # Check if password protection is enabled
    try:
        async with async_session() as db:
            result = await db.execute(select(AuthConfig).limit(1))
            config = result.scalar_one_or_none()
            if not config or not config.enabled:
                return await call_next(request)
            secret_key = config.secret_key
    except Exception:
        return await call_next(request)

    # Verify JWT token
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""
    if not token:
        return JSONResponse(status_code=401, content={"detail": "请先登录"})
    try:
        jwt.decode(token, secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return JSONResponse(status_code=401, content={"detail": "登录已过期，请重新登录"})

    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.router import api_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")
