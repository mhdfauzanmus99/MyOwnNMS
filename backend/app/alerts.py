"""Alert evaluation: link flaps + utilisation thresholds.

Called from the poller after each interface sample. Fires an alert + publishes an
SSE event. Threshold alerts are "open/closed" — one open alert per interface,
resolved when utilisation drops back below the threshold.
"""
from __future__ import annotations

import logging
from typing import Optional

from . import database, events
from .config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Link flap
# ---------------------------------------------------------------------------
def evaluate_link_flap(device: dict, interface: dict, prev: str | None, cur: str | None) -> None:
    if prev is None or cur is None or prev == cur:
        return
    if cur == "down" and prev != "down":
        _emit(
            device, interface, "link_down", "critical",
            f"{device['name']} {interface['name']}: link went DOWN",
        )
    elif cur == "up" and prev != "up":
        _emit(
            device, interface, "link_up", "info",
            f"{device['name']} {interface['name']}: link came UP",
        )


# ---------------------------------------------------------------------------
# Utilisation threshold
# ---------------------------------------------------------------------------
def evaluate_util_threshold(
    device: dict,
    interface: dict,
    in_pct: float | None,
    out_pct: float | None,
    speed_bps: int,
) -> None:
    if in_pct is None and out_pct is None:
        return
    peak = max(filter(lambda x: x is not None, (in_pct, out_pct)))
    threshold = settings.util_threshold_pct

    open_alert = database.query_one(
        "SELECT id FROM alerts WHERE interface_id=? AND type='util_threshold' "
        "AND resolved_at IS NULL ORDER BY id DESC LIMIT 1",
        (interface["id"],),
    )

    if peak >= threshold:
        if not open_alert:
            direction = "in" if in_pct == peak else "out"
            _emit(
                device, interface, "util_threshold", "warning",
                f"{device['name']} {interface['name']}: {direction} utilisation "
                f"{peak:.0f}% ≥ {threshold:.0f}%",
            )
    else:
        # Drop below threshold -> resolve any open alert.
        if open_alert:
            database.execute(
                "UPDATE alerts SET resolved_at=? WHERE id=?",
                (database.now_iso(), open_alert["id"]),
            )


# ---------------------------------------------------------------------------
# Shared emitter
# ---------------------------------------------------------------------------
def _emit(device: dict, interface: dict, atype: str, severity: str, message: str) -> None:
    alert_id = database.execute(
        """INSERT INTO alerts (device_id, interface_id, type, severity, message)
           VALUES (?,?,?,?,?)""",
        (device["id"], interface["id"], atype, severity, message),
    )
    events.publish({
        "kind": "alert",
        "id": alert_id,
        "device_id": device["id"],
        "device_name": device["name"],
        "interface_id": interface["id"],
        "interface_name": interface["name"],
        "type": atype,
        "severity": severity,
        "message": message,
        "ts": database.now_iso(),
    })
