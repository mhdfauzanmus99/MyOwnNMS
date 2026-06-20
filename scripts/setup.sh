#!/usr/bin/env bash
# NetPulse one-time setup: Python venv, deps, DB init, frontend deps.
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

echo "▶ NetPulse setup"
echo "  project root: $ROOT"
echo

# --- Python backend ----------------------------------------------------------
if [[ ! -d ".venv" ]]; then
  echo "▶ Creating Python virtualenv (.venv)"
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
echo "▶ Installing Python dependencies"
pip install --quiet --upgrade pip
pip install --quiet -r backend/requirements.txt
echo "  Python deps installed"
echo

# --- Database init + seeding -------------------------------------------------
echo "▶ Initializing database + seeding admin user and simulated devices"
python -m backend.app.init_db
echo

# --- Frontend ----------------------------------------------------------------
if ! command -v node >/dev/null 2>&1; then
  echo "✗ Node.js not found. Install it first:  brew install node"
  exit 1
fi
echo "▶ Installing frontend dependencies"
( cd frontend && npm install --silent )
echo

echo "✓ Setup complete. Start everything with:  bash scripts/run.sh"
