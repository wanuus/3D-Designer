from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models as m
from ..db import get_db

router = APIRouter(prefix="/api")
DEFAULT_SETTINGS = {"theme": "system", "units": "m", "ceiling_height": 2.7, "wall_thickness": 0.12,
                    "quality": "balanced", "walk_speed": 1.4, "default_ocr_unit": "mm"}


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    return DEFAULT_SETTINGS | {r.key: r.value.get("v") for r in db.scalars(select(m.Setting))}


@router.put("/settings")
def put_settings(body: dict, db: Session = Depends(get_db)):
    for k, v in body.items():
        if k not in DEFAULT_SETTINGS:
            continue
        row = db.get(m.Setting, k)
        if row:
            row.value = {"v": v}
        else:
            db.add(m.Setting(key=k, value={"v": v}))
    db.commit()
    return get_settings(db)


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    counts = dict(db.execute(select(m.Project.status, func.count()).group_by(m.Project.status)).all())
    total = sum(counts.values())
    archived, done = counts.get("Archived", 0), counts.get("Completed", 0)
    pending = db.scalar(select(func.count()).select_from(m.Room).where(m.Room.status == "Not Started")) or 0
    size = db.scalar(select(func.coalesce(func.sum(m.Asset.size_bytes), 0)).where(m.Asset.deleted_at.is_(None))) or 0
    return {"total_projects": total, "active_projects": total - archived - done, "completed_projects": done,
            "archived_projects": archived, "rooms_pending_design": pending, "storage_bytes": int(size)}
