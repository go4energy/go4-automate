"""Run the assistant background worker.

Usage:
    python run_assistant_worker.py [--tenant TENANT] [--user USER_ID] [--interval SECONDS]
"""

import argparse
import asyncio

from loguru import logger


def main() -> None:
    parser = argparse.ArgumentParser(description="Assistant background worker")
    parser.add_argument("--tenant", default="go4energy", help="Tenant ID")
    parser.add_argument("--user", type=int, default=1, help="User ID")
    parser.add_argument(
        "--interval", type=int, default=300, help="Polling interval in seconds"
    )
    args = parser.parse_args()

    logger.info(
        "Starting assistant worker: tenant={t} user={u} interval={i}s",
        t=args.tenant,
        u=args.user,
        i=args.interval,
    )

    from app.assistant.scheduler import run_worker_loop

    asyncio.run(
        run_worker_loop(
            tenant_id=args.tenant,
            user_id=args.user,
            interval_seconds=args.interval,
        )
    )


if __name__ == "__main__":
    main()
