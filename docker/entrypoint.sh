#!/usr/bin/env sh
set -eu

python -m backend.app.init_db

if [ "${NMS_SIMULATOR:-0}" = "1" ]; then
  echo "Starting SNMP simulator on UDP 1161-1163"
  python -m backend.app.simulator.agent &
fi

exec uvicorn backend.app.main:app --host "${NMS_HOST:-0.0.0.0}" --port "${NMS_PORT:-8000}"
