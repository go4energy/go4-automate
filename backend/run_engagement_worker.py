#!/usr/bin/env python3
"""
Engagement Brain Background Worker

Processes:
- Active pipeline enrollments
- Determines next actions via AI
- Creates pending actions for modules
- Handles inbound activity events

Usage:
    python run_engagement_worker.py

Environment Variables:
    DATABASE_URL - PostgreSQL connection string
    SCAN_INTERVAL - Seconds between scans (default: 900 = 15 minutes)
"""

import asyncio
import os
import signal
import sys

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.engagement.worker import EngagementWorker


def setup_logging():
    """Configure logging for the worker."""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>engagement-worker</cyan> | "
        "<level>{message}</level>",
        level="INFO",
    )
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    logger.add(
        "logs/engagement_worker.log",
        rotation="10 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="DEBUG",
    )


async def main():
    """Main entry point."""
    setup_logging()

    # Configuration from environment
    scan_interval = int(os.getenv("SCAN_INTERVAL", "900"))  # 15 minutes default

    # Create database connection
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    worker = EngagementWorker(session_factory)

    # Handle shutdown signals
    loop = asyncio.get_event_loop()
    shutdown_task = None

    def shutdown_handler():
        nonlocal shutdown_task
        logger.info("Shutdown-Signal empfangen...")
        shutdown_task = asyncio.create_task(worker.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_handler)

    logger.info("=" * 50)
    logger.info("Engagement Brain Worker")
    logger.info("=" * 50)
    logger.info(f"Scan-Interval: {scan_interval}s ({scan_interval // 60} Minuten)")
    logger.info("=" * 50)

    try:
        await worker.start(interval_seconds=scan_interval)
    except KeyboardInterrupt:
        logger.info("Worker durch Keyboard-Interrupt gestoppt")
    except Exception as e:
        logger.exception(f"Worker-Fehler: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
