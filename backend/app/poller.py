"""SNMP poller.

Polls a single device: system scalars + the interface tables, then persists
results and triggers alert evaluation. Utilisation is computed per-poll from the
delta of 64-bit HC counters (with 32-bit fallback) so graphs stay cheap.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from pysnmp.hlapi import (
    CommunityData,
    ContextData,
    ObjectType,
    ObjectIdentity,
    SnmpEngine,
    UsmUserData,
    UdpTransportTarget,
    nextCmd,
    getCmd,
    usmAesCfb128Protocol,
    usmAesCfb192Protocol,
    usmAesCfb256Protocol,
    usmDESPrivProtocol,
    usmHMAC128SHA224AuthProtocol,
    usmHMAC192SHA256AuthProtocol,
    usmHMAC256SHA384AuthProtocol,
    usmHMAC384SHA512AuthProtocol,
    usmHMACMD5AuthProtocol,
    usmHMACSHAAuthProtocol,
    usmNoAuthProtocol,
    usmNoPrivProtocol,
)

from . import alerts, database, oids
from .config import settings

logger = logging.getLogger(__name__)


# Map numeric ifOperStatus / ifAdminStatus to readable labels.
_STATUS = {1: "up", 2: "down", 3: "testing", 4: "unknown", 5: "dormant", 6: "notpresent", 7: "lowerlayerdown"}


def _transport(device: dict) -> UdpTransportTarget:
    return UdpTransportTarget(
        (device["hostname"], device["port"]),
        timeout=settings.snmp_timeout,
        retries=settings.snmp_retries,
    )


_AUTH_PROTOCOLS = {
    "none": usmNoAuthProtocol,
    "md5": usmHMACMD5AuthProtocol,
    "sha": usmHMACSHAAuthProtocol,
    "sha224": usmHMAC128SHA224AuthProtocol,
    "sha256": usmHMAC192SHA256AuthProtocol,
    "sha384": usmHMAC256SHA384AuthProtocol,
    "sha512": usmHMAC384SHA512AuthProtocol,
}

_PRIV_PROTOCOLS = {
    "none": usmNoPrivProtocol,
    "des": usmDESPrivProtocol,
    "aes": usmAesCfb128Protocol,
    "aes128": usmAesCfb128Protocol,
    "aes192": usmAesCfb192Protocol,
    "aes256": usmAesCfb256Protocol,
}


def _security_data(device: dict):
    version = (device.get("snmp_version") or "2c").lower()
    if version in {"3", "v3", "snmpv3"}:
        username = (device.get("snmpv3_username") or "").strip()
        if not username:
            raise RuntimeError("SNMPv3 username is required")

        security_level = (device.get("snmpv3_security_level") or "noAuthNoPriv").strip()
        auth_protocol_name = (device.get("snmpv3_auth_protocol") or "none").lower()
        priv_protocol_name = (device.get("snmpv3_priv_protocol") or "none").lower()
        auth_key = device.get("snmpv3_auth_password") or None
        priv_key = device.get("snmpv3_priv_password") or None

        if security_level in {"authNoPriv", "authPriv"} and not auth_key:
            raise RuntimeError("SNMPv3 auth password is required")
        if security_level == "authPriv" and not priv_key:
            raise RuntimeError("SNMPv3 privacy password is required")
        if security_level == "noAuthNoPriv":
            auth_protocol_name = "none"
            priv_protocol_name = "none"
            auth_key = None
            priv_key = None
        elif security_level == "authNoPriv":
            priv_protocol_name = "none"
            priv_key = None

        return UsmUserData(
            username,
            authKey=auth_key,
            privKey=priv_key,
            authProtocol=_AUTH_PROTOCOLS.get(auth_protocol_name, usmHMACSHAAuthProtocol),
            privProtocol=_PRIV_PROTOCOLS.get(priv_protocol_name, usmAesCfb128Protocol),
        )

    # mpModel: 0=SNMPv1, 1=SNMPv2c
    mp = 0 if version == "1" else 1
    return CommunityData(device.get("community") or "public", mpModel=mp)


def _context(device: dict) -> ContextData:
    context_name = device.get("snmpv3_context_name")
    if (device.get("snmp_version") or "").lower() in {"3", "v3", "snmpv3"} and context_name:
        return ContextData(contextName=str(context_name))
    return ContextData()


def _walk(oid: str, device: dict) -> dict[int, object]:
    """Walk a single column OID, returning {ifIndex: value}."""
    results: dict[int, object] = {}
    it = nextCmd(
        SnmpEngine(),
        _security_data(device),
        _transport(device),
        _context(device),
        ObjectType(ObjectIdentity(oid)),
        lexicographicMode=False,
    )
    for error_indication, error_status, error_index, var_binds in it:
        if error_indication:
            raise RuntimeError(str(error_indication))
        if error_status:
            raise RuntimeError(error_status.prettyPrint())
        for vb in var_binds:
            # The instance OID (e.g. "1.3.6.1.2.1.31.1.1.1.1.5") ends with the ifIndex.
            full_oid = vb[0].prettyPrint()
            if_index = oids.ifindex_from_oid(full_oid)
            try:
                results[if_index] = int(vb[1])
            except (TypeError, ValueError):
                results[if_index] = vb[1].prettyPrint()
    return results


def _get_scalar(oid: str, device: dict) -> Optional[object]:
    """Single GET for a scalar (.0) OID."""
    gen = getCmd(
        SnmpEngine(),
        _security_data(device),
        _transport(device),
        _context(device),
        ObjectType(ObjectIdentity(oid)),
    )
    error_indication, error_status, error_index, var_binds = next(gen)
    if error_indication:
        raise RuntimeError(str(error_indication))
    if error_status:
        raise RuntimeError(error_status.prettyPrint())
    if not var_binds:
        return None
    val = var_binds[0][1]
    try:
        return int(val)
    except (TypeError, ValueError):
        return val.prettyPrint()


def _guess_vendor(sysdescr: str, sysobjid: Optional[object]) -> str:
    d = (sysdescr or "").lower()
    if "cisco" in d:
        return "Cisco"
    if "juniper" in d or "junos" in d:
        return "Juniper"
    if "arista" in d:
        return "Arista"
    if "mikrotik" in d:
        return "MikroTik"
    if "linux" in d:
        return "Linux"
    if "windows" in d:
        return "Windows"
    return "Unknown"


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------
def poll_device(device: dict) -> None:
    """Poll one device end to end, persisting metrics + firing alerts."""
    device_id = device["id"]
    t_now = database.now_iso()
    try:
        # --- system scalars ---
        sysdescr = _get_scalar(oids.SYS_DESCR, device)
        sysname = _get_scalar(oids.SYS_NAME, device) or device["name"]
        syslocation = _get_scalar(oids.SYS_LOCATION, device)
        syscontact = _get_scalar(oids.SYS_CONTACT, device)
        uptime = _get_scalar(oids.SYS_UPTIME, device)
        sysdescr_s = str(sysdescr) if sysdescr is not None else ""

        # --- interface tables ---
        names = _walk(oids.IF_NAME, device)
        aliases = _walk(oids.IF_ALIAS, device)
        descrs = _walk(oids.IF_DESCR, device)
        iftypes = _walk(oids.IF_TYPE, device)
        hc_in = _walk(oids.IF_HC_IN_OCTETS, device)
        hc_out = _walk(oids.IF_HC_OUT_OCTETS, device)
        in_octets32 = _walk(oids.IF_IN_OCTETS, device)
        out_octets32 = _walk(oids.IF_OUT_OCTETS, device)
        in_errors = _walk(oids.IF_IN_ERRORS, device)
        out_errors = _walk(oids.IF_OUT_ERRORS, device)
        in_discards = _walk(oids.IF_IN_DISCARDS, device)
        out_discards = _walk(oids.IF_OUT_DISCARDS, device)
        admin_status = _walk(oids.IF_ADMIN_STATUS, device)
        oper_status = _walk(oids.IF_OPER_STATUS, device)
        high_speed = _walk(oids.IF_HIGH_SPEED, device)
        speed32 = _walk(oids.IF_SPEED, device)

        all_indexes = set(names) | set(descrs) | set(hc_in) | set(in_octets32)

        # --- persist device header + system info ---
        vendor = _guess_vendor(sysdescr_s, None)
        database.execute(
            """UPDATE devices SET status='up', sysname=?, sysdescr=?, vendor=?,
               location=?, contact=?, uptime=?, last_polled=?, reason=NULL WHERE id=?""",
            (sysname, sysdescr_s, vendor, str(syslocation), str(syscontact),
             int(uptime) if isinstance(uptime, int) else None, t_now, device_id),
        )
        database.execute(
            """INSERT INTO system_info (device_id, sysdescr, sysname, syslocation,
               syscontact, uptime, updated_at)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(device_id) DO UPDATE SET sysdescr=excluded.sysdescr,
               sysname=excluded.sysname, syslocation=excluded.syslocation,
               syscontact=excluded.syscontact, uptime=excluded.uptime,
               updated_at=excluded.updated_at""",
            (device_id, sysdescr_s, str(sysname), str(syslocation), str(syscontact),
             int(uptime) if isinstance(uptime, int) else None, t_now),
        )

        # --- per-interface processing ---
        for ifindex in sorted(all_indexes):
            # Resolve best octet counter (prefer 64-bit HC).
            if ifindex in hc_in and isinstance(hc_in[ifindex], int):
                in_oct = hc_in[ifindex]
            elif ifindex in in_octets32:
                in_oct = in_octets32[ifindex] if isinstance(in_octets32[ifindex], int) else None
            else:
                in_oct = None
            if ifindex in hc_out and isinstance(hc_out[ifindex], int):
                out_oct = hc_out[ifindex]
            elif ifindex in out_octets32:
                out_oct = out_octets32[ifindex] if isinstance(out_octets32[ifindex], int) else None
            else:
                out_oct = None

            # Speed in bps: prefer ifHighSpeed (Mbps) else ifSpeed (bps).
            speed_bps = 0
            if ifindex in high_speed and isinstance(high_speed[ifindex], int):
                speed_bps = high_speed[ifindex] * 1_000_000
            elif ifindex in speed32 and isinstance(speed32[ifindex], int):
                speed_bps = speed32[ifindex]

            admin = _STATUS.get(admin_status.get(ifindex, 0), "unknown")
            oper = _STATUS.get(oper_status.get(ifindex, 0), "unknown")

            iface_row = database.query_one(
                "SELECT id, oper_status FROM interfaces WHERE device_id=? AND ifindex=?",
                (device_id, ifindex),
            )
            if iface_row:
                iface_id = iface_row["id"]
                prev_oper = iface_row["oper_status"]
                # Update the interface row.
                database.execute(
                    """UPDATE interfaces SET name=?, alias=?, descr=?, iftype=?, speed=?,
                       admin_status=?, oper_status=?, last_seen=? WHERE id=?""",
                    (str(names.get(ifindex, "")), str(aliases.get(ifindex, "")),
                     str(descrs.get(ifindex, "")), iftypes.get(ifindex), speed_bps,
                     admin, oper, t_now, iface_id),
                )
            else:
                prev_oper = None
                iface_id = database.execute(
                    """INSERT INTO interfaces (device_id, ifindex, name, alias, descr,
                       iftype, speed, admin_status, oper_status, last_seen)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (device_id, ifindex, str(names.get(ifindex, "")),
                     str(aliases.get(ifindex, "")), str(descrs.get(ifindex, "")),
                     iftypes.get(ifindex), speed_bps, admin, oper, t_now),
                )

            # --- utilisation from previous metric sample ---
            last = database.query_one(
                "SELECT in_octets, out_octets, ts FROM interface_metrics "
                "WHERE interface_id=? ORDER BY ts DESC LIMIT 1",
                (iface_id,),
            )
            in_bps = out_bps = in_pct = out_pct = None
            if last and in_oct is not None and out_oct is not None and last["ts"]:
                from datetime import datetime
                try:
                    t_prev = datetime.fromisoformat(last["ts"])
                    t_cur = datetime.fromisoformat(t_now)
                    dt = (t_cur - t_prev).total_seconds()
                except ValueError:
                    dt = settings.poll_interval_seconds
                if dt > 0 and speed_bps > 0:
                    prev_in = last["in_octets"] if last["in_octets"] is not None else in_oct
                    prev_out = last["out_octets"] if last["out_octets"] is not None else out_oct
                    d_in = in_oct - prev_in
                    d_out = out_oct - prev_out
                    # Counter wraparound / device reboot guard.
                    if d_in < 0:
                        d_in = in_oct
                    if d_out < 0:
                        d_out = out_oct
                    in_bps = (d_in * 8) / dt
                    out_bps = (d_out * 8) / dt
                    in_pct = round(min(in_bps / speed_bps * 100, 100.0), 2)
                    out_pct = round(min(out_bps / speed_bps * 100, 100.0), 2)

            database.execute(
                """INSERT INTO interface_metrics
                   (interface_id, ts, in_octets, out_octets, in_errors, out_errors,
                    in_discards, out_discards, in_bps, out_bps, in_pct, out_pct)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (iface_id, t_now, in_oct, out_oct, in_errors.get(ifindex),
                 out_errors.get(ifindex), in_discards.get(ifindex),
                 out_discards.get(ifindex), in_bps, out_bps, in_pct, out_pct),
            )

            # --- alerts ---
            alerts.evaluate_link_flap(device, {"id": iface_id, "name": str(names.get(ifindex, ""))},
                                      prev_oper, oper)
            if in_pct is not None or out_pct is not None:
                alerts.evaluate_util_threshold(device, {"id": iface_id, "name": str(names.get(ifindex, ""))},
                                               in_pct, out_pct, speed_bps)

    except Exception as exc:  # noqa: BLE001
        logger.warning("Poll failed for device %s (%s): %s", device_id, device.get("hostname"), exc)
        database.execute(
            "UPDATE devices SET status='down', last_polled=?, reason=? WHERE id=?",
            (t_now, str(exc)[:300], device_id),
        )
