from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models as m, schemas as s
from ..db import get_db
from ..geometry import engine as geo
from ..services.storage import storage

router = APIRouter(prefix="/api")


def get_project(db: Session, pid: str) -> m.Project:
    p = db.get(m.Project, pid)
    if not p:
        raise HTTPException(404, "Project not found.")
    return p


def get_room(db: Session, rid: str) -> m.Room:
    r = db.get(m.Room, rid)
    if not r:
        raise HTTPException(404, "Room not found.")
    return r


def room_out(r: m.Room) -> s.RoomOut:
    out = s.RoomOut.model_validate(r)
    out.area = geo.polygon_area(geo.to_points(r.polygon))
    return out


def project_out(db: Session, p: m.Project) -> s.ProjectOut:
    out = s.ProjectOut.model_validate(p)
    out.room_count = db.scalar(select(func.count()).select_from(m.Room).where(m.Room.project_id == p.id)) or 0
    return out


def _check_status(v: str | None, allowed: list[str], what: str):
    if v is not None and v not in allowed:
        raise HTTPException(422, f"Unknown {what} status '{v}'. Use one of: {', '.join(allowed)}.")


# ---- projects -------------------------------------------------------------
@router.get("/projects", response_model=list[s.ProjectOut])
def list_projects(q: str = "", status: str = "", include_archived: bool = False,
                  sort: str = Query("updated", pattern="^(updated|created|name)$"), db: Session = Depends(get_db)):
    stmt = select(m.Project)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(m.Project.name.ilike(like) | m.Project.client_name.ilike(like))
    if status:
        stmt = stmt.where(m.Project.status == status)
    elif not include_archived:
        stmt = stmt.where(m.Project.status != "Archived")
    order = {"updated": m.Project.updated_at.desc(), "created": m.Project.created_at.desc(), "name": m.Project.name.asc()}[sort]
    return [project_out(db, p) for p in db.scalars(stmt.order_by(order))]


@router.post("/projects", response_model=s.ProjectOut, status_code=201)
def create_project(body: s.ProjectIn, db: Session = Depends(get_db)):
    _check_status(body.status, s.PROJECT_STATUSES, "project")
    p = m.Project(**body.model_dump())
    db.add(p); db.commit()
    return project_out(db, p)


@router.get("/projects/{pid}", response_model=s.ProjectOut)
def read_project(pid: str, db: Session = Depends(get_db)):
    return project_out(db, get_project(db, pid))


@router.patch("/projects/{pid}", response_model=s.ProjectOut)
def update_project(pid: str, body: s.ProjectPatch, db: Session = Depends(get_db)):
    p = get_project(db, pid)
    data = body.model_dump(exclude_unset=True)
    _check_status(data.get("status"), s.PROJECT_STATUSES, "project")
    for k, v in data.items():
        setattr(p, k, v)
    db.commit()
    return project_out(db, p)


@router.post("/projects/{pid}/duplicate", response_model=s.ProjectOut, status_code=201)
def duplicate_project(pid: str, db: Session = Depends(get_db)):
    src = get_project(db, pid)
    dup = m.Project(name=f"{src.name} (copy)", client_name=src.client_name, client_contact=src.client_contact,
                    description=src.description, location=src.location, status="Draft",
                    wall_thickness=src.wall_thickness, notes=src.notes)
    for r in src.rooms:
        nr = m.Room(name=r.name, polygon=r.polygon, ceiling_height=r.ceiling_height, floor_level=r.floor_level,
                    dimension_source=r.dimension_source, status="Not Started", progress=0, notes=r.notes)
        nr.openings = [m.Opening(kind=o.kind, edge_index=o.edge_index, offset=o.offset, width=o.width, height=o.height,
                                 sill=o.sill, is_entrance=o.is_entrance, source=o.source) for o in r.openings]
        dup.rooms.append(nr)
    db.add(dup); db.commit()  # assets are intentionally not copied
    return project_out(db, dup)


@router.delete("/projects/{pid}", status_code=204)
def delete_project(pid: str, db: Session = Depends(get_db)):
    p = get_project(db, pid)
    keys = [a.storage_key for a in p.assets]
    db.delete(p); db.commit()  # DB first: if file removal fails we only leave orphan files, never dangling rows
    for k in keys:
        try:
            storage.delete(k)
        except OSError:
            pass


# ---- rooms ----------------------------------------------------------------
def _validated_polygon(raw) -> list[list[float]]:
    try:
        poly = geo.normalize_ccw(geo.to_points(raw))
        geo.validate_polygon(poly)
    except geo.GeometryError as e:
        raise HTTPException(422, str(e))
    return [list(p) for p in poly]


@router.get("/projects/{pid}/rooms", response_model=list[s.RoomOut])
def list_rooms(pid: str, db: Session = Depends(get_db)):
    return [room_out(r) for r in get_project(db, pid).rooms]


@router.post("/projects/{pid}/rooms", response_model=s.RoomOut, status_code=201)
def create_room(pid: str, body: s.RoomIn, db: Session = Depends(get_db)):
    get_project(db, pid)
    _check_status(body.status, s.ROOM_STATUSES, "room")
    data = body.model_dump()
    data["polygon"] = _validated_polygon(data["polygon"])
    r = m.Room(project_id=pid, **data)
    db.add(r); db.commit()
    return room_out(r)


@router.patch("/rooms/{rid}", response_model=s.RoomOut)
def update_room(rid: str, body: s.RoomPatch, db: Session = Depends(get_db)):
    r = get_room(db, rid)
    data = body.model_dump(exclude_unset=True)
    _check_status(data.get("status"), s.ROOM_STATUSES, "room")
    if "polygon" in data:
        data["polygon"] = _validated_polygon(data["polygon"])
    new_poly = data.get("polygon", r.polygon)
    new_h = data.get("ceiling_height", r.ceiling_height)
    try:  # the existing doors/windows must still fit the edited geometry; otherwise reject, keep old data
        geo.validate_openings(geo.to_points(new_poly), _opening_dicts(r), new_h)
    except geo.GeometryError as e:
        raise HTTPException(422, f"Change rejected, existing doors/windows no longer fit: {e}")
    for k, v in data.items():
        setattr(r, k, v)
    db.commit()
    return room_out(r)


@router.delete("/rooms/{rid}", status_code=204)
def delete_room(rid: str, db: Session = Depends(get_db)):
    db.delete(get_room(db, rid)); db.commit()


# ---- openings -------------------------------------------------------------
def _opening_dicts(r: m.Room, replace: m.Opening | None = None, extra: dict | None = None) -> list[dict]:
    items = [dict(id=o.id, kind=o.kind, edge_index=o.edge_index, offset=o.offset, width=o.width, height=o.height,
                  sill=o.sill, is_entrance=o.is_entrance) for o in r.openings if not (replace and o.id == replace.id)]
    if extra:
        items.append(extra)
    return items


def _validate_openings(r: m.Room, items: list[dict]):
    try:
        geo.validate_openings(geo.to_points(r.polygon), items, r.ceiling_height)
    except geo.GeometryError as e:
        raise HTTPException(422, str(e))


@router.post("/rooms/{rid}/openings", response_model=s.OpeningOut, status_code=201)
def create_opening(rid: str, body: s.OpeningIn, db: Session = Depends(get_db)):
    r = get_room(db, rid)
    _validate_openings(r, _opening_dicts(r, extra=body.model_dump()))
    o = m.Opening(room_id=rid, **body.model_dump())
    db.add(o); db.commit()
    return o


@router.patch("/openings/{oid}", response_model=s.OpeningOut)
def update_opening(oid: str, body: s.OpeningPatch, db: Session = Depends(get_db)):
    o = db.get(m.Opening, oid)
    if not o:
        raise HTTPException(404, "Opening not found.")
    data = body.model_dump(exclude_unset=True)
    merged = dict(id=o.id, kind=o.kind, edge_index=o.edge_index, offset=o.offset, width=o.width, height=o.height,
                  sill=o.sill, is_entrance=o.is_entrance) | data
    _validate_openings(o.room, _opening_dicts(o.room, replace=o, extra=merged))
    for k, v in data.items():
        setattr(o, k, v)
    db.commit()
    return o


@router.delete("/openings/{oid}", status_code=204)
def delete_opening(oid: str, db: Session = Depends(get_db)):
    o = db.get(m.Opening, oid)
    if not o:
        raise HTTPException(404, "Opening not found.")
    db.delete(o); db.commit()


# ---- scene ----------------------------------------------------------------
@router.get("/projects/{pid}/scene")
def project_scene(pid: str, db: Session = Depends(get_db)):
    p = get_project(db, pid)
    rooms = [dict(id=r.id, name=r.name, polygon=r.polygon, ceiling_height=r.ceiling_height, floor_level=r.floor_level,
                  openings=_opening_dicts(r)) for r in p.rooms]
    try:
        scene = geo.build_scene(rooms, p.wall_thickness)
    except geo.GeometryError as e:
        raise HTTPException(422, str(e))
    scene["dimension_sources"] = {r.id: r.dimension_source for r in p.rooms}
    return scene
