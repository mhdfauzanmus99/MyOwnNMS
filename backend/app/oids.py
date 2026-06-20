"""Standard SNMP OID definitions used by the poller.

All values are numeric so we don't depend on MIB files being present. The poller
reads 64-bit HC counters from ifXTable where available (falls back to 32-bit
ifTable counters handled in the poller logic).
"""
from __future__ import annotations

# --- system group (iso.org.dod.internet.mgmt.mib-2.system) ---
SYS_DESCR = "1.3.6.1.2.1.1.1.0"
SYS_OBJECT_ID = "1.3.6.1.2.1.1.2.0"
SYS_UPTIME = "1.3.6.1.2.1.1.3.0"
SYS_CONTACT = "1.3.6.1.2.1.1.4.0"
SYS_NAME = "1.3.6.1.2.1.1.5.0"
SYS_LOCATION = "1.3.6.1.2.1.1.6.0"

# --- ifMIB (ifXTable): scalar/64-bit + extra columns ---
# Base for the table = 1.3.6.1.2.1.31.1.1.1 ; each column appended with its number.
IFXTABLE = "1.3.6.1.2.1.31.1.1.1"
IF_NAME = f"{IFXTABLE}.1"
IF_IN_MULTICAST_PKTS = f"{IFXTABLE}.2"
IF_IN_BROADCAST_PKTS = f"{IFXTABLE}.3"
IF_OUT_MULTICAST_PKTS = f"{IFXTABLE}.4"
IF_OUT_BROADCAST_PKTS = f"{IFXTABLE}.5"
IF_HC_IN_OCTETS = f"{IFXTABLE}.6"
IF_HC_IN_UCAST_PKTS = f"{IFXTABLE}.7"
IF_HC_IN_MULTICAST_PKTS = f"{IFXTABLE}.8"
IF_HC_IN_BROADCAST_PKTS = f"{IFXTABLE}.9"
IF_HC_OUT_OCTETS = f"{IFXTABLE}.10"
IF_HC_OUT_UCAST_PKTS = f"{IFXTABLE}.11"
IF_HC_OUT_MULTICAST_PKTS = f"{IFXTABLE}.12"
IF_HC_OUT_BROADCAST_PKTS = f"{IFXTABLE}.13"
IF_ALIAS = f"{IFXTABLE}.18"
IF_COUNTER_DISCONTINUITY = f"{IFXTABLE}.19"

# --- ifTable (32-bit legacy + status + speed) ---
IFTABLE = "1.3.6.1.2.1.2.2.1"
IF_INDEX = f"{IFTABLE}.1"
IF_DESCR = f"{IFTABLE}.2"
IF_TYPE = f"{IFTABLE}.3"
IF_MTU = f"{IFTABLE}.4"
IF_SPEED = f"{IFTABLE}.5"          # 32-bit bps
IF_PHYS_ADDRESS = f"{IFTABLE}.6"
IF_ADMIN_STATUS = f"{IFTABLE}.7"   # 1=up 2=down 3=testing
IF_OPER_STATUS = f"{IFTABLE}.8"    # 1=up 2=down 3=testing 4=unknown 5=dormant 6=notPresent 7=lowerLayerDown
IF_LAST_CHANGE = f"{IFTABLE}.9"
IF_IN_OCTETS = f"{IFTABLE}.10"     # 32-bit fallback
IF_IN_UCAST_PKTS = f"{IFTABLE}.11"
IF_IN_ERRORS = f"{IFTABLE}.14"
IF_OUT_ERRORS = f"{IFTABLE}.20"
IF_IN_DISCARDS = f"{IFTABLE}.13"
IF_OUT_DISCARDS = f"{IFTABLE}.19"
IF_OUT_OCTETS = f"{IFTABLE}.16"    # 32-bit fallback

# ifHighSpeed = Mbps (gauge). Real bps = value * 1_000_000.
IF_HIGH_SPEED = f"{IFXTABLE}.15"


def ifindex_from_oid(oid: str) -> int:
    """Extract the trailing ifIndex from a column-instance OID like '...1.5'."""
    try:
        return int(oid.rsplit(".", 1)[-1])
    except ValueError:
        return 0
