#!/usr/bin/env python
"""Run the LinkedIn scraper worker manually (headed mode)."""

import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

from app.database import async_session
from app.linkedin.scraper.worker import LinkedInWorker


async def main():
    """Run the worker for one job."""
    print("=" * 60)
    print("LinkedIn Scraper Worker - Headed Mode")
    print("=" * 60)
    print("\nStarting worker... Press Ctrl+C to stop.\n")

    worker = LinkedInWorker(
        db_session_factory=async_session,
        poll_interval=10,  # Check every 10 seconds
    )

    try:
        await worker.start()
    except KeyboardInterrupt:
        print("\nStopping worker...")
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
