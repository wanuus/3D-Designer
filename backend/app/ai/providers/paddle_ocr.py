from __future__ import annotations
from ...geometry.dimensions import parse_dimension, parse_pair
from .base import AIProvider, ProviderInfo, ProviderUnavailable


class PaddleOCRProvider(AIProvider):
    info = ProviderInfo(name="paddle_ocr", tasks=["floorplan_ocr"], execution="local", model_id="PaddleOCR (PP-OCR)",
                        hardware="CPU on Apple Silicon (PaddlePaddle macOS arm64 wheels) - verify with benchmark",
                        est_memory_gb=1.5, license="Apache-2.0",
                        notes="Optional heavy install: pip install -r backend/requirements-ai.txt")
    _engine = None

    def availability(self):
        try:
            import paddleocr  # noqa: F401
            return True, "PaddleOCR installed (models download on first run, needs internet once)"
        except ImportError:
            return False, "PaddleOCR is not installed. Run: pip install -r backend/requirements-ai.txt"

    def _get(self):
        if PaddleOCRProvider._engine is None:
            from paddleocr import PaddleOCR
            try:
                PaddleOCRProvider._engine = PaddleOCR(use_textline_orientation=True, lang="en")  # 3.x API
            except TypeError:
                PaddleOCRProvider._engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)  # 2.x API
        return PaddleOCRProvider._engine

    def run(self, task_type, payload):
        ok, detail = self.availability()
        if not ok:
            raise ProviderUnavailable(detail)
        eng, path = self._get(), payload["image_path"]
        items = []
        if hasattr(eng, "predict"):
            for res in eng.predict(path):
                d = res if isinstance(res, dict) else res.json.get("res", res)
                for t, sc, poly in zip(d.get("rec_texts", []), d.get("rec_scores", []), d.get("rec_polys", d.get("dt_polys", []))):
                    items.append((t, float(sc), [[float(x), float(y)] for x, y in poly]))
        else:
            for page in eng.ocr(path, cls=True) or []:
                for box, (t, sc) in page or []:
                    items.append((t, float(sc), [[float(x), float(y)] for x, y in box]))
        unit = payload.get("default_unit", "m")
        texts = []
        for t, sc, box in items:
            texts.append({"text": t, "confidence": sc, "box_px": box, "length_m": parse_dimension(t, unit), "pair_m": parse_pair(t, unit)})
        return {"texts": texts, "default_unit": unit, "note": "Parsed lengths are AI-estimated until the designer verifies them."}
