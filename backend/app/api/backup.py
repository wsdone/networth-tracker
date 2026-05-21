import os
import shutil
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import FileResponse

from app.config import settings

router = APIRouter()


def _db_path() -> str:
    url = settings.DATABASE_URL
    # sqlite+aiosqlite:///./wallet.db → ./wallet.db
    path = url.split("///")[-1]
    if not os.path.isabs(path):
        from app.database import engine
        # Resolve relative to engine's actual location
        sync_url = str(engine.url)
        path = sync_url.split("///")[-1]
        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)
    return path


@router.get("/backup")
async def backup_db():
    path = _db_path()
    if not os.path.exists(path):
        return {"error": "Database file not found"}
    # Copy to temp file to avoid locking issues
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tmp = f"/tmp/wallet_backup_{ts}.db"
    shutil.copy2(path, tmp)
    return FileResponse(
        tmp,
        media_type="application/octet-stream",
        filename=f"wallet_backup_{ts}.db",
        background=None,
    )


@router.post("/restore")
async def restore_db(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".db"):
        return {"error": "Please upload a .db file"}
    path = _db_path()
    # Backup current db first
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{path}.pre_restore_{ts}"
    shutil.copy2(path, backup)
    # Write uploaded file
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    return {"message": "Database restored. Please restart the server.", "backup": backup}
