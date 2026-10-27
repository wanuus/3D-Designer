from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def new_id() -> str:
    return uuid.uuid4().hex


def now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), index=True)
    client_name: Mapped[str] = mapped_column(String(200), default="")
    client_contact: Mapped[str] = mapped_column(String(300), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(40), default="Draft", index=True)
    wall_thickness: Mapped[float] = mapped_column(Float, default=0.12)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    rooms: Mapped[list["Room"]] = relationship(back_populates="project", cascade="all, delete-orphan", passive_deletes=True, order_by="Room.created_at")
    assets: Mapped[list["Asset"]] = relationship(back_populates="project", cascade="all, delete-orphan", passive_deletes=True)


class Room(Base):
    __tablename__ = "rooms"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    polygon: Mapped[list] = mapped_column(JSON)  # [[x, y], ...] metres, counter-clockwise, apartment coordinates
    ceiling_height: Mapped[float] = mapped_column(Float, default=2.7)
    floor_level: Mapped[float] = mapped_column(Float, default=0.0)
    dimension_source: Mapped[str] = mapped_column(String(20), default="user_defined")  # verified | ai_estimated | user_defined
    status: Mapped[str] = mapped_column(String(30), default="Not Started")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    project: Mapped[Project] = relationship(back_populates="rooms")
    openings: Mapped[list["Opening"]] = relationship(back_populates="room", cascade="all, delete-orphan", passive_deletes=True, order_by="Opening.created_at")


class Opening(Base):
    """Doors, windows and plain openings, positioned along a room-polygon edge."""
    __tablename__ = "openings"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # door | window | opening
    edge_index: Mapped[int] = mapped_column(Integer)
    offset: Mapped[float] = mapped_column(Float)  # metres from edge start to the opening's start
    width: Mapped[float] = mapped_column(Float)
    height: Mapped[float] = mapped_column(Float)
    sill: Mapped[float] = mapped_column(Float, default=0.0)
    is_entrance: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(20), default="user_defined")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    room: Mapped[Room] = relationship(back_populates="openings")


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    room_id: Mapped[Optional[str]] = mapped_column(ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(200))
    storage_key: Mapped[str] = mapped_column(String(300))
    mime: Mapped[str] = mapped_column(String(100), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # trash
    project: Mapped[Project] = relationship(back_populates="assets")


class AITask(Base):
    __tablename__ = "ai_tasks"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    project_id: Mapped[Optional[str]] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    task_type: Mapped[str] = mapped_column(String(60), index=True)
    provider: Mapped[str] = mapped_column(String(60), default="")
    model: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)  # queued|running|completed|failed|cancelled
    input: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)


class FloorPlan(Base):
    """Calibration of the uploaded plan image: ties image pixels to real metres. One per project."""
    __tablename__ = "floor_plans"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), unique=True, index=True)
    asset_id: Mapped[Optional[str]] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
    scale_m_per_px: Mapped[float] = mapped_column(Float)
    ref_p1: Mapped[list] = mapped_column(JSON)
    ref_p2: Mapped[list] = mapped_column(JSON)
    ref_real_m: Mapped[float] = mapped_column(Float)
    image_width: Mapped[int] = mapped_column(Integer)
    image_height: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
