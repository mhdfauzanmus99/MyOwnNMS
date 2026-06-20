"""SQLite database layer.

A single module-owned connection guarded by a threading.Lock is used because the
FastAPI app is single-process (uvicorn) and the poller runs in background threads.
SQLite with WAL mode handles concurrent reads + a single writer well at our scale.

Each public function opens its own short transaction so writes from the poller
threads don't hold the lock across SNMP I/O.
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterable, Iterator, Optional

from .config import DATABASE_PATH

_write_lock = threading.Lock()  # serialise writes across poller threads


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS devices (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    hostname     TEXT NOT NULL,
    port         INTEGER NOT NULL DEFAULT 161,
    community    TEXT NOT NULL DEFAULT 'public',
    snmp_version TEXT NOT NULL DEFAULT '2c',
    snmpv3_username      TEXT,
    snmpv3_security_level TEXT NOT NULL DEFAULT 'noAuthNoPriv',
    snmpv3_auth_protocol  TEXT NOT NULL DEFAULT 'none',
    snmpv3_auth_password  TEXT,
    snmpv3_priv_protocol  TEXT NOT NULL DEFAULT 'none',
    snmpv3_priv_password  TEXT,
    snmpv3_context_name   TEXT,
    enabled      INTEGER NOT NULL DEFAULT 1,
    status       TEXT NOT NULL DEFAULT 'unknown',   -- up | down | unknown
    sysname      TEXT,
    sysdescr     TEXT,
    vendor       TEXT,
    model        TEXT,
    location     TEXT,
    contact      TEXT,
    uptime       INTEGER,
    last_polled  TEXT,
    reason       TEXT,                              -- last error if down
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS interfaces (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id    INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    ifindex      INTEGER NOT NULL,
    name         TEXT,
    alias        TEXT,
    descr        TEXT,
    iftype       INTEGER,
    speed        INTEGER,           -- bps
    admin_status TEXT,              -- up | down
    oper_status  TEXT,              -- up | down
    last_seen    TEXT,
    UNIQUE(device_id, ifindex)
);
CREATE INDEX IF NOT EXISTS idx_interfaces_device ON interfaces(device_id);

CREATE TABLE IF NOT EXISTS interface_metrics (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    interface_id  INTEGER NOT NULL REFERENCES interfaces(id) ON DELETE CASCADE,
    ts            TEXT NOT NULL,
    in_octets     INTEGER,
    out_octets    INTEGER,
    in_errors     INTEGER,
    out_errors    INTEGER,
    in_discards   INTEGER,
    out_discards  INTEGER,
    in_bps        REAL,
    out_bps       REAL,
    in_pct        REAL,
    out_pct       REAL
);
CREATE INDEX IF NOT EXISTS idx_metrics_iface_ts ON interface_metrics(interface_id, ts);

CREATE TABLE IF NOT EXISTS system_info (
    device_id    INTEGER PRIMARY KEY REFERENCES devices(id) ON DELETE CASCADE,
    sysdescr     TEXT,
    sysname      TEXT,
    syslocation  TEXT,
    syscontact   TEXT,
    uptime       INTEGER,
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id    INTEGER REFERENCES devices(id) ON DELETE CASCADE,
    interface_id INTEGER REFERENCES interfaces(id) ON DELETE CASCADE,
    ts           TEXT NOT NULL DEFAULT (datetime('now')),
    type         TEXT NOT NULL,         -- link_down | link_up | util_threshold
    severity     TEXT NOT NULL,         -- critical | warning | info
    message      TEXT NOT NULL,
    resolved_at  TEXT,
    acknowledged INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(ts DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_open ON alerts(device_id, interface_id, type, resolved_at);
"""


def init_schema() -> None:
    with get_conn() as conn, _write_lock:
        conn.executescript(SCHEMA)
        _migrate_schema(conn)


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Apply additive migrations for existing SQLite databases."""
    device_columns = {row["name"] for row in conn.execute("PRAGMA table_info(devices)")}
    migrations = {
        "snmpv3_username": "ALTER TABLE devices ADD COLUMN snmpv3_username TEXT",
        "snmpv3_security_level": (
            "ALTER TABLE devices ADD COLUMN snmpv3_security_level TEXT NOT NULL DEFAULT 'noAuthNoPriv'"
        ),
        "snmpv3_auth_protocol": (
            "ALTER TABLE devices ADD COLUMN snmpv3_auth_protocol TEXT NOT NULL DEFAULT 'none'"
        ),
        "snmpv3_auth_password": "ALTER TABLE devices ADD COLUMN snmpv3_auth_password TEXT",
        "snmpv3_priv_protocol": (
            "ALTER TABLE devices ADD COLUMN snmpv3_priv_protocol TEXT NOT NULL DEFAULT 'none'"
        ),
        "snmpv3_priv_password": "ALTER TABLE devices ADD COLUMN snmpv3_priv_password TEXT",
        "snmpv3_context_name": "ALTER TABLE devices ADD COLUMN snmpv3_context_name TEXT",
    }
    for column, sql in migrations.items():
        if column not in device_columns:
            conn.execute(sql)


# ---------------------------------------------------------------------------
# Low-level helpers (return dict rows)
# ---------------------------------------------------------------------------
def query(sql: str, params: Iterable[Any] = ()) -> list[dict]:
    with get_conn() as conn:
        cur = conn.execute(sql, tuple(params))
        return [dict(r) for r in cur.fetchall()]


def query_one(sql: str, params: Iterable[Any] = ()) -> Optional[dict]:
    with get_conn() as conn:
        cur = conn.execute(sql, tuple(params))
        row = cur.fetchone()
        return dict(row) if row else None


def execute(sql: str, params: Iterable[Any] = ()) -> int:
    """Run a write statement and return lastrowid."""
    with get_conn() as conn, _write_lock:
        cur = conn.execute(sql, tuple(params))
        return cur.lastrowid


def executemany(sql: str, seq: Iterable[Iterable[Any]]) -> None:
    with get_conn() as conn, _write_lock:
        conn.executemany(sql, list(seq))


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")
