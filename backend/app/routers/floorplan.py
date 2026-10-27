from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m, schemas as s
from ..db import get_db
from ..geometry import calibration as cal, engine as geo
from .projects import get_project, project_out, room_out

router = APIRouter(prefix="/api")


class CalibrationIn(BaseModel):
    asset_id: Optional[str] = None
    p1: tuple[float, float]
    p2: tuple[float, float]
    real_distance_m: float = Field(gt=0, le=500)
    image_width: int = Field(gt=0, le=100000)
    image_height: int = Field(gt=0, le=100000)


class FloorPlanOut(s.ORM):
    id: str; project_id: str; asset_id: Optional[str]; scale_m_per_px: float
    ref_p1: list; ref_p2: list; ref_real_m: float; image_width: int; image_height: int


class TraceIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    points_px: list[tuple[float, float]]
    ceiling_height: float = Field(2.7, gt=1.5, le=10)
    snap_tolerance_m: float = Field(0.05, ge=0, le=0.3)
    grid_m: float = Field(0.01, ge=0, le=0.5)


def _plan(db: Session, pid: str) -> m.FloorPlan | None:
    return db.scalar(select(m.FloorPlan).where(m.FloorPlan.project_id == pid))


@router.get("/projects/{pid}/floorplan", response_model=Optional[FloorPlanOut])
def get_floorplan(pid: str, db: Session = Depends(get_db)):
    get_project(db, pid)
    return _plan(db, pid)


@router.put("/projects/{pid}/floorplan", response_model=FloorPlanOut)
def calibrate(pid: str, body: CalibrationIn, db: Session = Depends(get_db)):
    p = get_project(db, pid)
    if body.asset_id:
        a = db.get(m.Asset, body.asset_id)
        if not a or a.project_id != pid or a.category != "floor_plan":
            raise HTTPException(422, "The selected file is not a floor plan of this project.")
    try:
        scale = cal.scale_from_reference(body.p1, body.p2, body.real_distance_m)
    except cal.CalibrationError as e:
        raise HTTPException(422, str(e))
    fp = _plan(db, pid) or m.FloorPlan(project_id=pid)
    fp.asset_id, fp.scale_m_per_px = body.asset_id, scale
    fp.ref_p1, fp.ref_p2, fp.ref_real_m = list(body.p1), list(body.p2), body.real_distance_m
    fp.image_width, fp.image_height = body.image_width, body.image_height
    db.add(fp)
    if p.status == "Draft":
        p.status = "Floor Plan Uploaded"
    db.commit()
    return fp


@router.post("/projects/{pid}/floorplan/trace-room", response_model=s.RoomOut, status_code=201)
def trace_room(pid: str, body: TraceIn, db: Session = Depends(get_db)):
    """Create a room from corners clicked on the calibrated plan. Pixels -> metres uses ONLY the designer's calibration."""
    get_project(db, pid)
    fp = _plan(db, pid)
    if not fp:
        raise HTTPException(409, "Calibrate the floor plan scale first.")
    try:
        pts = cal.px_to_m(body.points_px, fp.scale_m_per_px)
        pts = cal.round_to_grid(cal.snap_coordinates(pts, body.snap_tolerance_m), body.grid_m)
        pts = geo.normalize_ccw(pts)
        geo.validate_polygon(pts)
    except geo.GeometryError as e:
        raise HTTPException(422, f"{e} If corners were merged by snapping, lower the snap tolerance.")
    r = m.Room(project_id=pid, name=body.name, polygon=[list(p) for p in pts], ceiling_height=body.ceiling_height,
               dimension_source="user_defined")
    db.add(r); db.commit()
    return room_out(r)


@router.post("/projects/{pid}/verify-floorplan", response_model=s.ProjectOut)
def verify_floorplan(pid: str, db: Session = Depends(get_db)):
    """The designer confirms every room's measurements. Only this action marks geometry verified."""
    p = get_project(db, pid)
    if not p.rooms:
        raise HTTPException(409, "Add at least one room before verifying the floor plan.")
    for r in p.rooms:
        r.dimension_source = "verified"
    p.status = "Floor Plan Verified"
    db.commit()
    return project_out(db, p)
