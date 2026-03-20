"""Run the autopilot background worker.

Usage:
    python run_autopilot_worker.py [--interval SECONDS]

Discovers all users with autopilot_enabled=True automatically.
"""

import argparse
import asyncio

from loguru import logger


def main() -> None:
    parser = argparse.ArgumentParser(description="Autopilot background worker")
    parser.add_argument(
        "--interval",
        type=int,
        default=1800,
        help="Polling interval in seconds (default 1800 = 30 min)",
    )
    args = parser.parse_args()

    logger.info(
        "Starting autopilot worker: interval={i}s",
        i=args.interval,
    )

    from app.assistant.scheduler import run_autopilot_worker_loop

    asyncio.run(run_autopilot_worker_loop(interval_seconds=args.interval))


if __name__ == "__main__":
    main()
