# Implementation progress (honest status)

Legend: DONE = implemented; TESTED = automated test exists and was executed; WRITTEN = code exists but has NOT been executed yet
(it was authored in a sandbox without network access, so dependency-based tests could not be run there).

| Area | Status |
|---|---|
| Deterministic geometry engine (walls, openings, floors, ceilings, spawn) | DONE + TESTED (14 unit tests passed) |
| Dimension string parsing (mm/cm/m, feet, "3 x 4 m") | DONE + TESTED |
| FastAPI backend, SQLite, projects/rooms/openings CRUD, scene endpoint | WRITTEN (compiles; API tests in `backend/tests/test_api.py` not yet run) |
| Asset upload/validation/trash/permanent delete, video-survives-reference-deletion test | WRITTEN |
| AI provider layer, task queue (1 job at a time), retry/cancel | WRITTEN |
| Ollama + Qwen2.5-VL reference analysis | WRITTEN, needs your Mac + `ollama pull qwen2.5vl:3b` |
| OpenCV floor-plan line detection, PaddleOCR | WRITTEN (raw candidates only) |
| Frontend: dashboard, projects, room editor, 3D overview, walkthrough with collision, files, AI center, settings, dark/light | WRITTEN (not yet compiled/run) |
| Scale calibration math, snapping, pixel->metre, trace-room + verify endpoints | DONE: pure math TESTED (checked by hand-run); API tests WRITTEN, not run |
| Floor-plan workspace UI (overlay, 2-point calibration, click-to-trace rooms, OCR length suggestions, verify) | WRITTEN (not compiled/run) |
| Automatic wall/room detection from the plan | NOT IMPLEMENTED (designer traces rooms; OpenCV only returns raw lines) |
| PDF/SVG/DXF tracing, corner dragging on non-rectangular rooms | NOT IMPLEMENTED |
| Furniture placement, object/component editing, undo/redo, versions, room replacement | NOT IMPLEMENTED |
| SAM 2, TripoSR, Blender integration | NOT IMPLEMENTED (providers report "not integrated") |
| Camera paths, walkthrough video export, FFmpeg | NOT IMPLEMENTED |
| Mini-map, section view, Alembic migrations, Playwright/Vitest tests | NOT IMPLEMENTED |
| Model benchmarks on M2 | NOT RUN: use `scripts/benchmark_models.py` |
