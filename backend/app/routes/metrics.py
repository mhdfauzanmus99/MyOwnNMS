"""Interface detail + time-series metrics for graphs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import database
from ..auth import require_user

router = APIRouter(prefix="/api", tags=["metrics"])

_RANGE_SECONDS = {"1h": 3600, "6h": 21600, "24h": 86400}


@router.get("/interfaces/{interface_id}")
def get_interface(interface_id: int, _user=Depends(require_user)) -> dict:
    row = database.query_one(
        """SELECT i.*, d.name AS device_name
           FROM interfaces i JOIN devices d ON d.id=i.device_id
           WHERE i.id=?""",
        (interface_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Interface not found")
    return row


@router.get("/interfaces/{interface_id}/metrics")
def interface_metrics(
    interface_id: int,
    range: str = Query("1h", pattern="^(1h|6h|24h)$"),
    _user=Depends(require_user),
) -> list[dict]:
    secs = _RANGE_SECONDS[range]
    rows = database.query(
        """SELECT ts, in_octets, out_octets, in_errors, out_errors,
                  in_discards, out_discards, in_bps, out_bps, in_pct, out_pct
           FROM interface_metrics
           WHERE interface_id=? AND ts >= datetime('now', ?)
           ORDER BY ts ASC""",
        (interface_id, f"-{secs} seconds"),
    )
    return rows
