"""Alert feed + acknowledge."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .. import database
from ..auth import require_user

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("")
def list_alerts(
    resolved: Optional[bool] = Query(default=None),
    limit: int = Query(default=100, le=500),
    _user=Depends(require_user),
) -> list[dict]:
    where = ""
    params: list = []
    if resolved is False:
        where = "WHERE a.resolved_at IS NULL"
    elif resolved is True:
        where = "WHERE a.resolved_at IS NOT NULL"
    return database.query(
        f"""SELECT a.*, d.name AS device_name, i.name AS interface_name
            FROM alerts a
            LEFT JOIN devices d ON d.id=a.device_id
            LEFT JOIN interfaces i ON i.id=a.interface_id
            {where}
            ORDER BY a.ts DESC LIMIT ?""",
        (*params, limit),
    )


class AckIn(BaseModel):
    acknowledged: bool = True


@router.post("/{alert_id}/ack")
def ack_alert(alert_id: int, body: AckIn, _user=Depends(require_user)) -> dict:
    database.execute(
        "UPDATE alerts SET acknowledged=? WHERE id=?",
        (int(body.acknowledged), alert_id),
    )
    return {"ok": True}


@router.delete("/{alert_id}")
def resolve_alert(alert_id: int, _user=Depends(require_user)) -> dict:
    database.execute(
        "UPDATE alerts SET resolved_at=datetime('now') WHERE id=? AND resolved_at IS NULL",
        (alert_id,),
    )
    return {"ok": True}
