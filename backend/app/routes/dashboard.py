"""Dashboard aggregation: summary counts + top utilised interfaces."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import database
from ..auth import require_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(_user=Depends(require_user)) -> dict:
    device_counts = database.query(
        """SELECT
              SUM(CASE WHEN status='up' THEN 1 ELSE 0 END) AS up,
              SUM(CASE WHEN status='down' THEN 1 ELSE 0 END) AS down,
              SUM(CASE WHEN status='unknown' THEN 1 ELSE 0 END) AS unknown,
              COUNT(*) AS total
           FROM devices WHERE enabled=1"""
    )[0]

    iface_counts = database.query(
        """SELECT
              SUM(CASE WHEN oper_status='up' THEN 1 ELSE 0 END) AS up,
              SUM(CASE WHEN oper_status='down' THEN 1 ELSE 0 END) AS down,
              COUNT(*) AS total
           FROM interfaces"""
    )[0]

    open_alerts = database.query(
        "SELECT COUNT(*) AS n FROM alerts WHERE resolved_at IS NULL"
    )[0]["n"]

    # Top utilised interfaces by latest sample (peak of in/out).
    top = database.query(
        """SELECT m.in_pct, m.out_pct, m.in_bps, m.out_bps, m.ts,
                  i.id AS interface_id, i.name AS interface_name,
                  i.speed, d.id AS device_id, d.name AS device_name
           FROM interface_metrics m
           JOIN interfaces i ON i.id=m.interface_id
           JOIN devices d ON d.id=i.device_id
           WHERE m.ts = (SELECT MAX(ts) FROM interface_metrics m2 WHERE m2.interface_id=m.interface_id)
             AND i.oper_status='up'
           ORDER BY MAX(m.in_pct, m.out_pct) DESC
           LIMIT 8"""
    )

    recent_alerts = database.query(
        """SELECT a.*, d.name AS device_name, i.name AS interface_name
           FROM alerts a
           LEFT JOIN devices d ON d.id=a.device_id
           LEFT JOIN interfaces i ON i.id=a.interface_id
           ORDER BY a.ts DESC LIMIT 10"""
    )

    return {
        "devices": device_counts,
        "interfaces": iface_counts,
        "open_alerts": open_alerts,
        "top_interfaces": top,
        "recent_alerts": recent_alerts,
    }
