"""Leadgen worker entry-point.

Usage:
    # Loop mode: poll queued runs every 30s (ctrl+c to stop)
    python run_leadgen_worker.py

    # Single-shot: process exactly one run and exit
    python run_leadgen_worker.py --run-id 5 --tenant go4energy

    # Loop mode with short interval for testing
    python run_leadgen_worker.py --interval 5
"""

import argparse
import asyncio
import sys

from loguru import logger


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Leadgen pipeline worker")
    parser.add_argument(
        "--run-id",
        type=int,
        default=None,
        help="If set: process this run once and exit.",
    )
    parser.add_argument(
        "--tenant",
        type=str,
        default=None,
        help="Required when --run-id is set.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=30.0,
        help="Poll interval in loop mode, seconds (default 30).",
    )
    return parser.parse_args()


async def _process_single(run_id: int, tenant_id: str) -> int:
    from app.database import async_session
    from app.leadgen.worker import run_once

    async with async_session() as db:
        result = await run_once(db, tenant_id=tenant_id, run_id=run_id)
        logger.info("Run {rid} result: {res}", rid=run_id, res=result)
    return 0 if result.get("status") in ("ok", "skipped", "noop") else 1


async def _process_loop(interval: float) -> int:
    from app.database import async_session
    from app.leadgen.worker import run_loop

    logger.info("Starting leadgen worker loop (interval={i}s)", i=interval)
    await run_loop(async_session, poll_interval_seconds=interval)
    return 0


async def _main() -> int:
    args = _parse_args()

    if args.run_id is not None:
        if not args.tenant:
            logger.error("--tenant ist erforderlich wenn --run-id gesetzt ist")
            return 2
        return await _process_single(args.run_id, args.tenant)

    return await _process_loop(args.interval)


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
