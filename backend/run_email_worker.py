#!/usr/bin/env python3
"""
Email Marketing Background Worker

Processes:
- Scheduled campaigns (status=scheduled, scheduled_at <= now)
- Sequence enrollments (next_send_at <= now)
- Rate limit counter resets

Usage:
    python run_email_worker.py

Environment Variables:
    DATABASE_URL - PostgreSQL connection string
    SCAN_INTERVAL - Seconds between scans (default: 5)
    MAX_SEND_ERRORS - Errors before pausing campaign (default: 10)
    BATCH_SIZE - Emails per batch (default: 100)
"""

import asyncio
import os
import signal
import sys

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger

from app.emailmarketing.worker import EmailWorker


def setup_logging():
    """Configure logging for the worker."""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>email-worker</cyan> | "
        "<level>{message}</level>",
        level="INFO",
    )
    logger.add(
        "logs/email_worker.log",
        rotation="10 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="DEBUG",
    )


async def main():
    """Main entry point."""
    setup_logging()

    # Configuration from environment
    scan_interval = int(os.getenv("SCAN_INTERVAL", "5"))
    max_send_errors = int(os.getenv("MAX_SEND_ERRORS", "10"))
    batch_size = int(os.getenv("BATCH_SIZE", "100"))

    worker = EmailWorker(
        scan_interval=scan_interval,
        max_send_errors=max_send_errors,
        batch_size=batch_size,
    )

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    def shutdown_handler():
        logger.info("Shutdown-Signal empfangen...")
        worker.stop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_handler)

    logger.info("=" * 50)
    logger.info("Email Marketing Worker")
    logger.info("=" * 50)
    logger.info(f"Scan-Interval: {scan_interval}s")
    logger.info(f"Max Send Errors: {max_send_errors}")
    logger.info(f"Batch Size: {batch_size}")
    logger.info("=" * 50)

    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Worker durch Keyboard-Interrupt gestoppt")
    except Exception as e:
        logger.exception(f"Worker-Fehler: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
