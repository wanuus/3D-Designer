from __future__ import annotations
from .base import AIProvider, ProviderInfo, ProviderUnavailable


class OpenCVFloorplanProvider(AIProvider):
    info = ProviderInfo(name="opencv_floorplan", tasks=["floorplan_preprocess"], execution="local", model_id="opencv (classical CV)",
                        hardware="Any CPU", est_memory_gb=0.3, license="Apache-2.0",
                        notes="Returns raw line-segment candidates only. Wall/room reconstruction is NOT implemented yet; the designer traces/verifies rooms manually.")

    def availability(self):
        try:
            import cv2  # noqa: F401
            return True, "OpenCV available"
        except ImportError:
            return False, "OpenCV is not installed. Run: pip install opencv-python-headless"

    def run(self, task_type, payload):
        ok, detail = self.availability()
        if not ok:
            raise ProviderUnavailable(detail)
        import cv2, numpy as np
        path = payload["image_path"]
        if path.lower().endswith((".pdf", ".svg", ".dxf")):
            raise ProviderUnavailable("Only raster floor plans (PNG/JPG) can be preprocessed so far. Export your PDF/SVG to PNG first.")
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ProviderUnavailable("The image could not be decoded.")
        h, w = img.shape
        scale = 1600 / max(h, w) if max(h, w) > 1600 else 1.0
        if scale != 1.0:
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        bw = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 10)
        min_len = max(img.shape) // 25
        lines = cv2.HoughLinesP(bw, 1, np.pi / 180, threshold=80, minLineLength=min_len, maxLineGap=8)
        segs = [] if lines is None else [[float(v) / scale for v in l[0]] for l in lines[:2000]]
        horiz = sum(1 for x1, y1, x2, y2 in segs if abs(y2 - y1) < abs(x2 - x1) * 0.1)
        vert = sum(1 for x1, y1, x2, y2 in segs if abs(x2 - x1) < abs(y2 - y1) * 0.1)
        return {"image_size_px": [w, h], "segments_px": segs, "horizontal": horiz, "vertical": vert,
                "scale_m_per_px": None, "needs_calibration": True,
                "note": "Raw line candidates in original pixel coordinates. No physical scale: calibrate against a known dimension before use."}
