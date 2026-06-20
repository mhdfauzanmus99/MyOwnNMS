"""Application configuration.

All settings can be overridden with environment variables, e.g.::

    NMS_ADMIN_PASSWORD=changeme python -m backend.app.init_db
"""
from __future__ import annotations

import os
from pathlib import Path

# Project root = two levels up from this file (backend/app/config.py -> repo root).
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIR / "nms.db"


class Settings:
    # --- Auth -------------------------------------------------------------
    secret_key: str = os.getenv("NMS_SECRET_KEY", "dev-secret-change-me-in-production")
    session_cookie: str = "nms_session"
    session_max_age: int = 60 * 60 * 24 * 7  # 7 days (seconds)

    admin_username: str = os.getenv("NMS_ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("NMS_ADMIN_PASSWORD", "admin")

    # --- Polling ----------------------------------------------------------
    poll_interval_seconds: int = int(os.getenv("NMS_POLL_INTERVAL", "60"))
    snmp_timeout: int = int(os.getenv("NMS_SNMP_TIMEOUT", "4"))   # seconds per GET/WALK
    snmp_retries: int = int(os.getenv("NMS_SNMP_RETRIES", "2"))

    # --- Alerting ---------------------------------------------------------
    # An interface sustaining utilisation above this fires a threshold alert.
    util_threshold_pct: float = float(os.getenv("NMS_UTIL_THRESHOLD", "80"))

    # --- Server -----------------------------------------------------------
    backend_host: str = os.getenv("NMS_HOST", "127.0.0.1")
    backend_port: int = int(os.getenv("NMS_PORT", "8000"))

    # --- Simulator --------------------------------------------------------
    # Set false if you only poll real devices.
    simulator_enabled: bool = os.getenv("NMS_SIMULATOR", "1") == "1"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{DATABASE_PATH}"


settings = Settings()
