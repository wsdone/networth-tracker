from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.snapshot import DailySnapshot
from app.services.snapshot import generate_daily_snapshot

router = APIRouter()


@router.get("")
async def list_snapshots(
    limit: int = 90,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DailySnapshot).order_by(DailySnapshot.date.desc()).limit(limit)
    )
    snapshots = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "date": s.date.isoformat(),
            "total_assets_cny": float(s.total_assets_cny),
            "total_liabilities_cny": float(s.total_liabilities_cny),
            "net_worth_cny": float(s.net_worth_cny),
            "daily_pnl_cny": float(s.daily_pnl_cny),
            "breakdown": s.breakdown,
            "created_at": s.created_at.isoformat(),
        }
        for s in snapshots
    ]


@router.post("/generate")
async def create_snapshot(db: AsyncSession = Depends(get_db)):
    snapshot = await generate_daily_snapshot(db)
    return {
        "id": str(snapshot.id),
        "date": snapshot.date.isoformat(),
        "total_assets_cny": float(snapshot.total_assets_cny),
        "total_liabilities_cny": float(snapshot.total_liabilities_cny),
        "net_worth_cny": float(snapshot.net_worth_cny),
        "daily_pnl_cny": float(snapshot.daily_pnl_cny),
    }
