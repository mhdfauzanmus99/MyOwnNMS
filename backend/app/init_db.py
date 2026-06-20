"""Standalone DB init + seeding entry point.

Run with::

    python -m backend.app.init_db

Creates the schema, seeds the admin user, and (if the simulator is enabled)
registers the three simulated SNMP devices so the dashboard is populated.
"""
from __future__ import annotations

import logging

from . import auth, database
from .config import settings

logger = logging.getLogger("init_db")

SIMULATED_DEVICES = [
    {"name": "core-router-01", "hostname": "127.0.0.1", "port": 1161, "community": "public", "snmp_version": "2c"},
    {"name": "edge-switch-01", "hostname": "127.0.0.1", "port": 1162, "community": "public", "snmp_version": "2c"},
    {"name": "access-switch-02", "hostname": "127.0.0.1", "port": 1163, "community": "public", "snmp_version": "2c"},
]


def seed_simulated_devices() -> None:
    if not settings.simulator_enabled:
        logger.info("Simulator disabled — skipping seed of simulated devices.")
        return
    for d in SIMULATED_DEVICES:
        existing = database.query_one("SELECT id FROM devices WHERE name=?", (d["name"],))
        if existing:
            continue
        database.execute(
            """INSERT INTO devices (name, hostname, port, community, snmp_version, enabled)
               VALUES (?,?,?,?,?,1)""",
            (d["name"], d["hostname"], d["port"], d["community"], d["snmp_version"]),
        )
        logger.info("Seeded simulated device: %s (udp/%d)", d["name"], d["port"])


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    database.init_schema()
    logger.info("Schema initialised at %s", database.DATABASE_PATH)
    auth.ensure_admin_user()
    logger.info("Admin user ensured: %s", settings.admin_username)
    seed_simulated_devices()
    logger.info("Done. Start everything with: bash scripts/run.sh")


if __name__ == "__main__":
    main()
