#!/usr/bin/env python3
"""Intel module worker — periodic source fetching + briefing composition.

Mirrors ``run_engagement_worker.py``. Runs ``run_pipeline_tick()`` every
``settings.intel_worker_interval_sec`` seconds (default 1800 = 30 min).

Usage::

    python run_intel_worker.py

Environment::

    DATABASE_URL                    PostgreSQL DSN (required)
    INTEL_TEI_URL                   http://tei:80 (default)
    INTEL_WORKER_INTERVAL_SEC       1800 (default)
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger  # noqa: E402

from app.config import settings  # noqa: E402
from app.intel.tasks import run_pipeline_tick  # noqa: E402


def _setup_logging() -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | <cyan>intel-worker</cyan> | "
            "<level>{message}</level>"
        ),
        level="INFO",
    )
    os.makedirs("logs", exist_ok=True)
    logger.add(
        "logs/intel_worker.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
    )


_STOP = asyncio.Event()


def _install_signal_handlers() -> None:
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _STOP.set)


async def main() -> None:
    _setup_logging()
    _install_signal_handlers()
    logger.info(
        "intel worker started (interval={i}s, tei={u})",
        i=settings.intel_worker_interval_sec,
        u=settings.intel_tei_url,
    )

    while not _STOP.is_set():
        try:
            await run_pipeline_tick()
        except Exception:  # noqa: BLE001
            logger.exception("intel tick crashed (continuing)")

        try:
            await asyncio.wait_for(
                _STOP.wait(),
                timeout=settings.intel_worker_interval_sec,
            )
        except asyncio.TimeoutError:
            pass

    logger.info("intel worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
