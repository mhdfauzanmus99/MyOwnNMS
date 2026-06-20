#!/usr/bin/env bash
# NetPulse run: starts the SNMP simulator, the FastAPI backend, and the Vite
# dev server. Ctrl-C stops everything.
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
# shellcheck disable=SC1091
source .venv/bin/activate

export NMS_SIMULATOR="${NMS_SIMULATOR:-1}"

CHILD_PIDS=()

cleanup() {
  echo
  echo "▶ Stopping all processes…"
  for pid in "${CHILD_PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# 1. SNMP simulator (fake devices) — only if enabled
if [[ "${NMS_SIMULATOR}" == "1" ]]; then
  echo "▶ Starting SNMP simulator (udp/1161-1163)"
  python -m backend.app.simulator.agent &
  CHILD_PIDS+=("$!")
  sleep 2
fi

# 2. FastAPI backend
echo "▶ Starting backend (http://127.0.0.1:8000)"
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 &
CHILD_PIDS+=("$!")
sleep 2

# 3. Vite dev server (frontend)
echo "▶ Starting frontend (http://localhost:5173)"
( cd frontend && npm run dev ) &
CHILD_PIDS+=("$!")

echo
echo "✓ NetPulse is running:"
echo "    Frontend  : http://localhost:5173"
echo "    Backend   : http://127.0.0.1:8000/docs"
echo "    Login     : admin / admin"
echo
echo "  Ctrl-C to stop."
echo

wait
