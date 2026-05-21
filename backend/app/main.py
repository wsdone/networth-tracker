import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, async_session
from app.models import Base

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.router import api_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")
