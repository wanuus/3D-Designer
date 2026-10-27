from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

PROJECT_STATUSES = ["Draft", "Floor Plan Uploaded", "Floor Plan Verified", "Design in Progress", "Ready for 3D Generation",
                    "3D Generated", "Under Client Review", "Revision Requested", "Approved", "Completed", "Archived"]
ROOM_STATUSES = ["Not Started", "In Progress", "Under Review", "Approved", "Completed"]
DimSource = Literal["verified", "ai_estimated", "user_defined"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    client_name: str = Field("", max_length=200)
    client_contact: str = Field("", max_length=300)
    description: str = ""
    location: str = Field("", max_length=300)
    status: str = "Draft"
    wall_thickness: float = Field(0.12, gt=0.02, le=1.0)
    notes: str = ""


class ProjectPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    wall_thickness: Optional[float] = Field(None, gt=0.02, le=1.0)
    notes: Optional[str] = None


class ProjectOut(ORM):
    id: str; name: str; client_name: str; client_contact: str; description: str; location: str
    status: str; wall_thickness: float; notes: str; created_at: datetime; updated_at: datetime
    room_count: int = 0


class RoomIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    polygon: list[tuple[float, float]]
    ceiling_height: float = Field(2.7, gt=1.5, le=10)
    floor_level: float = Field(0.0, ge=-5, le=100)
    dimension_source: DimSource = "user_defined"
    status: str = "Not Started"
    progress: int = Field(0, ge=0, le=100)
    notes: str = ""


class RoomPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    polygon: Optional[list[tuple[float, float]]] = None
    ceiling_height: Optional[float] = Field(None, gt=1.5, le=10)
    floor_level: Optional[float] = Field(None, ge=-5, le=100)
    dimension_source: Optional[DimSource] = None
    status: Optional[str] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    notes: Optional[str] = None


class OpeningIn(BaseModel):
    kind: Literal["door", "window", "opening"]
    edge_index: int = Field(ge=0)
    offset: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    sill: float = Field(0.0, ge=0)
    is_entrance: bool = False
    source: DimSource = "user_defined"


class OpeningPatch(BaseModel):
    kind: Optional[Literal["door", "window", "opening"]] = None
    edge_index: Optional[int] = Field(None, ge=0)
    offset: Optional[float] = Field(None, ge=0)
    width: Optional[float] = Field(None, gt=0)
    height: Optional[float] = Field(None, gt=0)
    sill: Optional[float] = Field(None, ge=0)
    is_entrance: Optional[bool] = None
    source: Optional[DimSource] = None


class OpeningOut(ORM):
    id: str; room_id: str; kind: str; edge_index: int; offset: float; width: float; height: float
    sill: float; is_entrance: bool; source: str


class RoomOut(ORM):
    id: str; project_id: str; name: str; polygon: list; ceiling_height: float; floor_level: float
    dimension_source: str; status: str; progress: int; notes: str
    openings: list[OpeningOut] = []
    area: float = 0.0


class AssetOut(ORM):
    id: str; project_id: str; room_id: Optional[str]; category: str; name: str; mime: str
    size_bytes: int; sha256: str; created_at: datetime; deleted_at: Optional[datetime]


class TaskIn(BaseModel):
    task_type: Literal["floorplan_preprocess", "floorplan_ocr", "reference_analysis", "segmentation", "image_to_3d"]
    asset_id: str
    options: dict = {}


class TaskOut(ORM):
    id: str; project_id: Optional[str]; task_type: str; provider: str; model: str; status: str
    input: dict; result: Optional[dict]; error: Optional[str]
    created_at: datetime; started_at: Optional[datetime]; finished_at: Optional[datetime]
