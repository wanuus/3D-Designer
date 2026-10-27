from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import config
from .db import engine
from .models import Base
from .routers import ai, assets, floorplan, misc, projects


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)  # Alembic migrations are a planned follow-up (see docs/14-IMPLEMENTATION-PROGRESS.md)
    yield


app = FastAPI(title="AI Interior Studio", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
for r in (projects.router, assets.router, floorplan.router, ai.router, misc.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"ok": True}
