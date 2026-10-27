# AI Model Benchmarks and Selection

> **Status: selection decisions below are provisional. No model has been benchmarked on the target
> MacBook Air M2 yet.** The sandbox this project was written in has no network access, Apple Silicon, or GPU,
> so no performance number in this file was invented. The "Measured results" section is filled automatically
> by `scripts/benchmark_models.py` when you run it on your Mac. Until then it says "not yet measured".

## How to produce real numbers

```bash
cd backend && source .venv/bin/activate
python ../scripts/benchmark_models.py --room-photo /path/to/real_bedroom_photo.jpg --floor-plan /path/to/real_plan.png
```
Models run one at a time. Peak memory is the system-wide increase in used RAM during the run (this includes the
separate Ollama process). A missing model is reported as unavailable, never as a fake success.

## Measured results

<!-- RESULTS:START -->
Not yet measured. Run the benchmark script above.
<!-- RESULTS:END -->

## Selection decisions (from prior knowledge; each item must be verified on first install)

| Task | Preferred | Runs through | Known concerns | Fallback if unsuitable |
|---|---|---|---|---|
| Floor-plan preprocessing | OpenCV | CPU | Gives line candidates only; wall/room reconstruction is not built yet. | Manual tracing in the editor (always available). |
| Dimension OCR | PaddleOCR | PaddlePaddle CPU | Large dependency; API differs between 2.x and 3.x (adapter handles both); first run downloads models. | Apple Vision OCR via a small Swift/pyobjc helper, or Tesseract (`brew install tesseract`); or type dimensions manually. |
| Reference-image understanding | Qwen2.5-VL 3B via Ollama | Ollama (Metal) | **License:** the 3B checkpoint is released under the Qwen Research License, not Apache-2.0, which may restrict commercial use. Confirm on the model card before using it for paid client work. | Qwen2.5-VL 7B (Apache-2.0 per my recollection; verify) is heavier (~6 GB class) but fits in 16 GB when run alone; or `llava`/`moondream` for lighter use. |
| Segmentation | SAM 2 (tiny/small checkpoint) | PyTorch MPS/CPU | Not integrated yet. MPS operator coverage should be tested. | Classical OpenCV segmentation or manual region selection. |
| Image-to-3D | TripoSR (experimental) | PyTorch | Not integrated yet. Native extension builds (e.g. marching cubes) can fail on macOS; MPS support unverified; output meshes are approximate and are labelled as such. | Asset library + manual GLB import (already the planned primary path); Blender for cleanup. |
| Geometry | Three.js deterministic engine | CPU/WebGL | None: implemented and unit-tested. | n/a |
| Video | Browser capture + FFmpeg | CPU | Not implemented yet. | n/a |

Approximate sizes (recollection, verify with `ollama show` / actual downloads): Qwen2.5-VL 3B in Ollama is a few GB on disk; SAM 2 tiny
is on the order of 150 MB; TripoSR weights are around 1-2 GB; PaddleOCR models are tens to low hundreds of MB.

## Rules enforced in code

* One AI job at a time (global lock in `backend/app/routers/ai.py`).
* Ollama is called with a short `keep_alive`, so the model unloads soon after use and frees RAM for other work.
* Providers are chosen in `config/providers.json`; changing a provider needs no application code changes.
* A provider that is not installed or not integrated returns an explanatory error. It never returns placeholder data.
* AI-extracted dimensions are always `dimensionsVerified: false`. Only the designer can mark geometry as verified.
