"""Storage abstraction. LocalStorage writes under data/assets; a cloud object store can
implement the same interface later without touching routers."""
from __future__ import annotations
import hashlib, os, re, uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

from .. import config

ALLOWED_EXT = {
    "floor_plan": {".png", ".jpg", ".jpeg", ".pdf", ".svg", ".dxf"},
    "room_reference": {".png", ".jpg", ".jpeg", ".webp"},
    "furniture_reference": {".png", ".jpg", ".jpeg", ".webp"},
    "material_texture": {".png", ".jpg", ".jpeg", ".webp"},
    "model_3d": {".glb", ".gltf"},
    "render_image": {".png", ".jpg", ".jpeg"},
    "walkthrough_video": {".mp4"},
}
CATEGORIES = sorted(ALLOWED_EXT)
_MAGIC = {".png": b"\x89PNG\r\n\x1a\n", ".jpg": b"\xff\xd8\xff", ".jpeg": b"\xff\xd8\xff",
          ".pdf": b"%PDF", ".webp": b"RIFF", ".glb": b"glTF"}
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".pdf": "application/pdf",
        ".svg": "image/svg+xml", ".dxf": "application/dxf", ".glb": "model/gltf-binary", ".gltf": "model/gltf+json", ".mp4": "video/mp4"}


class StorageError(ValueError):
    pass


def safe_display_name(name: str) -> str:
    base = os.path.basename((name or "file").replace("\\", "/"))
    base = re.sub(r"[\x00-\x1f<>:\"|?*]", "_", base).strip(". ") or "file"
    return base[:120]


class Storage(ABC):
    @abstractmethod
    def save(self, fileobj: BinaryIO, category: str, filename: str, max_bytes: int) -> tuple[str, int, str]: ...
    @abstractmethod
    def path(self, key: str) -> Path: ...
    @abstractmethod
    def delete(self, key: str) -> None: ...


class LocalStorage(Storage):
    def __init__(self, root: Path):
        self.root = root.resolve()

    def save(self, fileobj, category, filename, max_bytes):
        if category not in ALLOWED_EXT:
            raise StorageError(f"Unknown asset category '{category}'.")
        ext = Path(filename or "").suffix.lower()
        if ext not in ALLOWED_EXT[category]:
            raise StorageError(f"{ext or 'This file type'} is not allowed for {category}. Allowed: {', '.join(sorted(ALLOWED_EXT[category]))}.")
        key = f"{category}/{uuid.uuid4().hex}{ext}"
        dest = self.path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        h, size, head = hashlib.sha256(), 0, b""
        try:
            with open(dest, "wb") as out:
                while chunk := fileobj.read(1024 * 1024):
                    if not head:
                        head = chunk[:2048]
                    size += len(chunk)
                    if size > max_bytes:
                        raise StorageError(f"File is larger than the {max_bytes // (1024 * 1024)} MB limit.")
                    h.update(chunk); out.write(chunk)
            if size == 0:
                raise StorageError("File is empty.")
            self._sniff(ext, head)
        except Exception:
            dest.unlink(missing_ok=True)
            raise
        return key, size, h.hexdigest()

    @staticmethod
    def _sniff(ext: str, head: bytes) -> None:
        if ext in _MAGIC and not head.startswith(_MAGIC[ext]):
            raise StorageError(f"File content does not look like a real {ext} file.")
        if ext == ".svg" and b"<svg" not in head.lower():
            raise StorageError("File content does not look like an SVG.")
        if ext == ".mp4" and head[4:8] != b"ftyp":
            raise StorageError("File content does not look like an MP4 video.")

    def path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if self.root != p and self.root not in p.parents:
            raise StorageError("Invalid storage key.")
        return p

    def delete(self, key: str) -> None:
        self.path(key).unlink(missing_ok=True)


storage: Storage = LocalStorage(config.ASSET_DIR)
