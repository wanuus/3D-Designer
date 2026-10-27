from __future__ import annotations
import importlib.util
from .base import AIProvider, ProviderInfo, ProviderUnavailable


class _NotIntegrated(AIProvider):
    module = ""
    install = ""

    def availability(self):
        found = importlib.util.find_spec(self.module) is not None if self.module else False
        if not found:
            return False, f"Not installed. {self.install}"
        return False, "Package found, but the application adapter is not written yet (planned phase). Nothing is mocked."

    def run(self, task_type, payload):
        raise ProviderUnavailable(self.availability()[1])


class SAM2Provider(_NotIntegrated):
    module, install = "sam2", "See docs/AI-MODEL-BENCHMARKS.md - evaluate the tiny checkpoint first."
    info = ProviderInfo(name="sam2", tasks=["segmentation"], model_id="SAM 2 (tiny/small checkpoint)", hardware="PyTorch MPS or CPU",
                        est_memory_gb=2.0, license="Apache-2.0 (verify)", notes="Planned; not integrated.")


class TripoSRProvider(_NotIntegrated):
    module, install = "tsr", "See docs/AI-MODEL-BENCHMARKS.md - experimental; may need CPU fallback on Apple Silicon."
    info = ProviderInfo(name="triposr", tasks=["image_to_3d"], model_id="TripoSR", hardware="PyTorch; MPS support unverified",
                        est_memory_gb=6.0, license="MIT (verify)", notes="Experimental; planned; not integrated.")
