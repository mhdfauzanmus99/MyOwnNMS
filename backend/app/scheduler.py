"""Background polling scheduler.

APScheduler runs a single job every `poll_interval_seconds`; that job fans each
enabled device out to its own thread so one slow/unreachable device can't stall
the rest. Each worker thread re-reads the device row and calls the poller.
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from apscheduler.schedulers.background import BackgroundScheduler

from . import database, poller
from .config import settings

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None
_executor = ThreadPoolExecutor(max_workers=16, thread_name_prefix="poller")


def _poll_all() -> None:
    devices = database.query("SELECT * FROM devices WHERE enabled=1")
    if not devices:
        return
    futures = {_executor.submit(_safe_poll, d): d for d in devices}
    for fut in as_completed(futures, timeout=settings.poll_interval_seconds + 30):
        try:
            fut.result()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Poll worker error: %s", exc)


def _safe_poll(device: dict) -> None:
    try:
        poller.poll_device(device)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unhandled poller error for device %s: %s", device.get("hostname"), exc)


def start() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        _poll_all,
        "interval",
        seconds=settings.poll_interval_seconds,
        id="poll-all",
        next_run_time=None,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    # Kick off an immediate first poll so the dashboard isn't empty on boot.
    _executor.submit(_poll_all)
    logger.info("Poller scheduler started (interval=%ss)", settings.poll_interval_seconds)


def stop() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def poll_now() -> int:
    """Trigger an immediate poll run on a background thread; returns device count."""
    devices = database.query("SELECT * FROM devices WHERE enabled=1")
    _executor.submit(_poll_all)
    return len(devices)
