#!/usr/bin/env bash
# One-time setup for macOS (Apple Silicon). Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" || { echo "Need Python 3.10+. Run: brew install python@3.12"; exit 1; }
command -v node >/dev/null || { echo "Need Node.js 18.18+. Run: brew install node"; exit 1; }
echo "==> Backend"
python3 -m venv backend/.venv
backend/.venv/bin/pip install --upgrade pip
backend/.venv/bin/pip install -r backend/requirements-dev.txt
echo "==> Frontend"
(cd frontend && npm install)
echo "==> Done. Start the app with: ./scripts/dev.sh"
