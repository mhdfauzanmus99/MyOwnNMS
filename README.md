# NetPulse — Self-Hosted Network Monitoring System

A lightweight LibreNMS-style NMS that polls network devices over **SNMP**, monitors
link up/down status, and graphs interface utilization — wrapped in a modern,
dark-themed React dashboard.

- **Backend:** Python 3.9 · FastAPI · pysnmp · APScheduler · SQLite (WAL)
- **Frontend:** React 18 · TypeScript · Vite · Tailwind CSS · Recharts
- **Real-time:** SSE-pushed link-flap & threshold alerts → in-app toasts
- **Simulator:** Ships with 3 fake SNMP devices so the dashboard is alive on first run

---

## Prerequisites

You need on your machine:

| Tool | Why | Install |
|------|-----|---------|
| Python 3.9+ | Backend | already on macOS |
| Node.js 18+ + npm | Frontend build | `brew install node` |
| Git (optional) | Versioning | `brew install git` |

Check Node is present before the frontend step:

```bash
node --version   # expect v18+
npm --version
```

---

## Setup (one-time)

From the project root:

```bash
# 1. Python backend deps
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 2. Initialize the database + seed an admin user and the 3 simulated devices
python -m backend.app.init_db

# 3. Frontend deps
cd frontend && npm install && cd ..
```

Or just run the helper:

```bash
bash scripts/setup.sh
```

> **Default login:** `admin` / `admin` — change it in `backend/app/config.py` or via env vars before seeding.

---

## Run

The system has three processes: the **SNMP simulator** (fake devices), the **FastAPI
backend** (poller + API), and the **Vite dev server** (frontend). Start all three:

```bash
bash scripts/run.sh
```

Then open **http://localhost:5173**.

| Service | URL | Notes |
|---------|-----|-------|
| Frontend (dev) | http://localhost:5173 | proxies `/api` to the backend |
| Backend API | http://localhost:8000 | Swagger docs at `/docs` |
| SNMP simulator | UDP :1161/:1162/:1163 | community `public`, SNMPv2c |

---

## What it monitors

- **System info & discovery** — sysDescr, sysName, uptime, location, contact, vendor guess.
- **Interface polling (core)** — per-interface in/out octets (64-bit HC counters), errors,
  discards, admin/oper status, speed, alias/description.
- **Utilization graphs** — `(Δoctets × 8) / (Δseconds × speed) × 100`, precomputed each poll
  so graphs are cheap. Range selector: 1h / 6h / 24h.
- **Real-time link-flap alerts** — oper-status transitions push a toast via SSE.
- **Threshold alerting** — interfaces sustaining > 80% util flip red and log an event;
  auto-resolve when they drop back.

## Adding a real device

In the UI: **Devices → Add Device** → enter name, IP/hostname, port (161), community
(`public`), SNMP version (2c). Or against the API:

```bash
curl -X POST http://localhost:8000/api/devices \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"name":"Core-SW","hostname":"192.168.1.1","port":161,"community":"public","snmp_version":"2c"}'
```

For a real switch, enable SNMP and allow your Mac's IP in the device's community ACL.

---

## Project layout

```
backend/app/        FastAPI app, poller, scheduler, alerts, simulator, routes
frontend/src/       React SPA — pages, components, charts, API client
scripts/            setup.sh + run.sh
data/               SQLite DB (created on init)
```

## Scaling notes

SQLite comfortably handles dozens of devices / thousands of interfaces at a 60s poll.
If you outgrow it, the storage layer is isolated in `database.py` — swap the
`interface_metrics` table for **RRDtool** (what LibreNMS uses) or **InfluxDB** for
long-retention time-series without touching the poller or frontend.
# MyOwnNMS
