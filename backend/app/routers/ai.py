from __future__ import annotations
import threading
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m, schemas as s
from ..ai import registry
from ..db import SessionLocal, get_db
from ..services.storage import storage

router = APIRouter(prefix="/api/ai")
_heavy = threading.Lock()  # one AI job at a time: protects a 16 GB machine


def _run(task_id: str) -> None:
    with SessionLocal() as db:
        t = db.get(m.AITask, task_id)
        if not t or t.status == "cancelled":
            return
        with _heavy:
            db.refresh(t)
            if t.status == "cancelled":
                return
            t.status, t.started_at, t.finished_at, t.error, t.result = "running", datetime.now(timezone.utc), None, None, None
            db.commit()
            try:
                provider = registry.get_provider(t.task_type)
                t.provider, t.model = provider.info.name, provider.options.get("model", provider.info.model_id)
                asset = db.get(m.Asset, t.input.get("asset_id"))
                if not asset or asset.deleted_at:
                    raise RuntimeError("The source asset no longer exists.")
                payload = {**t.input.get("options", {}), "asset_id": asset.id, "image_path": str(storage.path(asset.storage_key))}
                t.result = provider.run(t.task_type, payload)
                t.status = "completed"
            except Exception as e:  # any failure is recorded; project data is untouched
                t.status, t.error = "failed", f"{type(e).__name__}: {e}"
            t.finished_at = datetime.now(timezone.utc)
            db.commit()


@router.get("/providers")
def providers():
    return registry.describe_all()


@router.post("/tasks", response_model=s.TaskOut, status_code=202)
def create_task(body: s.TaskIn, bg: BackgroundTasks, db: Session = Depends(get_db)):
    asset = db.get(m.Asset, body.asset_id)
    if not asset or asset.deleted_at:
        raise HTTPException(404, "Asset not found.")
    t = m.AITask(project_id=asset.project_id, task_type=body.task_type, status="queued",
                 input={"asset_id": asset.id, "options": body.options})
    db.add(t); db.commit()
    bg.add_task(_run, t.id)
    db.refresh(t)
    return t


@router.get("/tasks", response_model=list[s.TaskOut])
def list_tasks(project_id: str = "", db: Session = Depends(get_db)):
    stmt = select(m.AITask).order_by(m.AITask.created_at.desc()).limit(100)
    if project_id:
        stmt = stmt.where(m.AITask.project_id == project_id)
    return list(db.scalars(stmt))


@router.post("/tasks/{tid}/retry", response_model=s.TaskOut, status_code=202)
def retry_task(tid: str, bg: BackgroundTasks, db: Session = Depends(get_db)):
    t = db.get(m.AITask, tid)
    if not t:
        raise HTTPException(404, "Task not found.")
    if t.status not in ("failed", "cancelled"):
        raise HTTPException(409, "Only failed or cancelled tasks can be retried.")
    t.status = "queued"; db.commit()
    bg.add_task(_run, t.id)
    return t


@router.post("/tasks/{tid}/cancel", response_model=s.TaskOut)
def cancel_task(tid: str, db: Session = Depends(get_db)):
    t = db.get(m.AITask, tid)
    if not t:
        raise HTTPException(404, "Task not found.")
    if t.status != "queued":
        raise HTTPException(409, "Only queued tasks can be cancelled (running local inference cannot be interrupted safely).")
    t.status = "cancelled"; db.commit()
    return t
