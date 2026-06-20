"""SNMP device simulator.

Spins up three fake SNMPv2c agents on UDP 1161/1162/1163 that look like real
switches/routers to the poller. A background ticker:

  * increments octet counters each second to simulate traffic (one interface per
    device runs near line-rate to exercise the utilisation-threshold alert),
  * flaps one interface's oper status roughly every 90s to fire link-down/up alerts,
  * bumps sysUpTime.

Implementation note: pysnmp is pinned at 4.4.12 (the 6.x line rewrote the API to
asyncio-only and removed both the synchronous client helpers and the agent
responder we use here). We register a UDP endpoint with an SnmpEngine and hand it
a custom MibInstrumController subclass that serves values straight from an
in-memory store — no compiled MIB files required.

Run standalone::

    python -m backend.app.simulator.agent
"""
from __future__ import annotations

import logging
import random
import threading
import time
from dataclasses import dataclass, field

from pyasn1.type import univ
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp
from pysnmp.carrier.asyncore.dgram import udp
from pysnmp.smi import instrum
from pysnmp.proto import rfc1902, rfc1905

# SNMP-specific ASN.1 types (Counter64, TimeTicks, Gauge32, ...). These live in
# pysnmp.proto.rfc1902, not pyasn1.type.univ.
_TimeTicks = rfc1902.TimeTicks
_Counter64 = rfc1902.Counter64
_Counter32 = rfc1902.Counter32
_Gauge32 = rfc1902.Gauge32
_EndOfMibView = rfc1905.EndOfMibView
_NoSuchInstance = rfc1905.NoSuchInstance

logger = logging.getLogger("simulator")

INTERFACES_PER_DEVICE = 5
LINK_FLAP_SECONDS = 90
TICK_SECONDS = 1

IF_TYPE_ETHERNET = 6


@dataclass
class Iface:
    ifindex: int
    name: str
    descr: str
    alias: str
    iftype: int
    speed_bps: int
    admin_status: int = 1
    oper_status: int = 1
    in_octets: int = 0
    out_octets: int = 0
    in_errors: int = 0
    out_errors: int = 0
    in_discards: int = 0
    out_discards: int = 0
    target_util: float = 0.05
    flap: bool = False


@dataclass
class Device:
    name: str
    sysdescr: str
    sysname: str
    syslocation: str
    syscontact: str
    start_time: float = field(default_factory=time.time)
    interfaces: list[Iface] = field(default_factory=list)


def _build_device(name: str, sysdescr: str, sysname: str, high_util_index: int = 1) -> Device:
    dev = Device(name=name, sysdescr=sysdescr, sysname=sysname,
                 syslocation="Rack 12, DC-East", syscontact="netops@example.com")
    speeds = [1_000_000_000, 1_000_000_000, 10_000_000_000, 100_000_000, 1_000_000_000]
    labels = ["Gi0/1", "Gi0/2", "Te0/1", "Fa0/24", "Gi0/3"]
    descs = ["uplink-core", "peering", "10G-trunk", "mgmt", "access"]
    for i in range(INTERFACES_PER_DEVICE):
        dev.interfaces.append(Iface(
            ifindex=i + 1,
            name=labels[i],
            descr=f"{labels[i]} - {descs[i]}",
            alias=descs[i],
            iftype=IF_TYPE_ETHERNET,
            speed_bps=speeds[i],
            in_octets=random.randint(1_000_000, 50_000_000),
            out_octets=random.randint(1_000_000, 50_000_000),
            target_util=0.85 if (i + 1) == high_util_index else random.uniform(0.02, 0.15),
            flap=(i == 0),
        ))
    return dev


def _devices() -> list[Device]:
    return [
        _build_device("core-router-01", "Cisco IOS Software, ISR4451 Software (X86_64_LINUX_IOSD)", "core-router-01", high_util_index=2),
        _build_device("edge-switch-01", "Arista Networks EOS 4.28.0M", "edge-switch-01", high_util_index=1),
        _build_device("access-switch-02", "Linux net-snmp simulator 5.9", "access-switch-02", high_util_index=3),
    ]


# ---------------------------------------------------------------------------
# OID tables the poller queries. Columns map -> a function(Iface) -> value.
# ---------------------------------------------------------------------------
SYSTEM_SCALARS = {
    "1.3.6.1.2.1.1.1.0": lambda d: ("octet", d.sysdescr),
    "1.3.6.1.2.1.1.2.0": lambda d: ("oid", (0, 0)),
    "1.3.6.1.2.1.1.3.0": lambda d: ("timeticks", int((time.time() - d.start_time) * 100)),
    "1.3.6.1.2.1.1.4.0": lambda d: ("octet", d.syscontact),
    "1.3.6.1.2.1.1.5.0": lambda d: ("octet", d.sysname),
    "1.3.6.1.2.1.1.6.0": lambda d: ("octet", d.syslocation),
}

# Each column: (type_tag, value_fn). Type tags map to SNMP ASN.1 types so the
# poller and snmpwalk see correctly-typed values (e.g. HC counters as Counter64).
COLUMN_TABLE = {
    # ifTable (32-bit)
    "1.3.6.1.2.1.2.2.1.1": ("int", lambda i: i.ifindex),           # ifIndex
    "1.3.6.1.2.1.2.2.1.2": ("octet", lambda i: i.descr),           # ifDescr
    "1.3.6.1.2.1.2.2.1.3": ("int", lambda i: i.iftype),            # ifType
    "1.3.6.1.2.1.2.2.1.5": ("gauge", lambda i: min(i.speed_bps, 2**32 - 1)),  # ifSpeed (bps, 32-bit capped)
    "1.3.6.1.2.1.2.2.1.7": ("int", lambda i: i.admin_status),      # ifAdminStatus
    "1.3.6.1.2.1.2.2.1.8": ("int", lambda i: i.oper_status),       # ifOperStatus
    "1.3.6.1.2.1.2.2.1.10": ("counter32", lambda i: i.in_octets % (2**32)),
    "1.3.6.1.2.1.2.2.1.13": ("counter32", lambda i: i.in_discards),
    "1.3.6.1.2.1.2.2.1.14": ("counter32", lambda i: i.in_errors),
    "1.3.6.1.2.1.2.2.1.16": ("counter32", lambda i: i.out_octets % (2**32)),
    "1.3.6.1.2.1.2.2.1.19": ("counter32", lambda i: i.out_discards),
    "1.3.6.1.2.1.2.2.1.20": ("counter32", lambda i: i.out_errors),
    # ifXTable (64-bit)
    "1.3.6.1.2.1.31.1.1.1.1": ("octet", lambda i: i.name),                 # ifName
    "1.3.6.1.2.1.31.1.1.1.6": ("counter64", lambda i: i.in_octets),        # ifHCInOctets
    "1.3.6.1.2.1.31.1.1.1.10": ("counter64", lambda i: i.out_octets),      # ifHCOutOctets
    "1.3.6.1.2.1.31.1.1.1.15": ("gauge", lambda i: i.speed_bps // 1_000_000),  # ifHighSpeed (Mbps)
    "1.3.6.1.2.1.31.1.1.1.18": ("octet", lambda i: i.alias),               # ifAlias
}

ALL_COLUMNS = list(COLUMN_TABLE.keys())


def _encode(kind: str, val):
    """Map a type tag to the correct SNMP ASN.1 value object."""
    if kind == "octet":
        return univ.OctetString(val)
    if kind == "oid":
        return univ.ObjectIdentifier(val)
    if kind == "timeticks":
        return _TimeTicks(val)
    if kind == "counter64":
        return _Counter64(val)
    if kind == "counter32":
        return _Counter32(val)
    if kind == "gauge":
        return _Gauge32(val)
    return univ.Integer(val)  # "int"


def _resolve(device: Device, oid: str):
    """Return (value, end_of_mib?) for an exact OID, or (None, True) if unknown."""
    if oid in SYSTEM_SCALARS:
        kind, val = SYSTEM_SCALARS[oid](device)
        return _encode(kind, val), False
    head, _, tail = oid.rpartition(".")
    try:
        ifindex = int(tail)
    except ValueError:
        return None, True
    iface = next((i for i in device.interfaces if i.ifindex == ifindex), None)
    if iface is None:
        return None, True
    if head in COLUMN_TABLE:
        tag, fn = COLUMN_TABLE[head]
        return _encode(tag, fn(iface)), False
    return None, True


def _ordered_instances(device: Device) -> list[str]:
    """Full lexicographically-sorted OID list served by this device."""
    scalars = list(SYSTEM_SCALARS.keys())
    table = [f"{col}.{i.ifindex}" for col in ALL_COLUMNS for i in device.interfaces]
    return sorted(scalars + table, key=lambda o: tuple(int(x) for x in o.split(".")))


# ---------------------------------------------------------------------------
# Custom MibInstrumController: serves GET/GETNEXT from our store.
# ---------------------------------------------------------------------------
class SimInstrumController(instrum.MibInstrumController):
    def __init__(self, mibBuilder, device: Device):
        super().__init__(mibBuilder)
        self.device = device

    def readVars(self, varBinds, acInfo=(None, None)):  # GET
        result = []
        for name, _ in varBinds:
            oid = ".".join(str(x) for x in name)
            val, _eom = _resolve(self.device, oid)
            if val is None:
                val = _NoSuchInstance()
            result.append((name, val))
        return result

    def readNextVars(self, varBinds, acInfo=(None, None)):  # GETNEXT / GETBULK leaf
        ordered = _ordered_instances(self.device)
        result = []
        for name, _ in varBinds:
            oid_tuple = tuple(int(x) for x in str(name).split(".")) if not isinstance(name, tuple) else name
            nxt = None
            for cand in ordered:
                ct = tuple(int(x) for x in cand.split("."))
                if ct > oid_tuple:
                    nxt = cand
                    break
            if nxt is None:
                result.append((name, _EndOfMibView()))
            else:
                val, _eom = _resolve(self.device, nxt)
                nxt_tuple = tuple(int(x) for x in nxt.split("."))
                result.append((nxt_tuple, val))
        return result


# ---------------------------------------------------------------------------
# Per-device agent
# ---------------------------------------------------------------------------
def _serve_udp(device: Device, port: int, community: str) -> None:
    snmpEngine = engine.SnmpEngine()
    config.addTransport(
        snmpEngine,
        udp.domainName,
        udp.UdpTransport().openServerMode(("127.0.0.1", port)),
    )
    # Community string -> securityName for both v1 (secModel=1) and v2c (secModel=2).
    config.addV1System(snmpEngine, "idx", community)
    # VACM: authorize "idx" for read access under both security models.
    config.addVacmUser(snmpEngine, 1, "idx", "noAuthNoPriv",
                       (1, 3, 6, 1, 2, 1), (1, 3, 6, 1, 2, 1))
    config.addVacmUser(snmpEngine, 2, "idx", "noAuthNoPriv",
                       (1, 3, 6, 1, 2, 1), (1, 3, 6, 1, 2, 1))

    # Bind our custom instrument controller to the default (empty) context name,
    # then hand the context to the GET/GETNEXT/GETBULK responders.
    from pysnmp.entity.rfc3413.context import SnmpContext
    snmpContext = SnmpContext(snmpEngine)
    instrum_controller = SimInstrumController(snmpEngine.getMibBuilder(), device)
    # The default contextName is the empty octet string.
    snmpContext.unregisterContextName(univ.OctetString(""))
    snmpContext.registerContextName(univ.OctetString(""), instrum_controller)

    cmdrsp.GetCommandResponder(snmpEngine, snmpContext)
    cmdrsp.NextCommandResponder(snmpEngine, snmpContext)
    cmdrsp.BulkCommandResponder(snmpEngine, snmpContext)

    logger.info("Simulated device '%s' serving SNMPv2c on udp/127.0.0.1:%d (community=%s)",
                device.name, port, community)
    snmpEngine.transportDispatcher.jobStarted(1)
    try:
        snmpEngine.transportDispatcher.runDispatcher()
    finally:
        snmpEngine.transportDispatcher.closeDispatcher()


# ---------------------------------------------------------------------------
# Background ticker
# ---------------------------------------------------------------------------
def _ticker(devices: list[Device], stop: threading.Event) -> None:
    next_flap = {d.name: time.time() + LINK_FLAP_SECONDS for d in devices}
    while not stop.is_set():
        now = time.time()
        for d in devices:
            for iface in d.interfaces:
                if iface.oper_status != 1:
                    continue
                rate = iface.speed_bps * iface.target_util / 8
                iface.in_octets += int(rate * TICK_SECONDS * random.uniform(0.6, 1.4))
                iface.out_octets += int(rate * TICK_SECONDS * random.uniform(0.3, 0.9))
                if random.random() < 0.02:
                    iface.in_errors += random.randint(1, 5)
            if now >= next_flap[d.name]:
                flap = next((i for i in d.interfaces if i.flap), None)
                if flap:
                    flap.oper_status = 2 if flap.oper_status == 1 else 1
                    logger.info("[%s] interface %s oper_status -> %s",
                                d.name, flap.name, "up" if flap.oper_status == 1 else "down")
                next_flap[d.name] = now + LINK_FLAP_SECONDS
        time.sleep(TICK_SECONDS)


def run() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    devices = _devices()
    ports = [1161, 1162, 1163]
    stop = threading.Event()
    threading.Thread(target=_ticker, args=(devices, stop), daemon=True, name="sim-ticker").start()
    threads = []
    for dev, port in zip(devices, ports):
        th = threading.Thread(target=_serve_udp, args=(dev, port, "public"),
                              daemon=True, name=f"sim-{dev.name}")
        th.start()
        threads.append(th)
    logger.info("Simulator running. Ctrl-C to stop.")
    try:
        for th in threads:
            th.join()
    except KeyboardInterrupt:
        stop.set()


if __name__ == "__main__":
    run()
