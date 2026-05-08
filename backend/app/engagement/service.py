"""Engagement service - CRUD and business logic for pipelines, enrollments, actions."""

from datetime import datetime

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.contacts.models import Contact
from app.engagement.models import (
    ABTest,
    ABTestVariant,
    AttributionRecord,
    ContactActivity,
    EngagementPipeline,
    PendingAction,
    PipelineEnrollment,
    TrackingEvent,
    TrackingLink,
)
from app.engagement.schemas import (
    ABTestCreate,
    ABTestUpdate,
    ActivityCreate,
    BulkEnrollRequest,
    BulkEnrollResponse,
    EngagementDashboard,
    EnrollmentCreate,
    EnrollmentUpdate,
    FunnelStage,
    PendingActionApprove,
    PendingActionComplete,
    PendingActionCreate,
    PendingActionUpdate,
    PipelineCreate,
    PipelineFunnel,
    PipelineStats,
    PipelineUpdate,
    TrackingEventCreate,
    TrackingLinkBulkCreate,
    TrackingLinkCreate,
)
from app.exceptions import DuplicateError, NotFoundError, ValidationError


class PipelineService:
    """Service for engagement pipeline management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, tenant_id: str, data: PipelineCreate) -> EngagementPipeline:
        """Create a new engagement pipeline."""
        # Check for duplicate slug
        existing = await self.db.execute(
            select(EngagementPipeline).where(
                EngagementPipeline.tenant_id == tenant_id,
                EngagementPipeline.slug == data.slug,
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateError("Pipeline", "slug")

        tracking_cfg = data.tracking_config
        if hasattr(tracking_cfg, "model_dump"):
            tracking_cfg = tracking_cfg.model_dump()
        auto_enroll = data.auto_enroll_filter
        if hasattr(auto_enroll, "model_dump"):
            auto_enroll = auto_enroll.model_dump()
        pipeline = EngagementPipeline(
            tenant_id=tenant_id,
            name=data.name,
            slug=data.slug,
            product_name=data.product_name,
            product_description=data.product_description,
            target_audience=data.target_audience,
            channels=data.channels,
            goal=data.goal,
            playbook=data.playbook,
            tone_of_voice=data.tone_of_voice,
            min_days_between_touches=data.min_days_between_touches,
            auto_actions=data.auto_actions,
            tracking_config=tracking_cfg or {},
            auto_enroll_filter=auto_enroll,
            is_active=data.is_active,
        )
        self.db.add(pipeline)
        await self.db.flush()
        await self.db.refresh(pipeline)
        logger.info("Pipeline erstellt: {name} (Tenant: {tenant})", name=data.name, tenant=tenant_id)
        return pipeline

    async def get_by_id(self, tenant_id: str, pipeline_id: int) -> EngagementPipeline:
        """Get a pipeline by ID."""
        result = await self.db.execute(
            select(EngagementPipeline).where(
                EngagementPipeline.id == pipeline_id,
                EngagementPipeline.tenant_id == tenant_id,
            )
        )
        pipeline = result.scalar_one_or_none()
        if not pipeline:
            raise NotFoundError("Pipeline", pipeline_id)
        return pipeline

    async def get_by_slug(self, tenant_id: str, slug: str) -> EngagementPipeline:
        """Get a pipeline by slug."""
        result = await self.db.execute(
            select(EngagementPipeline).where(
                EngagementPipeline.slug == slug,
                EngagementPipeline.tenant_id == tenant_id,
            )
        )
        pipeline = result.scalar_one_or_none()
        if not pipeline:
            raise NotFoundError("Pipeline", slug)
        return pipeline

    async def list_pipelines(
        self, tenant_id: str, is_active: bool | None = None
    ) -> list[EngagementPipeline]:
        """List all pipelines for a tenant."""
        query = select(EngagementPipeline).where(EngagementPipeline.tenant_id == tenant_id)
        if is_active is not None:
            query = query.where(EngagementPipeline.is_active == is_active)
        query = query.order_by(EngagementPipeline.name)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, tenant_id: str, pipeline_id: int, data: PipelineUpdate
    ) -> EngagementPipeline:
        """Update a pipeline."""
        pipeline = await self.get_by_id(tenant_id, pipeline_id)

        update_data = data.model_dump(exclude_unset=True)
        # Pydantic-Submodels (tracking_config, auto_enroll_filter) sind durch
        # model_dump() bereits dicts. Nichts weiter zu tun.
        for key, value in update_data.items():
            setattr(pipeline, key, value)

        await self.db.flush()
        await self.db.refresh(pipeline)
        logger.info("Pipeline aktualisiert: {id}", id=pipeline_id)
        return pipeline

    async def delete(self, tenant_id: str, pipeline_id: int) -> None:
        """Delete a pipeline."""
        pipeline = await self.get_by_id(tenant_id, pipeline_id)

        # Check for active enrollments
        active_count = await self.db.execute(
            select(func.count(PipelineEnrollment.id)).where(
                PipelineEnrollment.pipeline_id == pipeline_id,
                PipelineEnrollment.status == "active",
            )
        )
        if active_count.scalar() > 0:
            raise ValidationError(
                "Pipeline kann nicht gelöscht werden, da noch aktive Enrollments vorhanden sind"
            )

        await self.db.delete(pipeline)
        await self.db.flush()
        logger.info("Pipeline gelöscht: {id}", id=pipeline_id)

    async def get_stats(self, tenant_id: str, pipeline_id: int) -> PipelineStats:
        """Get statistics for a pipeline."""
        pipeline = await self.get_by_id(tenant_id, pipeline_id)

        # Total and active enrollments
        total_result = await self.db.execute(
            select(func.count(PipelineEnrollment.id)).where(
                PipelineEnrollment.pipeline_id == pipeline_id
            )
        )
        total = total_result.scalar() or 0

        active_result = await self.db.execute(
            select(func.count(PipelineEnrollment.id)).where(
                PipelineEnrollment.pipeline_id == pipeline_id,
                PipelineEnrollment.status == "active",
            )
        )
        active = active_result.scalar() or 0

        # Stage counts
        stage_result = await self.db.execute(
            select(PipelineEnrollment.stage, func.count(PipelineEnrollment.id))
            .where(PipelineEnrollment.pipeline_id == pipeline_id)
            .group_by(PipelineEnrollment.stage)
        )
        stage_counts = {row[0]: row[1] for row in stage_result.all()}

        # Pending actions
        pending_result = await self.db.execute(
            select(func.count(PendingAction.id)).where(
                PendingAction.pipeline_id == pipeline_id,
                PendingAction.status.in_(["pending", "ready_for_approval"]),
            )
        )
        pending = pending_result.scalar() or 0

        approval_result = await self.db.execute(
            select(func.count(PendingAction.id)).where(
                PendingAction.pipeline_id == pipeline_id,
                PendingAction.status == "ready_for_approval",
            )
        )
        awaiting = approval_result.scalar() or 0

        # Conversion rate
        converted = stage_counts.get("converted", 0)
        conversion_rate = (converted / total * 100) if total > 0 else 0.0

        return PipelineStats(
            pipeline_id=pipeline_id,
            pipeline_name=pipeline.name,
            total_enrollments=total,
            active_enrollments=active,
            stage_counts=stage_counts,
            pending_actions=pending,
            awaiting_approval=awaiting,
            conversion_rate=round(conversion_rate, 2),
        )

    async def get_funnel(self, tenant_id: str, pipeline_id: int) -> PipelineFunnel:
        """Get funnel data for visualization."""
        pipeline = await self.get_by_id(tenant_id, pipeline_id)

        # Get counts by stage
        result = await self.db.execute(
            select(PipelineEnrollment.stage, func.count(PipelineEnrollment.id))
            .where(PipelineEnrollment.pipeline_id == pipeline_id)
            .group_by(PipelineEnrollment.stage)
        )
        stage_data = {row[0]: row[1] for row in result.all()}

        # Standard stage order
        stage_order = ["lead", "contacted", "engaged", "qualified", "converted", "lost"]
        total = sum(stage_data.values())

        stages = []
        for stage in stage_order:
            count = stage_data.get(stage, 0)
            percentage = (count / total * 100) if total > 0 else 0.0
            stages.append(FunnelStage(stage=stage, count=count, percentage=round(percentage, 1)))

        return PipelineFunnel(
            pipeline_id=pipeline_id,
            pipeline_name=pipeline.name,
            total=total,
            stages=stages,
        )


class EnrollmentService:
    """Service for pipeline enrollment management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def enroll(self, tenant_id: str, data: EnrollmentCreate) -> PipelineEnrollment:
        """Enroll a contact in a pipeline.

        Side effect: if the pipeline's tracking_config has
        ``auto_create_tracking_hash=True`` and the contact has no
        tracking_hash yet, one is generated here so outgoing letters,
        emails and links can include a stable identifier.
        """
        from app.contacts.utils import generate_tracking_hash

        # Check for duplicate enrollment
        existing = await self.db.execute(
            select(PipelineEnrollment).where(
                PipelineEnrollment.contact_id == data.contact_id,
                PipelineEnrollment.pipeline_id == data.pipeline_id,
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateError("Enrollment", "contact_id + pipeline_id")

        # Validate contact exists
        contact_result = await self.db.execute(
            select(Contact).where(
                Contact.id == data.contact_id,
                Contact.tenant_id == tenant_id,
            )
        )
        contact = contact_result.scalar_one_or_none()
        if not contact:
            raise NotFoundError("Contact", data.contact_id)

        # Validate pipeline exists
        pipeline_result = await self.db.execute(
            select(EngagementPipeline).where(
                EngagementPipeline.id == data.pipeline_id,
                EngagementPipeline.tenant_id == tenant_id,
            )
        )
        pipeline = pipeline_result.scalar_one_or_none()
        if not pipeline:
            raise NotFoundError("Pipeline", data.pipeline_id)

        # Auto-create tracking hash if pipeline configured + contact lacks one
        tracking_cfg = pipeline.tracking_config or {}
        if tracking_cfg.get("auto_create_tracking_hash") and not contact.tracking_hash:
            contact.tracking_hash = generate_tracking_hash()
            logger.info(
                "Auto-created tracking_hash for contact {cid} via pipeline {pid}",
                cid=contact.id,
                pid=pipeline.id,
            )

        enrollment = PipelineEnrollment(
            tenant_id=tenant_id,
            contact_id=data.contact_id,
            pipeline_id=data.pipeline_id,
            source_module=data.source_module,
            source_campaign=data.source_campaign,
            source_context=data.source_context,
        )
        self.db.add(enrollment)
        await self.db.flush()
        await self.db.refresh(enrollment)
        logger.info(
            "Contact {contact} enrolled in pipeline {pipeline}",
            contact=data.contact_id,
            pipeline=data.pipeline_id,
        )
        return enrollment

    async def bulk_enroll(
        self, tenant_id: str, data: BulkEnrollRequest
    ) -> BulkEnrollResponse:
        """Enroll multiple contacts in a pipeline."""
        enrolled = 0
        skipped = 0
        errors = []

        for contact_id in data.contact_ids:
            try:
                await self.enroll(
                    tenant_id,
                    EnrollmentCreate(
                        contact_id=contact_id,
                        pipeline_id=data.pipeline_id,
                        source_module=data.source_module,
                        source_campaign=data.source_campaign,
                    ),
                )
                enrolled += 1
            except DuplicateError:
                skipped += 1
            except NotFoundError as e:
                errors.append(f"Contact {contact_id}: {e.message}")
            except Exception as e:
                errors.append(f"Contact {contact_id}: {e!s}")

        logger.info(
            "Bulk enrollment: {enrolled} enrolled, {skipped} skipped, {errors} errors",
            enrolled=enrolled,
            skipped=skipped,
            errors=len(errors),
        )
        return BulkEnrollResponse(enrolled=enrolled, skipped=skipped, errors=errors)

    async def get_by_id(self, tenant_id: str, enrollment_id: int) -> PipelineEnrollment:
        """Get an enrollment by ID."""
        result = await self.db.execute(
            select(PipelineEnrollment)
            .options(selectinload(PipelineEnrollment.contact), selectinload(PipelineEnrollment.pipeline))
            .where(
                PipelineEnrollment.id == enrollment_id,
                PipelineEnrollment.tenant_id == tenant_id,
            )
        )
        enrollment = result.scalar_one_or_none()
        if not enrollment:
            raise NotFoundError("Enrollment", enrollment_id)
        return enrollment

    async def list_enrollments(
        self,
        tenant_id: str,
        pipeline_id: int | None = None,
        contact_id: int | None = None,
        status: str | None = None,
        stage: str | None = None,
    ) -> list[PipelineEnrollment]:
        """List enrollments with optional filters."""
        query = (
            select(PipelineEnrollment)
            .options(selectinload(PipelineEnrollment.contact), selectinload(PipelineEnrollment.pipeline))
            .where(PipelineEnrollment.tenant_id == tenant_id)
        )

        if pipeline_id:
            query = query.where(PipelineEnrollment.pipeline_id == pipeline_id)
        if contact_id:
            query = query.where(PipelineEnrollment.contact_id == contact_id)
        if status:
            query = query.where(PipelineEnrollment.status == status)
        if stage:
            query = query.where(PipelineEnrollment.stage == stage)

        query = query.order_by(PipelineEnrollment.enrolled_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, tenant_id: str, enrollment_id: int, data: EnrollmentUpdate
    ) -> PipelineEnrollment:
        """Update an enrollment."""
        enrollment = await self.get_by_id(tenant_id, enrollment_id)

        update_data = data.model_dump(exclude_unset=True)

        # Handle completion
        if update_data.get("status") == "completed":
            update_data["completed_at"] = datetime.utcnow()

        for key, value in update_data.items():
            setattr(enrollment, key, value)

        await self.db.flush()
        await self.db.refresh(enrollment)
        logger.info("Enrollment aktualisiert: {id}", id=enrollment_id)
        return enrollment

    async def record_touch(self, enrollment_id: int) -> None:
        """Record a touch on an enrollment."""
        result = await self.db.execute(
            select(PipelineEnrollment).where(PipelineEnrollment.id == enrollment_id)
        )
        enrollment = result.scalar_one_or_none()
        if enrollment:
            enrollment.touch_count += 1
            enrollment.last_touch_at = datetime.utcnow()
            await self.db.flush()

    async def record_response(self, enrollment_id: int) -> None:
        """Record a response from the contact."""
        result = await self.db.execute(
            select(PipelineEnrollment).where(PipelineEnrollment.id == enrollment_id)
        )
        enrollment = result.scalar_one_or_none()
        if enrollment:
            enrollment.last_response_at = datetime.utcnow()
            # Move to engaged if still in early stages
            if enrollment.stage in ["lead", "contacted"]:
                enrollment.stage = "engaged"
            await self.db.flush()

    async def unenroll(self, tenant_id: str, enrollment_id: int) -> None:
        """Remove an enrollment (stop the pipeline for this contact)."""
        enrollment = await self.get_by_id(tenant_id, enrollment_id)
        enrollment.status = "stopped"
        enrollment.completed_at = datetime.utcnow()
        await self.db.flush()
        logger.info("Enrollment stopped: {id}", id=enrollment_id)


class PendingActionService:
    """Service for pending action management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, tenant_id: str, data: PendingActionCreate) -> PendingAction:
        """Create a new pending action."""
        action = PendingAction(
            tenant_id=tenant_id,
            contact_id=data.contact_id,
            pipeline_id=data.pipeline_id,
            enrollment_id=data.enrollment_id,
            module=data.module,
            action_type=data.action_type,
            context=data.context,
            suggested_content=data.suggested_content,
            priority=data.priority,
            due_at=data.due_at,
            needs_approval=data.needs_approval,
            status="ready_for_approval" if data.needs_approval else "pending",
        )
        self.db.add(action)
        await self.db.flush()
        await self.db.refresh(action)
        logger.info(
            "Pending action created: {module}:{action}",
            module=data.module,
            action=data.action_type,
        )
        return action

    async def get_by_id(self, tenant_id: str, action_id: int) -> PendingAction:
        """Get an action by ID."""
        result = await self.db.execute(
            select(PendingAction)
            .options(
                selectinload(PendingAction.contact),
                selectinload(PendingAction.pipeline),
                selectinload(PendingAction.approver),
            )
            .where(
                PendingAction.id == action_id,
                PendingAction.tenant_id == tenant_id,
            )
        )
        action = result.scalar_one_or_none()
        if not action:
            raise NotFoundError("PendingAction", action_id)
        return action

    async def list_actions(
        self,
        tenant_id: str,
        module: str | None = None,
        status: str | None = None,
        pipeline_id: int | None = None,
        enrollment_id: int | None = None,
    ) -> list[PendingAction]:
        """List pending actions with optional filters."""
        query = (
            select(PendingAction)
            .options(selectinload(PendingAction.contact), selectinload(PendingAction.pipeline))
            .where(PendingAction.tenant_id == tenant_id)
        )

        if module:
            query = query.where(PendingAction.module == module)
        if status:
            query = query.where(PendingAction.status == status)
        if pipeline_id:
            query = query.where(PendingAction.pipeline_id == pipeline_id)
        if enrollment_id:
            query = query.where(PendingAction.enrollment_id == enrollment_id)

        query = query.order_by(
            PendingAction.priority.desc(),
            PendingAction.due_at.asc().nullslast(),
            PendingAction.created_at.asc(),
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_approval_queue(
        self, tenant_id: str, module: str | None = None
    ) -> list[PendingAction]:
        """Get actions awaiting approval."""
        return await self.list_actions(
            tenant_id, module=module, status="ready_for_approval"
        )

    async def update(
        self, tenant_id: str, action_id: int, data: PendingActionUpdate
    ) -> PendingAction:
        """Update a pending action."""
        action = await self.get_by_id(tenant_id, action_id)

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(action, key, value)

        await self.db.flush()
        await self.db.refresh(action)
        logger.info("Pending action aktualisiert: {id}", id=action_id)
        return action

    async def approve(
        self, tenant_id: str, action_id: int, user_id: int, data: PendingActionApprove
    ) -> PendingAction:
        """Approve a pending action."""
        action = await self.get_by_id(tenant_id, action_id)

        if action.status != "ready_for_approval":
            raise ValidationError(f"Action ist nicht zur Freigabe bereit (Status: {action.status})")

        action.status = "approved"
        action.approved_by = user_id
        action.approved_at = datetime.utcnow()

        if data.modified_content:
            action.suggested_content = data.modified_content

        await self.db.flush()
        await self.db.refresh(action)
        logger.info("Action approved: {id} by user {user}", id=action_id, user=user_id)
        return action

    async def complete(
        self, tenant_id: str, action_id: int, data: PendingActionComplete
    ) -> PendingAction:
        """Mark an action as completed."""
        action = await self.get_by_id(tenant_id, action_id)

        if data.error_message:
            action.status = "failed"
            action.error_message = data.error_message
        else:
            action.status = "completed"

        action.result = data.result
        action.completed_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(action)
        logger.info("Action completed: {id} status={status}", id=action_id, status=action.status)
        return action

    async def cancel(self, tenant_id: str, action_id: int) -> PendingAction:
        """Cancel a pending action."""
        action = await self.get_by_id(tenant_id, action_id)

        if action.status in ["completed", "failed"]:
            raise ValidationError(f"Action kann nicht abgebrochen werden (Status: {action.status})")

        action.status = "cancelled"
        action.completed_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(action)
        logger.info("Action cancelled: {id}", id=action_id)
        return action


class ActivityService:
    """Service for contact activity management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log_activity(
        self, tenant_id: str, user_id: int | None, data: ActivityCreate
    ) -> ContactActivity:
        """Log a contact activity."""
        activity = ContactActivity(
            tenant_id=tenant_id,
            contact_id=data.contact_id,
            pipeline_id=data.pipeline_id,
            enrollment_id=data.enrollment_id,
            channel=data.channel,
            activity_type=data.activity_type,
            direction=data.direction,
            subject=data.subject,
            content=data.content,
            source_module=data.source_module,
            source_action_id=data.source_action_id,
            external_id=data.external_id,
            sentiment=data.sentiment,
            detected_intent=data.detected_intent,
            status=data.status,
            metadata_=data.metadata_,
            performed_by=user_id,
            performed_at=data.performed_at or datetime.utcnow(),
        )
        self.db.add(activity)
        await self.db.flush()
        await self.db.refresh(activity)
        logger.info(
            "Activity logged: {channel}:{type} for contact {contact}",
            channel=data.channel,
            type=data.activity_type,
            contact=data.contact_id,
        )
        return activity

    async def get_by_id(self, tenant_id: str, activity_id: int) -> ContactActivity:
        """Get an activity by ID."""
        result = await self.db.execute(
            select(ContactActivity)
            .options(selectinload(ContactActivity.performer), selectinload(ContactActivity.pipeline))
            .where(
                ContactActivity.id == activity_id,
                ContactActivity.tenant_id == tenant_id,
            )
        )
        activity = result.scalar_one_or_none()
        if not activity:
            raise NotFoundError("ContactActivity", activity_id)
        return activity

    async def list_for_contact(
        self, tenant_id: str, contact_id: int, limit: int = 50
    ) -> list[ContactActivity]:
        """Get activity timeline for a contact."""
        result = await self.db.execute(
            select(ContactActivity)
            .options(selectinload(ContactActivity.performer), selectinload(ContactActivity.pipeline))
            .where(
                ContactActivity.tenant_id == tenant_id,
                ContactActivity.contact_id == contact_id,
            )
            .order_by(ContactActivity.performed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_for_enrollment(
        self, tenant_id: str, enrollment_id: int
    ) -> list[ContactActivity]:
        """Get activities for a specific enrollment."""
        result = await self.db.execute(
            select(ContactActivity)
            .options(selectinload(ContactActivity.performer))
            .where(
                ContactActivity.tenant_id == tenant_id,
                ContactActivity.enrollment_id == enrollment_id,
            )
            .order_by(ContactActivity.performed_at.desc())
        )
        return list(result.scalars().all())

    async def get_recent(
        self, tenant_id: str, limit: int = 20, channel: str | None = None
    ) -> list[ContactActivity]:
        """Get recent activities across all contacts."""
        query = (
            select(ContactActivity)
            .options(selectinload(ContactActivity.performer))
            .where(ContactActivity.tenant_id == tenant_id)
        )

        if channel:
            query = query.where(ContactActivity.channel == channel)

        query = query.order_by(ContactActivity.performed_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())


class EngagementDashboardService:
    """Service for engagement dashboard data."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_dashboard(self, tenant_id: str) -> EngagementDashboard:
        """Get dashboard data for the engagement module."""
        # Pipeline counts
        total_pipelines_result = await self.db.execute(
            select(func.count(EngagementPipeline.id)).where(
                EngagementPipeline.tenant_id == tenant_id
            )
        )
        total_pipelines = total_pipelines_result.scalar() or 0

        active_pipelines_result = await self.db.execute(
            select(func.count(EngagementPipeline.id)).where(
                EngagementPipeline.tenant_id == tenant_id,
                EngagementPipeline.is_active.is_(True),
            )
        )
        active_pipelines = active_pipelines_result.scalar() or 0

        # Enrollment counts
        total_enrollments_result = await self.db.execute(
            select(func.count(PipelineEnrollment.id)).where(
                PipelineEnrollment.tenant_id == tenant_id
            )
        )
        total_enrollments = total_enrollments_result.scalar() or 0

        active_enrollments_result = await self.db.execute(
            select(func.count(PipelineEnrollment.id)).where(
                PipelineEnrollment.tenant_id == tenant_id,
                PipelineEnrollment.status == "active",
            )
        )
        active_enrollments = active_enrollments_result.scalar() or 0

        # Pending actions
        pending_result = await self.db.execute(
            select(func.count(PendingAction.id)).where(
                PendingAction.tenant_id == tenant_id,
                PendingAction.status.in_(["pending", "ready_for_approval", "approved"]),
            )
        )
        pending_actions = pending_result.scalar() or 0

        approval_result = await self.db.execute(
            select(func.count(PendingAction.id)).where(
                PendingAction.tenant_id == tenant_id,
                PendingAction.status == "ready_for_approval",
            )
        )
        awaiting_approval = approval_result.scalar() or 0

        # Today's tasks (actions due today)
        today = datetime.utcnow().date()
        todays_result = await self.db.execute(
            select(func.count(PendingAction.id)).where(
                PendingAction.tenant_id == tenant_id,
                PendingAction.status.in_(["pending", "ready_for_approval", "approved"]),
                func.date(PendingAction.due_at) <= today,
            )
        )
        todays_tasks = todays_result.scalar() or 0

        # Pipeline stats (for active pipelines)
        pipelines_result = await self.db.execute(
            select(EngagementPipeline)
            .where(
                EngagementPipeline.tenant_id == tenant_id,
                EngagementPipeline.is_active.is_(True),
            )
            .limit(10)
        )
        pipelines = list(pipelines_result.scalars().all())

        pipeline_service = PipelineService(self.db)
        pipeline_stats = []
        for pipeline in pipelines:
            stats = await pipeline_service.get_stats(tenant_id, pipeline.id)
            pipeline_stats.append(stats)

        # Recent activities
        activity_service = ActivityService(self.db)
        recent_activities_raw = await activity_service.get_recent(tenant_id, limit=10)
        recent_activities = [
            {
                "id": a.id,
                "channel": a.channel,
                "activity_type": a.activity_type,
                "direction": a.direction,
                "subject": a.subject,
                "status": a.status,
                "sentiment": a.sentiment,
                "performed_at": a.performed_at,
                "performer_name": a.performer.full_name if a.performer else None,
            }
            for a in recent_activities_raw
        ]

        return EngagementDashboard(
            total_pipelines=total_pipelines,
            active_pipelines=active_pipelines,
            total_enrollments=total_enrollments,
            active_enrollments=active_enrollments,
            pending_actions=pending_actions,
            awaiting_approval=awaiting_approval,
            todays_tasks=todays_tasks,
            pipeline_stats=pipeline_stats,
            recent_activities=recent_activities,
        )


# ============== Statistics Engine ==============


class StatisticsService:
    """Comprehensive statistics and analytics for the Engagement module."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_channel_performance(
        self,
        tenant_id: str,
        pipeline_id: int | None = None,
        days: int = 30,
    ) -> dict:
        """Get performance metrics by channel.

        Returns:
            Dict with channel -> {sent, delivered, opened, clicked, replied, conversion_rate}
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        # Base query for activities
        query = select(
            ContactActivity.channel,
            ContactActivity.activity_type,
            func.count(ContactActivity.id).label("count"),
        ).where(
            ContactActivity.tenant_id == tenant_id,
            ContactActivity.performed_at >= cutoff,
        )

        if pipeline_id:
            query = query.where(ContactActivity.pipeline_id == pipeline_id)

        query = query.group_by(ContactActivity.channel, ContactActivity.activity_type)

        result = await self.db.execute(query)
        rows = result.all()

        # Aggregate by channel
        channel_stats = {}
        for channel, activity_type, count in rows:
            if channel not in channel_stats:
                channel_stats[channel] = {
                    "total_activities": 0,
                    "sent": 0,
                    "delivered": 0,
                    "opened": 0,
                    "clicked": 0,
                    "replied": 0,
                    "inbound": 0,
                    "outbound": 0,
                }
            channel_stats[channel]["total_activities"] += count

            # Map activity types to metrics
            if "sent" in activity_type:
                channel_stats[channel]["sent"] += count
                channel_stats[channel]["outbound"] += count
            if "delivered" in activity_type:
                channel_stats[channel]["delivered"] += count
            if "opened" in activity_type or "read" in activity_type:
                channel_stats[channel]["opened"] += count
            if "clicked" in activity_type:
                channel_stats[channel]["clicked"] += count
            if "replied" in activity_type or "received" in activity_type:
                channel_stats[channel]["replied"] += count
                channel_stats[channel]["inbound"] += count

        # Calculate rates
        for channel, stats in channel_stats.items():
            sent = stats["sent"] or 1
            stats["delivery_rate"] = round((stats["delivered"] / sent) * 100, 2)
            stats["open_rate"] = round((stats["opened"] / sent) * 100, 2)
            stats["click_rate"] = round((stats["clicked"] / sent) * 100, 2)
            stats["reply_rate"] = round((stats["replied"] / sent) * 100, 2)

        return channel_stats

    async def get_conversion_funnel(
        self,
        tenant_id: str,
        pipeline_id: int | None = None,
        days: int = 30,
    ) -> dict:
        """Get conversion funnel metrics.

        Returns:
            Dict with stage -> count and conversion rates between stages
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        # Count enrollments by current stage
        query = select(
            PipelineEnrollment.stage,
            func.count(PipelineEnrollment.id).label("count"),
        ).where(
            PipelineEnrollment.tenant_id == tenant_id,
            PipelineEnrollment.enrolled_at >= cutoff,
        )

        if pipeline_id:
            query = query.where(PipelineEnrollment.pipeline_id == pipeline_id)

        query = query.group_by(PipelineEnrollment.stage)

        result = await self.db.execute(query)
        rows = result.all()

        # Stage order for funnel
        stage_order = ["lead", "contacted", "engaged", "qualified", "converted", "lost"]

        funnel = {}
        total = 0
        for stage, count in rows:
            funnel[stage] = count
            if stage != "lost":
                total += count

        # Calculate funnel percentages
        funnel_data = []
        cumulative = total or 1

        for stage in stage_order:
            count = funnel.get(stage, 0)
            percentage = round((count / cumulative) * 100, 1) if cumulative > 0 else 0

            funnel_data.append({
                "stage": stage,
                "count": count,
                "percentage": percentage,
                "from_previous": round((count / (funnel_data[-1]["count"] or 1)) * 100, 1) if funnel_data and funnel_data[-1]["count"] > 0 else 100,
            })

            if stage != "lost":
                cumulative = count or 1

        return {
            "total_enrollments": total + funnel.get("lost", 0),
            "stages": funnel_data,
            "conversion_rate": round((funnel.get("converted", 0) / (total or 1)) * 100, 2),
            "loss_rate": round((funnel.get("lost", 0) / (total + funnel.get("lost", 0) or 1)) * 100, 2),
        }

    async def get_response_time_analytics(
        self,
        tenant_id: str,
        pipeline_id: int | None = None,
        days: int = 30,
    ) -> dict:
        """Get response time analytics.

        Returns:
            Dict with average response times and distribution
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        # Get enrollments with response times
        query = select(
            PipelineEnrollment.id,
            PipelineEnrollment.enrolled_at,
            PipelineEnrollment.last_response_at,
            PipelineEnrollment.last_touch_at,
            PipelineEnrollment.touch_count,
            PipelineEnrollment.stage,
        ).where(
            PipelineEnrollment.tenant_id == tenant_id,
            PipelineEnrollment.enrolled_at >= cutoff,
            PipelineEnrollment.last_response_at.isnot(None),
        )

        if pipeline_id:
            query = query.where(PipelineEnrollment.pipeline_id == pipeline_id)

        result = await self.db.execute(query)
        enrollments = result.all()

        if not enrollments:
            return {
                "total_responses": 0,
                "avg_response_time_hours": 0,
                "avg_touches_to_response": 0,
                "fastest_response_hours": 0,
                "slowest_response_hours": 0,
            }

        response_times = []
        touches_to_response = []

        for _, enrolled_at, response_at, last_touch, touch_count, _ in enrollments:
            if response_at and enrolled_at:
                hours = (response_at - enrolled_at).total_seconds() / 3600
                response_times.append(hours)
            if touch_count:
                touches_to_response.append(touch_count)

        return {
            "total_responses": len(enrollments),
            "avg_response_time_hours": round(sum(response_times) / len(response_times), 2) if response_times else 0,
            "avg_touches_to_response": round(sum(touches_to_response) / len(touches_to_response), 2) if touches_to_response else 0,
            "fastest_response_hours": round(min(response_times), 2) if response_times else 0,
            "slowest_response_hours": round(max(response_times), 2) if response_times else 0,
            "median_response_hours": round(sorted(response_times)[len(response_times) // 2], 2) if response_times else 0,
        }

    async def get_best_performing_patterns(
        self,
        tenant_id: str,
        pipeline_id: int | None = None,
        days: int = 90,
    ) -> dict:
        """Analyze what's working best (Optimization Engine).

        Returns:
            Dict with insights about best performing channels, times, and sequences
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        # Get converted enrollments with their activities
        query = select(
            PipelineEnrollment.id,
            PipelineEnrollment.touch_count,
            PipelineEnrollment.enrolled_at,
            PipelineEnrollment.completed_at,
        ).where(
            PipelineEnrollment.tenant_id == tenant_id,
            PipelineEnrollment.stage == "converted",
            PipelineEnrollment.enrolled_at >= cutoff,
        )

        if pipeline_id:
            query = query.where(PipelineEnrollment.pipeline_id == pipeline_id)

        result = await self.db.execute(query)
        converted_enrollments = result.all()

        # Get first touch channel for converted enrollments
        enrollment_ids = [e[0] for e in converted_enrollments]

        if not enrollment_ids:
            return {
                "total_conversions": 0,
                "best_first_channel": None,
                "channel_breakdown": {},
                "avg_touches_to_convert": 0,
                "avg_days_to_convert": 0,
                "insights": [],
            }

        # First activity per enrollment
        first_activity_query = (
            select(
                ContactActivity.enrollment_id,
                ContactActivity.channel,
                func.min(ContactActivity.performed_at).label("first_touch"),
            )
            .where(
                ContactActivity.enrollment_id.in_(enrollment_ids),
                ContactActivity.direction == "outbound",
            )
            .group_by(ContactActivity.enrollment_id, ContactActivity.channel)
        )

        first_activities = await self.db.execute(first_activity_query)
        first_touches = first_activities.all()

        # Count by first channel
        channel_counts = {}
        for _, channel, _ in first_touches:
            channel_counts[channel] = channel_counts.get(channel, 0) + 1

        best_channel = max(channel_counts.items(), key=lambda x: x[1])[0] if channel_counts else None

        # Calculate averages
        touch_counts = [e[1] for e in converted_enrollments if e[1]]
        days_to_convert = []
        for _, _, enrolled_at, completed_at in converted_enrollments:
            if enrolled_at and completed_at:
                days = (completed_at - enrolled_at).days
                days_to_convert.append(days)

        return {
            "total_conversions": len(converted_enrollments),
            "best_first_channel": best_channel,
            "channel_breakdown": channel_counts,
            "avg_touches_to_convert": round(sum(touch_counts) / len(touch_counts), 1) if touch_counts else 0,
            "avg_days_to_convert": round(sum(days_to_convert) / len(days_to_convert), 1) if days_to_convert else 0,
            "insights": self._generate_insights(channel_counts, touch_counts, days_to_convert),
        }

    def _generate_insights(
        self,
        channel_counts: dict,
        touch_counts: list,
        days_to_convert: list,
    ) -> list[str]:
        """Generate human-readable insights from the data."""
        insights = []

        if channel_counts:
            best_channel = max(channel_counts.items(), key=lambda x: x[1])
            insights.append(f"{best_channel[0]} ist der effektivste Erstkanal mit {best_channel[1]} Conversions")

        if touch_counts:
            avg = sum(touch_counts) / len(touch_counts)
            if avg < 3:
                insights.append("Durchschnittlich nur wenige Touches bis zur Conversion - effiziente Ansprache")
            elif avg > 7:
                insights.append("Viele Touches noetig - eventuell Messaging oder Zielgruppe ueberpruefen")

        if days_to_convert:
            avg_days = sum(days_to_convert) / len(days_to_convert)
            if avg_days < 14:
                insights.append(f"Schnelle Conversion (durchschnittlich {avg_days:.0f} Tage)")
            elif avg_days > 60:
                insights.append(f"Langer Sales Cycle ({avg_days:.0f} Tage) - Nurturing-Strategie empfohlen")

        return insights

    async def get_comprehensive_stats(
        self,
        tenant_id: str,
        pipeline_id: int | None = None,
        days: int = 30,
    ) -> dict:
        """Get all statistics combined."""
        return {
            "channel_performance": await self.get_channel_performance(tenant_id, pipeline_id, days),
            "conversion_funnel": await self.get_conversion_funnel(tenant_id, pipeline_id, days),
            "response_analytics": await self.get_response_time_analytics(tenant_id, pipeline_id, days),
            "optimization_insights": await self.get_best_performing_patterns(tenant_id, pipeline_id, days * 3),
        }


# ============== A/B Testing Service ==============


class ABTestService:
    """Service for A/B test management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, tenant_id: str, data: ABTestCreate) -> ABTest:
        """Create a new A/B test with variants."""
        # Validate pipeline exists
        pipeline_result = await self.db.execute(
            select(EngagementPipeline).where(
                EngagementPipeline.id == data.pipeline_id,
                EngagementPipeline.tenant_id == tenant_id,
            )
        )
        if not pipeline_result.scalar_one_or_none():
            raise NotFoundError("Pipeline", data.pipeline_id)

        # Create traffic split
        traffic_split = {}
        for variant in data.variants:
            traffic_split[variant.name] = variant.weight

        ab_test = ABTest(
            tenant_id=tenant_id,
            pipeline_id=data.pipeline_id,
            name=data.name,
            description=data.description,
            test_type=data.test_type,
            channel=data.channel,
            action_type=data.action_type,
            sample_size=data.sample_size,
            traffic_split=traffic_split,
            status="draft",
            is_active=False,
        )
        self.db.add(ab_test)
        await self.db.flush()

        # Create variants
        for variant_data in data.variants:
            variant = ABTestVariant(
                ab_test_id=ab_test.id,
                name=variant_data.name,
                description=variant_data.description,
                content=variant_data.content,
                subject=variant_data.subject,
                config=variant_data.config,
                weight=variant_data.weight,
                is_control=variant_data.is_control,
            )
            self.db.add(variant)

        await self.db.flush()
        await self.db.refresh(ab_test)
        logger.info("A/B test created: {name}", name=data.name)
        return ab_test

    async def get_by_id(self, tenant_id: str, ab_test_id: int) -> ABTest:
        """Get an A/B test by ID."""
        result = await self.db.execute(
            select(ABTest)
            .options(selectinload(ABTest.variants), selectinload(ABTest.pipeline))
            .where(
                ABTest.id == ab_test_id,
                ABTest.tenant_id == tenant_id,
            )
        )
        ab_test = result.scalar_one_or_none()
        if not ab_test:
            raise NotFoundError("ABTest", ab_test_id)
        return ab_test

    async def list_tests(
        self,
        tenant_id: str,
        pipeline_id: int | None = None,
        status: str | None = None,
    ) -> list[ABTest]:
        """List A/B tests with optional filters."""
        query = (
            select(ABTest)
            .options(selectinload(ABTest.variants), selectinload(ABTest.pipeline))
            .where(ABTest.tenant_id == tenant_id)
        )

        if pipeline_id:
            query = query.where(ABTest.pipeline_id == pipeline_id)
        if status:
            query = query.where(ABTest.status == status)

        query = query.order_by(ABTest.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, tenant_id: str, ab_test_id: int, data: ABTestUpdate
    ) -> ABTest:
        """Update an A/B test."""
        ab_test = await self.get_by_id(tenant_id, ab_test_id)

        update_data = data.model_dump(exclude_unset=True)

        # Handle status changes
        if "status" in update_data:
            new_status = update_data["status"]
            if new_status == "running" and ab_test.status == "draft":
                update_data["started_at"] = datetime.utcnow()
                update_data["is_active"] = True
            elif new_status == "completed":
                update_data["ended_at"] = datetime.utcnow()
                update_data["is_active"] = False
            elif new_status == "paused":
                update_data["is_active"] = False

        for key, value in update_data.items():
            setattr(ab_test, key, value)

        await self.db.flush()
        await self.db.refresh(ab_test)
        logger.info("A/B test updated: {id}", id=ab_test_id)
        return ab_test

    async def delete(self, tenant_id: str, ab_test_id: int) -> None:
        """Delete an A/B test."""
        ab_test = await self.get_by_id(tenant_id, ab_test_id)

        if ab_test.status == "running":
            raise ValidationError("Running test kann nicht gelöscht werden")

        await self.db.delete(ab_test)
        await self.db.flush()
        logger.info("A/B test deleted: {id}", id=ab_test_id)

    async def start(self, tenant_id: str, ab_test_id: int) -> ABTest:
        """Start an A/B test."""
        return await self.update(
            tenant_id, ab_test_id, ABTestUpdate(status="running")
        )

    async def pause(self, tenant_id: str, ab_test_id: int) -> ABTest:
        """Pause an A/B test."""
        return await self.update(
            tenant_id, ab_test_id, ABTestUpdate(status="paused")
        )

    async def complete(self, tenant_id: str, ab_test_id: int, winner_variant_id: int | None = None) -> ABTest:
        """Complete an A/B test and optionally declare a winner."""
        ab_test = await self.get_by_id(tenant_id, ab_test_id)

        ab_test.status = "completed"
        ab_test.ended_at = datetime.utcnow()
        ab_test.is_active = False

        if winner_variant_id:
            ab_test.winner_variant_id = winner_variant_id

        # Calculate results summary
        results = {}
        for variant in ab_test.variants:
            results[variant.name] = {
                "impressions": variant.impressions,
                "clicks": variant.clicks,
                "conversions": variant.conversions,
                "responses": variant.responses,
                "click_rate": round((variant.clicks / max(variant.impressions, 1)) * 100, 2),
                "conversion_rate": round((variant.conversions / max(variant.impressions, 1)) * 100, 2),
                "response_rate": round((variant.responses / max(variant.impressions, 1)) * 100, 2),
            }
        ab_test.results_summary = results

        await self.db.flush()
        await self.db.refresh(ab_test)
        logger.info("A/B test completed: {id}", id=ab_test_id)
        return ab_test

    async def select_variant(self, ab_test_id: int) -> ABTestVariant | None:
        """Select a variant based on traffic weights (for action assignment)."""
        import random

        result = await self.db.execute(
            select(ABTest)
            .options(selectinload(ABTest.variants))
            .where(ABTest.id == ab_test_id, ABTest.is_active.is_(True))
        )
        ab_test = result.scalar_one_or_none()

        if not ab_test or not ab_test.variants:
            return None

        # Weighted random selection
        total_weight = sum(v.weight for v in ab_test.variants)
        random_value = random.uniform(0, total_weight)

        cumulative = 0
        for variant in ab_test.variants:
            cumulative += variant.weight
            if random_value <= cumulative:
                return variant

        return ab_test.variants[-1]

    async def record_impression(self, variant_id: int) -> None:
        """Record an impression for a variant."""
        result = await self.db.execute(
            select(ABTestVariant).where(ABTestVariant.id == variant_id)
        )
        variant = result.scalar_one_or_none()
        if variant:
            variant.impressions += 1
            await self.db.flush()

    async def record_click(self, variant_id: int) -> None:
        """Record a click for a variant."""
        result = await self.db.execute(
            select(ABTestVariant).where(ABTestVariant.id == variant_id)
        )
        variant = result.scalar_one_or_none()
        if variant:
            variant.clicks += 1
            await self.db.flush()

    async def record_conversion(self, variant_id: int) -> None:
        """Record a conversion for a variant."""
        result = await self.db.execute(
            select(ABTestVariant).where(ABTestVariant.id == variant_id)
        )
        variant = result.scalar_one_or_none()
        if variant:
            variant.conversions += 1
            await self.db.flush()

    async def record_response(self, variant_id: int) -> None:
        """Record a response for a variant."""
        result = await self.db.execute(
            select(ABTestVariant).where(ABTestVariant.id == variant_id)
        )
        variant = result.scalar_one_or_none()
        if variant:
            variant.responses += 1
            await self.db.flush()

    async def get_results(self, tenant_id: str, ab_test_id: int) -> dict:
        """Get detailed results for an A/B test."""
        ab_test = await self.get_by_id(tenant_id, ab_test_id)

        variants_data = []
        best_variant = None
        best_conversion_rate = 0

        for variant in ab_test.variants:
            impressions = max(variant.impressions, 1)
            click_rate = round((variant.clicks / impressions) * 100, 2)
            conversion_rate = round((variant.conversions / impressions) * 100, 2)
            response_rate = round((variant.responses / impressions) * 100, 2)

            variant_data = {
                "id": variant.id,
                "name": variant.name,
                "is_control": variant.is_control,
                "impressions": variant.impressions,
                "clicks": variant.clicks,
                "conversions": variant.conversions,
                "responses": variant.responses,
                "click_rate": click_rate,
                "conversion_rate": conversion_rate,
                "response_rate": response_rate,
            }
            variants_data.append(variant_data)

            if conversion_rate > best_conversion_rate:
                best_conversion_rate = conversion_rate
                best_variant = variant_data

        return {
            "ab_test_id": ab_test_id,
            "name": ab_test.name,
            "status": ab_test.status,
            "test_type": ab_test.test_type,
            "started_at": ab_test.started_at,
            "ended_at": ab_test.ended_at,
            "variants": variants_data,
            "best_performing": best_variant,
            "winner_declared": ab_test.winner_variant_id is not None,
            "winner_variant_id": ab_test.winner_variant_id,
        }


# ============== Tracking Link Service ==============


class TrackingLinkService:
    """Service for tracking link management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _generate_token(self) -> str:
        """Generate a unique tracking token."""
        import hashlib
        import time
        import uuid

        unique_string = f"{uuid.uuid4()}{time.time()}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:16]

    def _generate_short_code(self) -> str:
        """Generate a short code for URLs."""
        import random
        import string

        return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))

    async def create(self, tenant_id: str, data: TrackingLinkCreate) -> TrackingLink:
        """Create a new tracking link."""
        # Validate contact exists
        contact_result = await self.db.execute(
            select(Contact).where(
                Contact.id == data.contact_id,
                Contact.tenant_id == tenant_id,
            )
        )
        if not contact_result.scalar_one_or_none():
            raise NotFoundError("Contact", data.contact_id)

        tracking_link = TrackingLink(
            tenant_id=tenant_id,
            contact_id=data.contact_id,
            pipeline_id=data.pipeline_id,
            enrollment_id=data.enrollment_id,
            token=self._generate_token(),
            short_code=self._generate_short_code(),
            target_url=data.target_url,
            utm_source=data.utm_source,
            utm_medium=data.utm_medium,
            utm_campaign=data.utm_campaign,
            utm_content=data.utm_content,
            utm_term=data.utm_term,
            expires_at=data.expires_at,
        )
        self.db.add(tracking_link)
        await self.db.flush()
        await self.db.refresh(tracking_link)
        logger.info(
            "Tracking link created for contact {contact}",
            contact=data.contact_id,
        )
        return tracking_link

    async def bulk_create(
        self, tenant_id: str, data: TrackingLinkBulkCreate
    ) -> list[TrackingLink]:
        """Create tracking links for multiple contacts."""
        links = []
        for contact_id in data.contact_ids:
            try:
                link = await self.create(
                    tenant_id,
                    TrackingLinkCreate(
                        contact_id=contact_id,
                        pipeline_id=data.pipeline_id,
                        target_url=data.target_url,
                        utm_source=data.utm_source,
                        utm_medium=data.utm_medium,
                        utm_campaign=data.utm_campaign,
                        expires_at=data.expires_at,
                    ),
                )
                links.append(link)
            except NotFoundError:
                continue

        logger.info("Bulk tracking links created: {count}", count=len(links))
        return links

    async def get_by_token(self, token: str) -> TrackingLink | None:
        """Get a tracking link by token."""
        result = await self.db.execute(
            select(TrackingLink)
            .options(
                selectinload(TrackingLink.contact),
                selectinload(TrackingLink.pipeline),
            )
            .where(
                TrackingLink.token == token,
                TrackingLink.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, tenant_id: str, link_id: int) -> TrackingLink:
        """Get a tracking link by ID."""
        result = await self.db.execute(
            select(TrackingLink)
            .options(
                selectinload(TrackingLink.contact),
                selectinload(TrackingLink.pipeline),
            )
            .where(
                TrackingLink.id == link_id,
                TrackingLink.tenant_id == tenant_id,
            )
        )
        link = result.scalar_one_or_none()
        if not link:
            raise NotFoundError("TrackingLink", link_id)
        return link

    async def list_links(
        self,
        tenant_id: str,
        contact_id: int | None = None,
        pipeline_id: int | None = None,
        is_active: bool | None = None,
    ) -> list[TrackingLink]:
        """List tracking links with optional filters."""
        query = (
            select(TrackingLink)
            .options(selectinload(TrackingLink.contact))
            .where(TrackingLink.tenant_id == tenant_id)
        )

        if contact_id:
            query = query.where(TrackingLink.contact_id == contact_id)
        if pipeline_id:
            query = query.where(TrackingLink.pipeline_id == pipeline_id)
        if is_active is not None:
            query = query.where(TrackingLink.is_active == is_active)

        query = query.order_by(TrackingLink.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def record_click(self, token: str) -> TrackingLink | None:
        """Record a click on a tracking link."""
        link = await self.get_by_token(token)
        if not link:
            return None

        # Check if expired
        if link.expires_at and link.expires_at < datetime.utcnow():
            return None

        link.click_count += 1
        if not link.first_click_at:
            link.first_click_at = datetime.utcnow()
        link.last_click_at = datetime.utcnow()

        await self.db.flush()
        return link

    async def deactivate(self, tenant_id: str, link_id: int) -> TrackingLink:
        """Deactivate a tracking link."""
        link = await self.get_by_id(tenant_id, link_id)
        link.is_active = False
        await self.db.flush()
        await self.db.refresh(link)
        return link

    def build_tracking_url(
        self, link: TrackingLink, base_url: str = ""
    ) -> str:
        """Build the full tracking URL with UTM parameters."""
        from urllib.parse import urlencode, urlparse, urlunparse

        parsed = urlparse(link.target_url)

        # Build UTM params
        utm_params = {"ref": link.token}
        if link.utm_source:
            utm_params["utm_source"] = link.utm_source
        if link.utm_medium:
            utm_params["utm_medium"] = link.utm_medium
        if link.utm_campaign:
            utm_params["utm_campaign"] = link.utm_campaign
        if link.utm_content:
            utm_params["utm_content"] = link.utm_content
        if link.utm_term:
            utm_params["utm_term"] = link.utm_term

        # Add to existing query string
        existing_query = parsed.query
        new_query = urlencode(utm_params)
        if existing_query:
            full_query = f"{existing_query}&{new_query}"
        else:
            full_query = new_query

        return urlunparse(parsed._replace(query=full_query))


# ============== Tracking Event Service ==============


class TrackingEventService:
    """Service for website tracking events."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.link_service = TrackingLinkService(db)

    def _detect_device_type(self, user_agent: str | None) -> str | None:
        """Detect device type from user agent."""
        if not user_agent:
            return None

        ua_lower = user_agent.lower()
        if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
            return "mobile"
        elif "tablet" in ua_lower or "ipad" in ua_lower:
            return "tablet"
        else:
            return "desktop"

    async def log_event(
        self,
        tenant_id: str,
        data: TrackingEventCreate,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TrackingEvent:
        """Log a tracking event from the pixel."""
        tracking_link = None
        contact_id = None

        # Try to resolve contact from token
        if data.ref:
            tracking_link = await self.link_service.get_by_token(data.ref)
            if tracking_link:
                contact_id = tracking_link.contact_id
                # Record click if page_view
                if data.event in ["page_view", "click"]:
                    await self.link_service.record_click(data.ref)

        event = TrackingEvent(
            tenant_id=tenant_id,
            tracking_link_id=tracking_link.id if tracking_link else None,
            contact_id=contact_id,
            event_type=data.event,
            url=data.url,
            referrer=data.referrer,
            utm_source=data.utm_source or (tracking_link.utm_source if tracking_link else None),
            utm_medium=data.utm_medium or (tracking_link.utm_medium if tracking_link else None),
            utm_campaign=data.utm_campaign or (tracking_link.utm_campaign if tracking_link else None),
            utm_content=data.utm_content or (tracking_link.utm_content if tracking_link else None),
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=self._detect_device_type(user_agent),
            metadata_=data.metadata,
            event_time=data.timestamp or datetime.utcnow(),
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)

        # If we have a contact, update their enrollment stage if appropriate
        if contact_id and tracking_link and tracking_link.enrollment_id:
            enrollment_service = EnrollmentService(self.db)
            try:
                enrollment = await enrollment_service.get_by_id(
                    tenant_id, tracking_link.enrollment_id
                )
                if enrollment.stage in ["lead", "contacted"]:
                    enrollment.stage = "engaged"
                    enrollment.last_response_at = datetime.utcnow()
                    await self.db.flush()
            except NotFoundError:
                pass

        logger.info("Tracking event logged: {event}", event=data.event)
        return event

    async def list_events(
        self,
        tenant_id: str,
        contact_id: int | None = None,
        tracking_link_id: int | None = None,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[TrackingEvent]:
        """List tracking events with filters."""
        query = select(TrackingEvent).where(TrackingEvent.tenant_id == tenant_id)

        if contact_id:
            query = query.where(TrackingEvent.contact_id == contact_id)
        if tracking_link_id:
            query = query.where(TrackingEvent.tracking_link_id == tracking_link_id)
        if event_type:
            query = query.where(TrackingEvent.event_type == event_type)

        query = query.order_by(TrackingEvent.event_time.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_event_summary(
        self,
        tenant_id: str,
        contact_id: int | None = None,
        days: int = 30,
    ) -> dict:
        """Get summary of tracking events."""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        query = select(
            TrackingEvent.event_type,
            func.count(TrackingEvent.id).label("count"),
        ).where(
            TrackingEvent.tenant_id == tenant_id,
            TrackingEvent.event_time >= cutoff,
        )

        if contact_id:
            query = query.where(TrackingEvent.contact_id == contact_id)

        query = query.group_by(TrackingEvent.event_type)
        result = await self.db.execute(query)
        events = {row[0]: row[1] for row in result.all()}

        return {
            "total_events": sum(events.values()),
            "event_breakdown": events,
            "page_views": events.get("page_view", 0),
            "form_submits": events.get("form_submit", 0),
            "clicks": events.get("click", 0) + events.get("cta_click", 0),
        }


# ============== Attribution Service ==============


class AttributionService:
    """Service for conversion attribution."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_conversion(
        self,
        tenant_id: str,
        contact_id: int,
        conversion_type: str,
        conversion_value: float | None = None,
        pipeline_id: int | None = None,
        enrollment_id: int | None = None,
    ) -> AttributionRecord:
        """Record a conversion with attribution data."""
        # Get all activities for this contact to build touchpoint journey
        activities_result = await self.db.execute(
            select(ContactActivity)
            .where(
                ContactActivity.tenant_id == tenant_id,
                ContactActivity.contact_id == contact_id,
                ContactActivity.direction == "outbound",
            )
            .order_by(ContactActivity.performed_at.asc())
        )
        activities = list(activities_result.scalars().all())

        # Build touchpoint list
        touchpoints = []
        for activity in activities:
            touchpoints.append({
                "channel": activity.channel,
                "type": activity.activity_type,
                "at": activity.performed_at.isoformat() if activity.performed_at else None,
            })

        # First and last touch attribution
        first_touch = activities[0] if activities else None
        last_touch = activities[-1] if activities else None

        from decimal import Decimal

        record = AttributionRecord(
            tenant_id=tenant_id,
            contact_id=contact_id,
            pipeline_id=pipeline_id,
            enrollment_id=enrollment_id,
            conversion_type=conversion_type,
            conversion_value=Decimal(str(conversion_value)) if conversion_value else None,
            first_touch_channel=first_touch.channel if first_touch else None,
            first_touch_source=first_touch.source_module if first_touch else None,
            first_touch_at=first_touch.performed_at if first_touch else None,
            last_touch_channel=last_touch.channel if last_touch else None,
            last_touch_source=last_touch.source_module if last_touch else None,
            last_touch_at=last_touch.performed_at if last_touch else None,
            touchpoints=touchpoints,
            touchpoint_count=len(touchpoints),
            converted_at=datetime.utcnow(),
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)

        logger.info(
            "Conversion recorded: {type} for contact {contact}",
            type=conversion_type,
            contact=contact_id,
        )
        return record

    async def list_conversions(
        self,
        tenant_id: str,
        pipeline_id: int | None = None,
        conversion_type: str | None = None,
        days: int = 30,
    ) -> list[AttributionRecord]:
        """List conversion records."""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        query = (
            select(AttributionRecord)
            .where(
                AttributionRecord.tenant_id == tenant_id,
                AttributionRecord.converted_at >= cutoff,
            )
        )

        if pipeline_id:
            query = query.where(AttributionRecord.pipeline_id == pipeline_id)
        if conversion_type:
            query = query.where(AttributionRecord.conversion_type == conversion_type)

        query = query.order_by(AttributionRecord.converted_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_attribution_dashboard(
        self,
        tenant_id: str,
        pipeline_id: int | None = None,
        days: int = 30,
    ) -> dict:
        """Get attribution dashboard data."""
        conversions = await self.list_conversions(tenant_id, pipeline_id, days=days)

        total_conversions = len(conversions)
        total_value = sum(
            float(c.conversion_value) for c in conversions if c.conversion_value
        )

        # Attribution breakdowns
        first_touch_channels = {}
        last_touch_channels = {}
        first_touch_sources = {}
        total_touchpoints = []

        for conversion in conversions:
            if conversion.first_touch_channel:
                first_touch_channels[conversion.first_touch_channel] = (
                    first_touch_channels.get(conversion.first_touch_channel, 0) + 1
                )
            if conversion.last_touch_channel:
                last_touch_channels[conversion.last_touch_channel] = (
                    last_touch_channels.get(conversion.last_touch_channel, 0) + 1
                )
            if conversion.first_touch_source:
                first_touch_sources[conversion.first_touch_source] = (
                    first_touch_sources.get(conversion.first_touch_source, 0) + 1
                )
            total_touchpoints.append(conversion.touchpoint_count)

        return {
            "total_conversions": total_conversions,
            "total_value": round(total_value, 2),
            "conversion_by_channel": first_touch_channels,
            "conversion_by_source": first_touch_sources,
            "avg_touchpoints": round(
                sum(total_touchpoints) / len(total_touchpoints), 1
            ) if total_touchpoints else 0,
            "first_touch_attribution": first_touch_channels,
            "last_touch_attribution": last_touch_channels,
        }
