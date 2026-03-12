"""LinkedIn job scheduler.

Checks scheduled jobs and queues them for execution
based on their schedule settings (days, time window).
Jobs run sequentially via the existing worker.
"""

from datetime import date, datetime

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.linkedin.models import LinkedInJobLog, LinkedInScraperJob


class LinkedInScheduler:
    """Scheduler that queues LinkedIn jobs based on their schedule config."""

    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self._last_daily_reset: date | None = None

    async def check_and_queue_jobs(self) -> list[dict]:
        """Check all scheduled jobs and queue eligible ones.

        Returns:
            List of actions taken (for logging/API).
        """
        actions = []
        now = datetime.now()
        current_day = now.weekday()  # 0=Monday, 6=Sunday
        current_time = now.strftime("%H:%M")
        today = now.date()

        async with self.db_session_factory() as db:
            # Find all jobs with scheduling enabled
            result = await db.execute(
                select(LinkedInScraperJob).where(
                    LinkedInScraperJob.schedule_enabled.is_(True),
                    LinkedInScraperJob.status.in_(
                        ["draft", "paused", "completed", "failed"]
                    ),
                )
            )
            jobs = result.scalars().all()

            for job in jobs:
                action = await self._evaluate_job(
                    db, job, current_day, current_time, today
                )
                if action:
                    actions.append(action)

            await db.commit()

        return actions

    async def _evaluate_job(
        self,
        db: AsyncSession,
        job: LinkedInScraperJob,
        current_day: int,
        current_time: str,
        today: date,
    ) -> dict | None:
        """Evaluate a single job and queue it if conditions are met."""
        # Check if today is a scheduled day
        if job.schedule_days and current_day not in job.schedule_days:
            return None

        # Check if we're within the time window
        start_time = job.schedule_start_time or "00:00"
        end_time = job.schedule_end_time or "23:59"

        if not (start_time <= current_time <= end_time):
            return None

        # Check if already ran today (from job logs)
        already_ran = await self._ran_today(db, job.id, today)
        if already_ran:
            return None

        # Reset daily counter and queue the job
        job.profiles_scraped = 0
        job.status = "queued"
        job.error_message = None
        if not job.started_at:
            job.started_at = datetime.utcnow()

        logger.info(
            "Scheduler: queued job {id} ({name}) - day {day}, time {time}",
            id=job.id,
            name=job.name,
            day=current_day,
            time=current_time,
        )

        return {
            "job_id": job.id,
            "job_name": job.name,
            "action": "queued",
            "reason": f"Schedule match: day={current_day}, time={current_time}",
        }

    async def _ran_today(
        self, db: AsyncSession, job_id: int, today: date
    ) -> bool:
        """Check if a job already ran today (has a log entry from today)."""
        result = await db.execute(
            select(func.count(LinkedInJobLog.id)).where(
                LinkedInJobLog.job_id == job_id,
                func.date(LinkedInJobLog.started_at) == today,
            )
        )
        count = result.scalar() or 0
        return count > 0

    async def get_status(self) -> list[dict]:
        """Get scheduler status for all scheduled jobs.

        Returns:
            List of job status dicts for the API.
        """
        now = datetime.now()
        current_day = now.weekday()
        current_time = now.strftime("%H:%M")
        today = now.date()

        async with self.db_session_factory() as db:
            result = await db.execute(
                select(LinkedInScraperJob).where(
                    LinkedInScraperJob.schedule_enabled.is_(True),
                )
            )
            jobs = result.scalars().all()

            statuses = []
            for job in jobs:
                ran_today = await self._ran_today(db, job.id, today)

                # Calculate next run
                in_window = self._is_in_window(
                    job, current_day, current_time
                )

                # Get last log
                log_result = await db.execute(
                    select(LinkedInJobLog)
                    .where(LinkedInJobLog.job_id == job.id)
                    .order_by(LinkedInJobLog.started_at.desc())
                    .limit(1)
                )
                last_log = log_result.scalar_one_or_none()

                statuses.append({
                    "job_id": job.id,
                    "job_name": job.name,
                    "job_status": job.status,
                    "schedule_days": job.schedule_days,
                    "schedule_start_time": job.schedule_start_time,
                    "schedule_end_time": job.schedule_end_time,
                    "daily_limit": job.daily_limit,
                    "profiles_scraped": job.profiles_scraped,
                    "in_schedule_window": in_window,
                    "ran_today": ran_today,
                    "last_run_at": (
                        last_log.started_at.isoformat() if last_log else None
                    ),
                    "last_run_status": (
                        last_log.status if last_log else None
                    ),
                    "last_run_profiles": (
                        last_log.profiles_scraped if last_log else 0
                    ),
                })

            return statuses

    def _is_in_window(
        self, job: LinkedInScraperJob, current_day: int, current_time: str
    ) -> bool:
        """Check if current time is within job's schedule window."""
        if job.schedule_days and current_day not in job.schedule_days:
            return False
        start = job.schedule_start_time or "00:00"
        end = job.schedule_end_time or "23:59"
        return start <= current_time <= end
