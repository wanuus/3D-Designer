from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Literal
from pydantic import BaseModel


class ProviderUnavailable(RuntimeError):
    """Raised with a user-actionable message when a provider cannot run."""


class ProviderInfo(BaseModel):
    name: str
    tasks: list[str]
    execution: Literal["local", "cloud"] = "local"
    model_id: str = ""
    hardware: str = ""
    est_memory_gb: float | None = None
    pricing: str = "free"
    license: str = ""
    notes: str = ""


class AIProvider(ABC):
    info: ProviderInfo

    def __init__(self, **options):
        self.options = options

    @abstractmethod
    def availability(self) -> tuple[bool, str]:
        """(ready, human-readable detail). Must be cheap and never raise."""

    @abstractmethod
    def run(self, task_type: str, payload: dict) -> dict:
        """Run the task for real. Raise ProviderUnavailable (or any error) on failure; never return fabricated data."""

    def describe(self) -> dict:
        ok, detail = self.availability()
        return {**self.info.model_dump(), "model_id": self.options.get("model", self.info.model_id), "available": ok, "detail": detail}
