"""Maps task -> provider using config/providers.json (re-read on every call, so edits apply without restart)."""
from __future__ import annotations
import json, os
from pathlib import Path
from .. import config
from .providers.base import AIProvider, ProviderUnavailable
from .providers.not_integrated import SAM2Provider, TripoSRProvider
from .providers.ollama_vision import OllamaVisionProvider
from .providers.opencv_floorplan import OpenCVFloorplanProvider
from .providers.paddle_ocr import PaddleOCRProvider

PROVIDER_CLASSES: dict[str, type[AIProvider]] = {c.info.name: c for c in
    (OllamaVisionProvider, OpenCVFloorplanProvider, PaddleOCRProvider, SAM2Provider, TripoSRProvider)}
MODES = ("local-only", "hybrid", "cloud-enabled")


def load_config() -> dict:
    path = Path(os.environ.get("AIS_PROVIDER_CONFIG", config.DEFAULT_PROVIDER_CONFIG))
    return json.loads(path.read_text()) if path.exists() else {"mode": "local-only", "providers": {}, "tasks": {}}


def get_provider(task_type: str) -> AIProvider:
    cfg = load_config()
    task = cfg.get("tasks", {}).get(task_type)
    if not task:
        raise ProviderUnavailable(f"No provider is configured for '{task_type}'. Add it under 'tasks' in config/providers.json.")
    cls = PROVIDER_CLASSES.get(task["provider"])
    if not cls:
        raise ProviderUnavailable(f"Unknown provider '{task['provider']}'. Available: {', '.join(PROVIDER_CLASSES)}.")
    inst = cls(**{**cfg.get("providers", {}).get(task["provider"], {}), **task.get("options", {})})
    if inst.info.execution == "cloud" and cfg.get("mode", "local-only") == "local-only":
        raise ProviderUnavailable("This provider is cloud-based and the app is in local-only mode. Nothing was sent.")
    return inst


def describe_all() -> dict:
    cfg = load_config()
    out = []
    for name, cls in PROVIDER_CLASSES.items():
        opts = cfg.get("providers", {}).get(name, {})
        for t in cfg.get("tasks", {}).values():
            if t["provider"] == name:
                opts = {**opts, **t.get("options", {})}
        out.append(cls(**opts).describe())
    return {"mode": cfg.get("mode", "local-only"),
            "assignments": {k: v["provider"] for k, v in cfg.get("tasks", {}).items()}, "providers": out}
