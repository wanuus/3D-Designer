#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
trap 'kill 0' EXIT INT TERM
(cd backend && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload) &
(cd frontend && npm run dev -- -H 127.0.0.1) &
echo "Backend  http://127.0.0.1:8000/docs"; echo "App      http://127.0.0.1:3000"
wait
