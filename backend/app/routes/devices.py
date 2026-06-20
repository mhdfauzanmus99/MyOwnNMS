"""Device CRUD + interface listing + manual poll trigger."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .. import database, scheduler
from ..auth import require_user

router = APIRouter(prefix="/api/devices", tags=["devices"])


class DeviceIn(BaseModel):
    name: str
    hostname: str
    port: int = 161
    community: str = "public"
    snmp_version: str = Field(default="2c")
    enabled: bool = True


class DevicePatch(BaseModel):
    name: Optional[str] = None
    hostname: Optional[str] = None
    port: Optional[int] = None
    community: Optional[str] = None
    snmp_version: Optional[str] = None
    enabled: Optional[bool] = None


@router.get("")
def list_devices(_user=Depends(require_user)) -> list[dict]:
    return database.query(
        """SELECT d.*,
                  (SELECT COUNT(*) FROM interfaces i WHERE i.device_id=d.id) AS interface_count,
                  (SELECT COUNT(*) FROM alerts a WHERE a.device_id=d.id AND a.resolved_at IS NULL)
                    AS open_alerts
           FROM devices d ORDER BY d.name"""
    )


@router.post("")
def create_device(body: DeviceIn, _user=Depends(require_user)) -> dict:
    dev_id = database.execute(
        """INSERT INTO devices (name, hostname, port, community, snmp_version, enabled)
           VALUES (?,?,?,?,?,?)""",
        (body.name, body.hostname, body.port, body.community, body.snmp_version, int(body.enabled)),
    )
    # Trigger an immediate poll so the new device appears populated.
    scheduler.poll_now()
    return {"id": dev_id, "ok": True}


@router.get("/{device_id}")
def get_device(device_id: int, _user=Depends(require_user)) -> dict:
    row = database.query_one("SELECT * FROM devices WHERE id=?", (device_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Device not found")
    return row


@router.patch("/{device_id}")
def patch_device(device_id: int, body: DevicePatch, _user=Depends(require_user)) -> dict:
    fields, vals = [], []
    for k, v in body.dict(exclude_none=True).items():
        fields.append(f"{k}=?")
        vals.append(int(v) if isinstance(v, bool) else v)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    vals.append(device_id)
    database.execute(f"UPDATE devices SET {', '.join(fields)} WHERE id=?", vals)
    return {"ok": True}


@router.delete("/{device_id}")
def delete_device(device_id: int, _user=Depends(require_user)) -> dict:
    database.execute("DELETE FROM devices WHERE id=?", (device_id,))
    return {"ok": True}


@router.get("/{device_id}/interfaces")
def device_interfaces(device_id: int, _user=Depends(require_user)) -> list[dict]:
    return database.query(
        """SELECT i.*,
                  (SELECT in_pct  FROM interface_metrics m WHERE m.interface_id=i.id ORDER BY m.ts DESC LIMIT 1) AS in_pct,
                  (SELECT out_pct FROM interface_metrics m WHERE m.interface_id=i.id ORDER BY m.ts DESC LIMIT 1) AS out_pct,
                  (SELECT in_bps  FROM interface_metrics m WHERE m.interface_id=i.id ORDER BY m.ts DESC LIMIT 1) AS in_bps,
                  (SELECT out_bps FROM interface_metrics m WHERE m.interface_id=i.id ORDER BY m.ts DESC LIMIT 1) AS out_bps
           FROM interfaces i WHERE i.device_id=? ORDER BY i.ifindex""",
        (device_id,),
    )


@router.post("/{device_id}/poll")
def poll_device_now(device_id: int, _user=Depends(require_user)) -> dict:
    dev = database.query_one("SELECT * FROM devices WHERE id=?", (device_id,))
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    from .. import poller
    poller.poll_device(dev)
    return {"ok": True}
