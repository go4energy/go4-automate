#!/usr/bin/env python
"""LinkedIn scheduler + worker cron job.

Alles in einem Script:
1. Prüft ob bereits eine Instanz läuft (Lock-File) → skip
2. Scheduler: Prüft DB nach geplanten Jobs → queued
3. Worker: Verarbeitet ALLE queued Jobs nacheinander
4. Beendet sich wenn fertig

Cron (jede Minute):
  * * * * * cd /opt/go4-automate/backend && .venv/bin/python run_linkedin_scheduler.py >> logs/scheduler.log 2>&1
"""

import asyncio
import fcntl
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
os.chdir(SCRIPT_DIR)

from dotenv import load_dotenv

load_dotenv()

import contextlib  # noqa: E402

from loguru import logger  # noqa: E402

from app.database import async_session  # noqa: E402
from app.linkedin.scheduler import LinkedInScheduler  # noqa: E402
from app.linkedin.scraper.worker import LinkedInWorker  # noqa: E402

LOCK_FILE = os.path.join(os.path.dirname(__file__), "logs", ".scheduler.lock")


def acquire_lock() -> object | None:
    """Try to acquire exclusive lock. Returns file handle or None."""
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    lock_fh = open(LOCK_FILE, "w")  # noqa: SIM115
    try:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fh.write(str(os.getpid()))
        lock_fh.flush()
        return lock_fh
    except OSError:
        lock_fh.close()
        return None


async def main() -> None:
    """Run scheduler check + process all queued jobs."""
    # 1. Schedule: Queue eligible jobs
    scheduler = LinkedInScheduler(async_session)
    actions = await scheduler.check_and_queue_jobs()

    for action in actions:
        logger.info(
            "Scheduler: {action} job {id} ({name})",
            action=action["action"],
            id=action["job_id"],
            name=action["job_name"],
        )

    # 2. Worker: Process all queued jobs (one by one)
    worker = LinkedInWorker(
        db_session_factory=async_session,
        poll_interval=0,  # Don't poll, just process
    )

    jobs_processed = 0
    worker.running = True

    while worker.running:
        had_job = await worker._process_next_job()
        if not had_job:
            break
        jobs_processed += 1

    if jobs_processed > 0:
        logger.info("Worker: {count} Jobs verarbeitet", count=jobs_processed)
    elif not actions:
        logger.debug("Scheduler: nichts zu tun")


if __name__ == "__main__":
    lock = acquire_lock()
    if lock is None:
        # Another instance is already running
        sys.exit(0)

    try:
        asyncio.run(main())
    finally:
        lock.close()
        with contextlib.suppress(OSError):
            os.unlink(LOCK_FILE)
