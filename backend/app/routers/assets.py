from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import config, models as m, schemas as s
from ..db import get_db
from ..services.storage import CATEGORIES, MIME, StorageError, safe_display_name, storage
from .projects import get_project

router = APIRouter(prefix="/api")


@router.get("/asset-categories")
def categories():
    return CATEGORIES


@router.post("/projects/{pid}/assets", response_model=s.AssetOut, status_code=201)
def upload_asset(pid: str, category: str = Form(...), room_id: Optional[str] = Form(None),
                 file: UploadFile = File(...), db: Session = Depends(get_db)):
    p = get_project(db, pid)
    if room_id and not db.get(m.Room, room_id):
        raise HTTPException(404, "Room not found.")
    try:
        key, size, digest = storage.save(file.file, category, file.filename or "", config.MAX_UPLOAD_MB * 1024 * 1024)
    except StorageError as e:
        raise HTTPException(422, str(e))
    ext = "." + key.rsplit(".", 1)[-1]
    a = m.Asset(project_id=pid, room_id=room_id or None, category=category, name=safe_display_name(file.filename or ""),
                storage_key=key, mime=MIME.get(ext, "application/octet-stream"), size_bytes=size, sha256=digest)
    db.add(a)
    if category == "floor_plan" and p.status == "Draft":
        p.status = "Floor Plan Uploaded"
    db.commit()
    return a


@router.get("/projects/{pid}/assets", response_model=list[s.AssetOut])
def list_assets(pid: str, category: str = "", include_deleted: bool = False, db: Session = Depends(get_db)):
    get_project(db, pid)
    stmt = select(m.Asset).where(m.Asset.project_id == pid)
    if category:
        stmt = stmt.where(m.Asset.category == category)
    if not include_deleted:
        stmt = stmt.where(m.Asset.deleted_at.is_(None))
    return list(db.scalars(stmt.order_by(m.Asset.created_at.desc())))


def _asset(db: Session, aid: str) -> m.Asset:
    a = db.get(m.Asset, aid)
    if not a:
        raise HTTPException(404, "Asset not found.")
    return a


@router.get("/assets/{aid}/file")
def asset_file(aid: str, db: Session = Depends(get_db)):
    a = _asset(db, aid)
    path = storage.path(a.storage_key)
    if not path.exists():
        raise HTTPException(410, "The file for this asset has been removed from disk.")
    return FileResponse(path, media_type=a.mime, filename=a.name)


@router.delete("/assets/{aid}", status_code=204)
def delete_asset(aid: str, permanent: bool = False, db: Session = Depends(get_db)):
    """Default: move to trash (recoverable). permanent=true removes row and file."""
    a = _asset(db, aid)
    if not permanent:
        a.deleted_at = datetime.now(timezone.utc)
        db.commit(); return
    key = a.storage_key
    db.delete(a); db.commit()
    storage.delete(key)


@router.post("/assets/{aid}/restore", response_model=s.AssetOut)
def restore_asset(aid: str, db: Session = Depends(get_db)):
    a = _asset(db, aid)
    a.deleted_at = None
    db.commit()
    return a


@router.get("/storage/usage")
def storage_usage(db: Session = Depends(get_db)):
    rows = db.execute(select(m.Asset.category, m.Asset.deleted_at.is_(None), func.coalesce(func.sum(m.Asset.size_bytes), 0))
                      .group_by(m.Asset.category, m.Asset.deleted_at.is_(None))).all()
    by_cat: dict[str, int] = {}
    trash = 0
    for cat, active, size in rows:
        if active:
            by_cat[cat] = by_cat.get(cat, 0) + int(size)
        else:
            trash += int(size)
    return {"by_category": by_cat, "active_bytes": sum(by_cat.values()), "trash_bytes": trash}
