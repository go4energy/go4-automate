#!/usr/bin/env python3
"""Letter Worker — submits PendingActions to Letterxpress.

Single-shot per default (one batch + status sync, then exit). Pass
``--loop`` to run continuously with the given ``--interval`` in seconds.

Usage:
    python run_letter_worker.py                    # one batch + sync, exit
    python run_letter_worker.py --tenant go4energy # explicit tenant
    python run_letter_worker.py --loop --interval 600  # every 10 minutes

Per project policy: never schedule via cron without an explicit go-ahead.
"""

import argparse
import asyncio
import os
import signal
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.config import settings  # noqa: E402
from app.letter.worker import (  # noqa: E402
    process_letter_actions,
    sync_pending_letter_statuses,
)


def _setup_logging() -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | "
        "<cyan>letter-worker</cyan> | <level>{message}</level>",
        level="INFO",
    )


async def _run_once(session_factory, tenant_id: str) -> int:
    async with session_factory() as db:
        stats = await process_letter_actions(db, tenant_id)
        sync = await sync_pending_letter_statuses(db, tenant_id)
        await db.commit()

    logger.info(
        "Run done — picked={p} ok={s} failed={f} skipped={k} | "
        "sync_checked={c} sync_updated={u} sync_delivered={d} sync_errors={e}",
        p=stats.picked, s=stats.succeeded, f=stats.failed, k=stats.skipped,
        c=sync["checked"], u=sync["updated"], d=sync["delivered"], e=sync["errors"],
    )
    if stats.errors:
        for err in stats.errors:
            logger.warning("  · {err}", err=err)
    return stats.failed


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", default="go4energy")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval", type=int, default=600,
                        help="loop interval in seconds (default 600)")
    args = parser.parse_args()

    _setup_logging()
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    logger.info("=" * 50)
    logger.info("Letter Worker — tenant={t}", t=args.tenant)
    logger.info("Mode: {m}", m="loop" if args.loop else "single-shot")
    if args.loop:
        logger.info("Interval: {i}s", i=args.interval)
    logger.info("=" * 50)

    if not args.loop:
        try:
            failed = await _run_once(session_factory, args.tenant)
            return 1 if failed else 0
        finally:
            await engine.dispose()

    stop = asyncio.Event()

    def _shutdown(*_):
        logger.info("Shutdown-Signal empfangen...")
        stop.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _shutdown)

    try:
        while not stop.is_set():
            await _run_once(session_factory, args.tenant)
            try:
                await asyncio.wait_for(stop.wait(), timeout=args.interval)
            except asyncio.TimeoutError:
                pass
    finally:
        await engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
