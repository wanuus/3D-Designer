#!/usr/bin/env python3
"""Real, minimal inference benchmark for each configured local model.

Run on the target machine (MacBook Air M2):
    cd backend && source .venv/bin/activate
    python ../scripts/benchmark_models.py --room-photo ~/Pictures/some_bedroom.jpg --floor-plan ~/plans/apt.png

Models run strictly one at a time. Nothing is mocked: a model that is missing or fails is reported as such.
Results go to benchmarks/results.json and into docs/AI-MODEL-BENCHMARKS.md (between the RESULTS markers).
"""
from __future__ import annotations
import argparse, json, platform, subprocess, sys, tempfile, threading, time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import psutil  # noqa: E402


class MemSampler:
    """Samples system-wide used memory (covers Ollama's separate process)."""
    def __init__(self):
        self.base = psutil.virtual_memory().used; self.peak = self.base; self._stop = threading.Event()
    def __enter__(self):
        def loop():
            while not self._stop.is_set():
                self.peak = max(self.peak, psutil.virtual_memory().used); time.sleep(0.25)
        self.t = threading.Thread(target=loop, daemon=True); self.t.start(); return self
    def __exit__(self, *a):
        self._stop.set(); self.t.join(); self.peak = max(self.peak, psutil.virtual_memory().used)
    @property
    def delta_gb(self): return round((self.peak - self.base) / 1e9, 2)


def synthetic_plan(path: Path) -> None:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (1200, 900), "white"); d = ImageDraw.Draw(img)
    d.rectangle([100, 100, 700, 500], outline="black", width=8); d.rectangle([700, 100, 1100, 500], outline="black", width=8)
    d.rectangle([100, 500, 1100, 800], outline="black", width=8)
    for txt, xy in [("BEDROOM 3.00 m x 4.00 m", (150, 280)), ("KITCHEN 4000 x 2500 mm", (730, 280)), ("LIVING 12.0 x 3.0 m", (400, 640))]:
        d.text(xy, txt, fill="black")
    img.save(path)


def timed(name: str, fn, results: dict, note: str = ""):
    rec = {"model": name, "status": "ok", "note": note}
    try:
        with MemSampler() as ms:
            t0 = time.perf_counter(); out = fn(); rec["seconds"] = round(time.perf_counter() - t0, 2)
        rec["peak_extra_memory_gb"] = ms.delta_gb; rec["output_preview"] = json.dumps(out, default=str)[:600]
    except Exception as e:
        rec.update(status="failed", error=f"{type(e).__name__}: {str(e)[:400]}")
    results[name] = rec; print(f"[{rec['status']}] {name}: {rec.get('seconds', '-')}s, +{rec.get('peak_extra_memory_gb', '-')} GB"); return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--room-photo", help="a real photo of a furnished room (needed for the vision benchmark)")
    ap.add_argument("--floor-plan", help="a real floor-plan PNG/JPG (a synthetic one is used if omitted)")
    ap.add_argument("--vision-model", default="qwen2.5vl:3b")
    a = ap.parse_args()
    from app.ai.providers.ollama_vision import OllamaVisionProvider
    from app.ai.providers.opencv_floorplan import OpenCVFloorplanProvider
    from app.ai.providers.paddle_ocr import PaddleOCRProvider
    from app.ai.providers.not_integrated import SAM2Provider, TripoSRProvider

    tmp = Path(tempfile.mkdtemp()); plan = Path(a.floor_plan) if a.floor_plan else tmp / "synthetic_plan.png"
    if not a.floor_plan: synthetic_plan(plan)
    plan_kind = "real floor plan" if a.floor_plan else "SYNTHETIC floor plan (quality figures are not representative)"
    results: dict = {}
    env = {"date": datetime.now().isoformat(timespec="seconds"), "machine": platform.platform(), "processor": platform.processor(),
           "ram_gb": round(psutil.virtual_memory().total / 1e9, 1), "python": platform.python_version()}

    p = OpenCVFloorplanProvider(); ok, d = p.availability()
    if ok: timed("opencv_floorplan", lambda: {k: v for k, v in p.run("floorplan_preprocess", {"image_path": str(plan)}).items() if k != "segments_px"}, results, plan_kind)
    else: results["opencv_floorplan"] = {"model": "opencv_floorplan", "status": "unavailable", "note": d}

    p = PaddleOCRProvider(); ok, d = p.availability()
    if ok:
        timed("paddle_ocr (first run, includes model download/load)", lambda: p.run("floorplan_ocr", {"image_path": str(plan), "default_unit": "mm"}), results, plan_kind)
        timed("paddle_ocr (warm)", lambda: p.run("floorplan_ocr", {"image_path": str(plan), "default_unit": "mm"}), results, plan_kind)
    else: results["paddle_ocr"] = {"model": "paddle_ocr", "status": "unavailable", "note": d}

    p = OllamaVisionProvider(model=a.vision_model); ok, d = p.availability()
    if not a.room_photo: results["ollama_vision"] = {"model": a.vision_model, "status": "skipped", "note": "No --room-photo given; a floor plan is not a valid test of room-photo analysis."}
    elif not ok: results["ollama_vision"] = {"model": a.vision_model, "status": "unavailable", "note": d}
    else:
        timed(f"ollama_vision ({a.vision_model}, cold)", lambda: p.run("reference_analysis", {"image_path": a.room_photo}), results, "Judge output quality by reading output_preview vs. your photo.")
        timed(f"ollama_vision ({a.vision_model}, warm)", lambda: p.run("reference_analysis", {"image_path": a.room_photo}), results)
        subprocess.run(["ollama", "stop", a.vision_model], capture_output=True)

    for prov in (SAM2Provider(), TripoSRProvider()):
        ok, d = prov.availability(); results[prov.info.name] = {"model": prov.info.model_id, "status": "not integrated", "note": d}

    (ROOT / "benchmarks").mkdir(exist_ok=True)
    (ROOT / "benchmarks" / "results.json").write_text(json.dumps({"env": env, "results": results}, indent=2))
    rows = "\n".join(f"| {k} | {v['status']} | {v.get('seconds', '-')} | {v.get('peak_extra_memory_gb', '-')} | {(v.get('note') or v.get('error') or '').replace('|', '/')[:160]} |" for k, v in results.items())
    block = (f"Measured {env['date']} on {env['machine']} ({env['ram_gb']} GB RAM, Python {env['python']}).\n\n"
             "| Test | Status | Seconds | Peak extra RAM (GB) | Notes |\n|---|---|---|---|---|\n" + rows + "\n")
    doc = ROOT / "docs" / "AI-MODEL-BENCHMARKS.md"; txt = doc.read_text()
    s, e = "<!-- RESULTS:START -->", "<!-- RESULTS:END -->"
    doc.write_text(txt.split(s)[0] + s + "\n" + block + e + txt.split(e)[1]); print(f"\nWrote {doc} and benchmarks/results.json")


if __name__ == "__main__":
    main()
