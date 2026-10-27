from __future__ import annotations
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    return Path(os.environ.get("AIS_DATA_DIR", ROOT / "data")).resolve()


DATA_DIR = data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)
ASSET_DIR = DATA_DIR / "assets"
ASSET_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.environ.get("AIS_DATABASE_URL", f"sqlite:///{DATA_DIR / 'studio.db'}")
MAX_UPLOAD_MB = int(os.environ.get("AIS_MAX_UPLOAD_MB", "200"))
CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
DEFAULT_PROVIDER_CONFIG = ROOT / "config" / "providers.json"
