"""Engagement Brain Worker - Periodic processing of enrollments.

This worker runs periodically to:
1. Process all active enrollments and determine next actions
2. Handle scheduled actions that are due
3. Update enrollment stages based on activity
4. Generate pending actions for the brain's recommendations
"""

import asyncio
from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.config import settings
from app.engagement.brain import EngagementBrain
from app.engagement.models import (
    ContactActivity,
    EngagementPipeline,
    PendingAction,
    PipelineEnrollment,
)


class EngagementWorker:
    """Worker for processing engagement enrollments."""

    def __init__(self, db_session_factory: async_sessionmaker) -> None:
        self.db_session_factory = db_session_factory
        self.running = False

    async def start(self, interval_seconds: int = 900) -> None:
        """Start the worker with the specified interval (default: 15 minutes)."""
        self.running = True
        logger.info(
            "Engagement worker starting with interval: {interval}s",
            interval=interval_seconds,
        )

        while self.running:
            try:
                await self.process_all_enrollments()
            except Exception as e:
                logger.exception("Error in engagement worker cycle: {err}", err=str(e))

            await asyncio.sleep(interval_seconds)

    async def stop(self) -> None:
        """Stop the worker."""
        self.running = False
        logger.info("Engagement worker stopped")

    async def process_all_enrollments(self) -> int:
        """Process all active enrollments across all tenants.

        Returns:
            Number of enrollments processed
        """
        async with self.db_session_factory() as db:
            # Get all active enrollments with their pipelines
            result = await db.execute(
                select(PipelineEnrollment)
                .options(
                    selectinload(PipelineEnrollment.contact),
                    selectinload(PipelineEnrollment.pipeline),
                )
                .where(
                    PipelineEnrollment.status == "active",
                )
                .order_by(PipelineEnrollment.last_touch_at.asc().nullsfirst())
            )
            enrollments = result.scalars().all()

            logger.info("Processing {count} active enrollments", count=len(enrollments))

            processed = 0
            for enrollment in enrollments:
                try:
                    await self._process_enrollment(db, enrollment)
                    processed += 1
                except Exception as e:
                    logger.error(
                        "Error processing enrollment {id}: {err}",
                        id=enrollment.id,
                        err=str(e),
                    )

            return processed

    async def _process_enrollment(
        self,
        db: AsyncSession,
        enrollment: PipelineEnrollment,
    ) -> None:
        """Process a single enrollment.

        Steps:
        1. Check if there are pending actions - if so, skip
        2. Check if enough time has passed since last touch
        3. Get activities for the contact
        4. Call brain to analyze and recommend next action
        5. Create pending action if needed
        """
        pipeline = enrollment.pipeline
        if not pipeline.is_active:
            return

        # Check for existing pending actions
        pending_result = await db.execute(
            select(func.count(PendingAction.id)).where(
                PendingAction.enrollment_id == enrollment.id,
                PendingAction.status.in_(["pending", "ready_for_approval", "approved"]),
            )
        )
        pending_count = pending_result.scalar() or 0

        if pending_count > 0:
            logger.debug(
                "Enrollment {id} has {count} pending actions, skipping",
                id=enrollment.id,
                count=pending_count,
            )
            return

        # Check timing
        if not self._should_touch(enrollment, pipeline):
            return

        # Get recent activities
        activities_result = await db.execute(
            select(ContactActivity)
            .where(ContactActivity.contact_id == enrollment.contact_id)
            .order_by(ContactActivity.performed_at.desc())
            .limit(20)
        )
        activities = list(activities_result.scalars().all())

        # Initialize brain
        brain = EngagementBrain(db, enrollment.tenant_id)

        # Analyze and get recommendation
        recommendation = await brain.analyze_contact(enrollment, activities)

        # Create pending action
        action = await brain.create_action_for_enrollment(enrollment, recommendation)

        # Update enrollment touch count
        enrollment.touch_count += 1

        # Update stage if recommended
        if recommendation.new_stage and recommendation.new_stage != enrollment.stage:
            enrollment.stage = recommendation.new_stage
            logger.info(
                "Enrollment {id} stage changed: {old} -> {new}",
                id=enrollment.id,
                old=enrollment.stage,
                new=recommendation.new_stage,
            )

        await db.commit()

        logger.info(
            "Created action for enrollment {id}: {module}:{action}",
            id=enrollment.id,
            module=action.module,
            action=action.action_type,
        )

    def _should_touch(
        self,
        enrollment: PipelineEnrollment,
        pipeline: EngagementPipeline,
    ) -> bool:
        """Check if we should create a new touch for this enrollment."""
        if not enrollment.last_touch_at:
            return True

        min_days = pipeline.min_days_between_touches
        min_interval = timedelta(days=min_days)
        next_touch_at = enrollment.last_touch_at + min_interval

        return datetime.utcnow() >= next_touch_at


class EventHandler:
    """Handler for incoming events/activities.

    This is called when new activities are logged (especially inbound)
    to trigger immediate brain analysis.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def handle_inbound_activity(self, activity: ContactActivity) -> None:
        """Handle an incoming activity (e.g., reply from contact).

        This triggers the brain to:
        1. Analyze the response
        2. Update enrollment stage if needed
        3. Create follow-up action if needed
        """
        if activity.direction != "inbound":
            return

        if not activity.enrollment_id:
            logger.debug("Activity has no enrollment, skipping")
            return

        # Get enrollment
        enrollment_result = await self.db.execute(
            select(PipelineEnrollment)
            .options(
                selectinload(PipelineEnrollment.contact),
                selectinload(PipelineEnrollment.pipeline),
            )
            .where(PipelineEnrollment.id == activity.enrollment_id)
        )
        enrollment = enrollment_result.scalar_one_or_none()

        if not enrollment or enrollment.status != "active":
            return

        # Get last outbound activity
        last_outbound_result = await self.db.execute(
            select(ContactActivity)
            .where(
                ContactActivity.enrollment_id == activity.enrollment_id,
                ContactActivity.direction == "outbound",
                ContactActivity.performed_at < activity.performed_at,
            )
            .order_by(ContactActivity.performed_at.desc())
            .limit(1)
        )
        last_outbound = last_outbound_result.scalar_one_or_none()

        # Initialize brain
        brain = EngagementBrain(self.db, enrollment.tenant_id)

        # Analyze the response
        analysis = await brain.analyze_response(enrollment, activity, last_outbound)

        # Update enrollment based on analysis
        enrollment.last_response_at = datetime.utcnow()

        if analysis.new_stage and analysis.new_stage != enrollment.stage:
            enrollment.stage = analysis.new_stage
            logger.info(
                "Enrollment {id} stage updated from response: {stage}",
                id=enrollment.id,
                stage=analysis.new_stage,
            )

        # Update activity with analysis results
        activity.sentiment = analysis.sentiment
        activity.detected_intent = analysis.intent
        activity.ai_analysis = {
            "urgency": analysis.urgency,
            "recommended_action": analysis.recommended_action,
            "needs_human": analysis.needs_human,
            "reasoning": analysis.reasoning,
        }

        await self.db.commit()

        # If immediate action is needed and not human-required, create action
        if analysis.urgency == "immediate" and not analysis.needs_human:
            # Get recent activities
            activities_result = await self.db.execute(
                select(ContactActivity)
                .where(ContactActivity.contact_id == enrollment.contact_id)
                .order_by(ContactActivity.performed_at.desc())
                .limit(20)
            )
            activities = list(activities_result.scalars().all())

            # Get new recommendation
            recommendation = await brain.analyze_contact(enrollment, activities)

            # Create action
            await brain.create_action_for_enrollment(enrollment, recommendation)
            await self.db.commit()

            logger.info(
                "Created immediate follow-up action for enrollment {id}",
                id=enrollment.id,
            )


async def run_worker() -> None:
    """Entry point for running the worker standalone."""
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    worker = EngagementWorker(session_factory)

    try:
        await worker.start()
    except KeyboardInterrupt:
        await worker.stop()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_worker())
