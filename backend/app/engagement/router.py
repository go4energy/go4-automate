"""Engagement router - API endpoints for pipelines, enrollments, actions, activities."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.database import get_db
from app.engagement.schemas import (
    ABTestCreate,
    ABTestDetailResponse,
    ABTestResponse,
    ABTestUpdate,
    ActionRecommendation,
    ActivityCreate,
    ActivityListResponse,
    ActivityResponse,
    AttributionDashboard,
    AvailableChannel,
    AvailableChannelsResponse,
    BrainSetupMessage,
    BrainSetupResponse,
    BulkEnrollRequest,
    BulkEnrollResponse,
    ContactAnalyzeRequest,
    EngagementDashboard,
    EnrollmentCreate,
    EnrollmentListResponse,
    EnrollmentResponse,
    EnrollmentUpdate,
    ModulePromptsGenerateRequest,
    ModulePromptsGenerateResponse,
    PendingActionApprove,
    PendingActionComplete,
    PendingActionCreate,
    PendingActionListResponse,
    PendingActionResponse,
    PendingActionUpdate,
    PipelineCreate,
    PipelineCreateFromSetup,
    PipelineCreateFromSetupResponse,
    PipelineFunnel,
    PipelineListResponse,
    PipelineResponse,
    PipelineStats,
    PipelineUpdate,
    PixelCodeResponse,
    PlaybookGenerateRequest,
    PlaybookGenerateResponse,
    PrerequisiteCheckRequest,
    PrerequisiteReport,
    ResponseAnalysis,
    ResponseAnalyzeRequest,
    TrackingEventCreate,
    TrackingEventResponse,
    TrackingLinkBulkCreate,
    TrackingLinkBulkResponse,
    TrackingLinkCreate,
    TrackingLinkResponse,
)
from app.engagement.service import (
    ABTestService,
    ActivityService,
    AttributionService,
    EngagementDashboardService,
    EnrollmentService,
    PendingActionService,
    PipelineService,
    TrackingEventService,
    TrackingLinkService,
)
from app.exceptions import AppError, DuplicateError, NotFoundError, ValidationError
from app.utils.dependencies import get_current_tenant_id

# Main router
router = APIRouter(prefix="/engagement", tags=["engagement"])

# Include sub-routers
from app.engagement.audience_router import router as audience_router  # noqa: E402
from app.engagement.meta_router import router as meta_router  # noqa: E402

router.include_router(meta_router)
router.include_router(audience_router)


# ============== Dashboard ==============


@router.get("/dashboard", response_model=EngagementDashboard)
async def get_dashboard(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get engagement dashboard data."""
    try:
        service = EngagementDashboardService(db)
        return await service.get_dashboard(tenant_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting engagement dashboard")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


# ============== Pipelines ==============


@router.post("/pipelines", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
async def create_pipeline(
    data: PipelineCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new engagement pipeline."""
    try:
        service = PipelineService(db)
        pipeline = await service.create(tenant_id, data)
        await db.commit()
        return pipeline
    except DuplicateError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error creating pipeline")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/pipelines", response_model=list[PipelineListResponse])
async def list_pipelines(
    is_active: bool | None = Query(None),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """List all pipelines."""
    try:
        service = PipelineService(db)
        pipelines = await service.list_pipelines(tenant_id, is_active)
        return pipelines
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error listing pipelines")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/pipelines/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(
    pipeline_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a pipeline by ID."""
    try:
        service = PipelineService(db)
        return await service.get_by_id(tenant_id, pipeline_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting pipeline")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.put("/pipelines/{pipeline_id}", response_model=PipelineResponse)
async def update_pipeline(
    pipeline_id: int,
    data: PipelineUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a pipeline."""
    try:
        service = PipelineService(db)
        pipeline = await service.update(tenant_id, pipeline_id, data)
        await db.commit()
        return pipeline
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error updating pipeline")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.delete("/pipelines/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline(
    pipeline_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a pipeline."""
    try:
        service = PipelineService(db)
        await service.delete(tenant_id, pipeline_id)
        await db.commit()
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error deleting pipeline")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/pipelines/{pipeline_id}/stats", response_model=PipelineStats)
async def get_pipeline_stats(
    pipeline_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get statistics for a pipeline."""
    try:
        service = PipelineService(db)
        return await service.get_stats(tenant_id, pipeline_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting pipeline stats")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/pipelines/{pipeline_id}/funnel", response_model=PipelineFunnel)
async def get_pipeline_funnel(
    pipeline_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get funnel data for a pipeline."""
    try:
        service = PipelineService(db)
        return await service.get_funnel(tenant_id, pipeline_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting pipeline funnel")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


# ============== Enrollments ==============


@router.post("/enrollments", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_contact(
    data: EnrollmentCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Enroll a contact in a pipeline."""
    try:
        service = EnrollmentService(db)
        enrollment = await service.enroll(tenant_id, data)
        await db.commit()
        return enrollment
    except DuplicateError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error enrolling contact")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.post("/enrollments/bulk", response_model=BulkEnrollResponse)
async def bulk_enroll_contacts(
    data: BulkEnrollRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Bulk enroll contacts in a pipeline."""
    try:
        service = EnrollmentService(db)
        result = await service.bulk_enroll(tenant_id, data)
        await db.commit()
        return result
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error bulk enrolling contacts")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/enrollments", response_model=list[EnrollmentListResponse])
async def list_enrollments(
    pipeline_id: int | None = Query(None),
    contact_id: int | None = Query(None),
    status: str | None = Query(None),
    stage: str | None = Query(None),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """List enrollments with optional filters."""
    try:
        service = EnrollmentService(db)
        enrollments = await service.list_enrollments(
            tenant_id, pipeline_id, contact_id, status, stage
        )
        return [
            EnrollmentListResponse(
                id=e.id,
                contact_id=e.contact_id,
                pipeline_id=e.pipeline_id,
                stage=e.stage,
                status=e.status,
                touch_count=e.touch_count,
                last_touch_at=e.last_touch_at,
                last_response_at=e.last_response_at,
                enrolled_at=e.enrolled_at,
                contact_name=e.contact.name if e.contact else None,
                contact_email=e.contact.email if e.contact else None,
                pipeline_name=e.pipeline.name if e.pipeline else None,
            )
            for e in enrollments
        ]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error listing enrollments")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/enrollments/{enrollment_id}", response_model=EnrollmentResponse)
async def get_enrollment(
    enrollment_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get an enrollment by ID."""
    try:
        service = EnrollmentService(db)
        enrollment = await service.get_by_id(tenant_id, enrollment_id)
        return EnrollmentResponse(
            id=enrollment.id,
            tenant_id=enrollment.tenant_id,
            contact_id=enrollment.contact_id,
            pipeline_id=enrollment.pipeline_id,
            source_module=enrollment.source_module,
            source_campaign=enrollment.source_campaign,
            source_context=enrollment.source_context,
            stage=enrollment.stage,
            status=enrollment.status,
            touch_count=enrollment.touch_count,
            last_touch_at=enrollment.last_touch_at,
            last_response_at=enrollment.last_response_at,
            outcome=enrollment.outcome,
            enrolled_at=enrollment.enrolled_at,
            completed_at=enrollment.completed_at,
            created_at=enrollment.created_at,
            updated_at=enrollment.updated_at,
            contact_name=enrollment.contact.name if enrollment.contact else None,
            contact_email=enrollment.contact.email if enrollment.contact else None,
            pipeline_name=enrollment.pipeline.name if enrollment.pipeline else None,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting enrollment")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.put("/enrollments/{enrollment_id}", response_model=EnrollmentResponse)
async def update_enrollment(
    enrollment_id: int,
    data: EnrollmentUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Update an enrollment."""
    try:
        service = EnrollmentService(db)
        enrollment = await service.update(tenant_id, enrollment_id, data)
        await db.commit()
        return enrollment
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error updating enrollment")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.post("/enrollments/{enrollment_id}/unenroll", status_code=status.HTTP_204_NO_CONTENT)
async def unenroll_contact(
    enrollment_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Stop/unenroll a contact from a pipeline."""
    try:
        service = EnrollmentService(db)
        await service.unenroll(tenant_id, enrollment_id)
        await db.commit()
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error unenrolling contact")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


# ============== Pending Actions ==============


@router.post("/actions", response_model=PendingActionResponse, status_code=status.HTTP_201_CREATED)
async def create_action(
    data: PendingActionCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a pending action."""
    try:
        service = PendingActionService(db)
        action = await service.create(tenant_id, data)
        await db.commit()
        return action
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error creating action")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/actions", response_model=list[PendingActionListResponse])
async def list_actions(
    module: str | None = Query(None),
    status: str | None = Query(None),
    pipeline_id: int | None = Query(None),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """List pending actions with optional filters."""
    try:
        service = PendingActionService(db)
        actions = await service.list_actions(tenant_id, module, status, pipeline_id)
        return [
            PendingActionListResponse(
                id=a.id,
                contact_id=a.contact_id,
                pipeline_id=a.pipeline_id,
                module=a.module,
                action_type=a.action_type,
                priority=a.priority,
                due_at=a.due_at,
                needs_approval=a.needs_approval,
                status=a.status,
                created_at=a.created_at,
                contact_name=a.contact.name if a.contact else None,
                pipeline_name=a.pipeline.name if a.pipeline else None,
            )
            for a in actions
        ]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error listing actions")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/actions/approval-queue", response_model=list[PendingActionListResponse])
async def get_approval_queue(
    module: str | None = Query(None),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get actions awaiting approval."""
    try:
        service = PendingActionService(db)
        actions = await service.get_approval_queue(tenant_id, module)
        return [
            PendingActionListResponse(
                id=a.id,
                contact_id=a.contact_id,
                pipeline_id=a.pipeline_id,
                module=a.module,
                action_type=a.action_type,
                priority=a.priority,
                due_at=a.due_at,
                needs_approval=a.needs_approval,
                status=a.status,
                created_at=a.created_at,
                contact_name=a.contact.name if a.contact else None,
                pipeline_name=a.pipeline.name if a.pipeline else None,
            )
            for a in actions
        ]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting approval queue")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/actions/{action_id}", response_model=PendingActionResponse)
async def get_action(
    action_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a pending action by ID."""
    try:
        service = PendingActionService(db)
        action = await service.get_by_id(tenant_id, action_id)
        return PendingActionResponse(
            id=action.id,
            tenant_id=action.tenant_id,
            contact_id=action.contact_id,
            pipeline_id=action.pipeline_id,
            enrollment_id=action.enrollment_id,
            module=action.module,
            action_type=action.action_type,
            context=action.context,
            suggested_content=action.suggested_content,
            priority=action.priority,
            due_at=action.due_at,
            needs_approval=action.needs_approval,
            status=action.status,
            approved_by=action.approved_by,
            approved_at=action.approved_at,
            result=action.result,
            error_message=action.error_message,
            created_at=action.created_at,
            completed_at=action.completed_at,
            contact_name=action.contact.name if action.contact else None,
            contact_email=action.contact.email if action.contact else None,
            pipeline_name=action.pipeline.name if action.pipeline else None,
            approver_name=action.approver.full_name if action.approver else None,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting action")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.put("/actions/{action_id}", response_model=PendingActionResponse)
async def update_action(
    action_id: int,
    data: PendingActionUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a pending action."""
    try:
        service = PendingActionService(db)
        action = await service.update(tenant_id, action_id, data)
        await db.commit()
        return action
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error updating action")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.post("/actions/{action_id}/approve", response_model=PendingActionResponse)
async def approve_action(
    action_id: int,
    data: PendingActionApprove,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a pending action."""
    try:
        service = PendingActionService(db)
        action = await service.approve(tenant_id, action_id, current_user.id, data)
        await db.commit()
        return action
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error approving action")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.post("/actions/{action_id}/complete", response_model=PendingActionResponse)
async def complete_action(
    action_id: int,
    data: PendingActionComplete,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Mark an action as completed."""
    try:
        service = PendingActionService(db)
        action = await service.complete(tenant_id, action_id, data)
        await db.commit()
        return action
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error completing action")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.post("/actions/{action_id}/cancel", response_model=PendingActionResponse)
async def cancel_action(
    action_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending action."""
    try:
        service = PendingActionService(db)
        action = await service.cancel(tenant_id, action_id)
        await db.commit()
        return action
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error cancelling action")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


# ============== Activities ==============


@router.post("/activities", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def log_activity(
    data: ActivityCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Log a contact activity."""
    try:
        service = ActivityService(db)
        activity = await service.log_activity(tenant_id, current_user.id, data)
        await db.commit()
        return activity
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error logging activity")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/activities/contact/{contact_id}", response_model=list[ActivityListResponse])
async def get_contact_activities(
    contact_id: int,
    limit: int = Query(50, ge=1, le=200),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get activity timeline for a contact."""
    try:
        service = ActivityService(db)
        activities = await service.list_for_contact(tenant_id, contact_id, limit)
        return [
            ActivityListResponse(
                id=a.id,
                channel=a.channel,
                activity_type=a.activity_type,
                direction=a.direction,
                subject=a.subject,
                status=a.status,
                sentiment=a.sentiment,
                performed_at=a.performed_at,
                performer_name=a.performer.full_name if a.performer else None,
            )
            for a in activities
        ]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting contact activities")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/activities/enrollment/{enrollment_id}", response_model=list[ActivityListResponse])
async def get_enrollment_activities(
    enrollment_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get activities for a specific enrollment."""
    try:
        service = ActivityService(db)
        activities = await service.list_for_enrollment(tenant_id, enrollment_id)
        return [
            ActivityListResponse(
                id=a.id,
                channel=a.channel,
                activity_type=a.activity_type,
                direction=a.direction,
                subject=a.subject,
                status=a.status,
                sentiment=a.sentiment,
                performed_at=a.performed_at,
                performer_name=a.performer.full_name if a.performer else None,
            )
            for a in activities
        ]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting enrollment activities")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/activities/recent", response_model=list[ActivityListResponse])
async def get_recent_activities(
    limit: int = Query(20, ge=1, le=100),
    channel: str | None = Query(None),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get recent activities across all contacts."""
    try:
        service = ActivityService(db)
        activities = await service.get_recent(tenant_id, limit, channel)
        return [
            ActivityListResponse(
                id=a.id,
                channel=a.channel,
                activity_type=a.activity_type,
                direction=a.direction,
                subject=a.subject,
                status=a.status,
                sentiment=a.sentiment,
                performed_at=a.performed_at,
                performer_name=a.performer.full_name if a.performer else None,
            )
            for a in activities
        ]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting recent activities")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/activities/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get an activity by ID."""
    try:
        service = ActivityService(db)
        activity = await service.get_by_id(tenant_id, activity_id)
        return ActivityResponse(
            id=activity.id,
            tenant_id=activity.tenant_id,
            contact_id=activity.contact_id,
            pipeline_id=activity.pipeline_id,
            enrollment_id=activity.enrollment_id,
            channel=activity.channel,
            activity_type=activity.activity_type,
            direction=activity.direction,
            subject=activity.subject,
            content=activity.content,
            source_module=activity.source_module,
            source_action_id=activity.source_action_id,
            external_id=activity.external_id,
            sentiment=activity.sentiment,
            detected_intent=activity.detected_intent,
            ai_analysis=activity.ai_analysis,
            status=activity.status,
            metadata_=activity.metadata_,
            performed_by=activity.performed_by,
            performed_at=activity.performed_at,
            created_at=activity.created_at,
            performer_name=activity.performer.full_name if activity.performer else None,
            pipeline_name=activity.pipeline.name if activity.pipeline else None,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting activity")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


# ============== Brain Setup ==============


@router.post("/brain/setup-chat", response_model=BrainSetupResponse)
async def brain_setup_chat(
    data: BrainSetupMessage,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Chat with the brain for pipeline setup."""
    try:
        from app.engagement.brain import EngagementBrain

        brain = EngagementBrain(db, tenant_id)
        result = await brain.process_setup_message(data.message, data.conversation_history)
        return BrainSetupResponse(
            message=result["message"],
            pipeline_config=result.get("pipeline_config"),
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error in brain setup chat")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.post("/brain/check-prerequisites", response_model=PrerequisiteReport)
async def check_prerequisites(
    data: PrerequisiteCheckRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Check prerequisites for the requested channels."""
    try:
        from app.engagement.brain import EngagementBrain

        brain = EngagementBrain(db, tenant_id)
        report = await brain.check_prerequisites(data.channels)
        return PrerequisiteReport(**report.to_dict())
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error checking prerequisites")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.post("/brain/generate-playbook", response_model=PlaybookGenerateResponse)
async def generate_playbook(
    data: PlaybookGenerateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate a playbook for a pipeline."""
    try:
        from app.engagement.brain import EngagementBrain

        brain = EngagementBrain(db, tenant_id)
        playbook = await brain.generate_playbook(data.pipeline_config)
        return PlaybookGenerateResponse(playbook=playbook)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error generating playbook")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.post("/brain/generate-module-prompts", response_model=ModulePromptsGenerateResponse)
async def generate_module_prompts(
    data: ModulePromptsGenerateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate module-specific prompts for a pipeline."""
    try:
        from app.engagement.brain import EngagementBrain

        brain = EngagementBrain(db, tenant_id)
        prompts = await brain.generate_module_prompts(data.pipeline_config)
        return ModulePromptsGenerateResponse(prompts=prompts)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error generating module prompts")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/brain/available-channels", response_model=AvailableChannelsResponse)
async def get_available_channels(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get available channels with their capabilities."""
    try:
        from app.engagement.brain import EngagementBrain

        brain = EngagementBrain(db, tenant_id)
        channels_data = brain.get_available_channels()
        channels = [AvailableChannel(**ch) for ch in channels_data]
        return AvailableChannelsResponse(channels=channels)
    except Exception:
        logger.exception("Error getting available channels")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.post("/brain/create-pipeline-from-setup", response_model=PipelineCreateFromSetupResponse)
async def create_pipeline_from_setup(
    data: PipelineCreateFromSetup,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a pipeline from the setup wizard with all generated content."""
    try:
        from app.engagement.brain import EngagementBrain

        brain = EngagementBrain(db, tenant_id)
        config = data.pipeline_config

        # Check prerequisites if requested
        prerequisites = None
        if data.check_prerequisites and config.get("channels"):
            prerequisites_report = await brain.check_prerequisites(config["channels"])
            prerequisites = PrerequisiteReport(**prerequisites_report.to_dict())

        # Generate playbook if requested
        playbook = None
        if data.generate_playbook:
            playbook = await brain.generate_playbook(config)

        # Generate module prompts if requested
        module_prompts = None
        if data.generate_module_prompts:
            module_prompts = await brain.generate_module_prompts(config)

        # Create the pipeline
        pipeline_service = PipelineService(db)
        pipeline_data = PipelineCreate(
            name=config.get("name", "Neue Pipeline"),
            slug=config.get("slug", "neue-pipeline"),
            product_name=config.get("product_name"),
            product_description=config.get("product_description"),
            target_audience=config.get("target_audience"),
            channels=config.get("channels", []),
            goal=config.get("goal"),
            playbook=playbook,
            tone_of_voice=config.get("tone_of_voice", "professionell"),
        )
        pipeline = await pipeline_service.create(tenant_id, pipeline_data)

        # Save module prompts if generated
        if module_prompts:
            await brain.save_module_prompts(pipeline, module_prompts)

        await db.commit()

        return PipelineCreateFromSetupResponse(
            pipeline=pipeline,
            playbook=playbook,
            module_prompts=module_prompts,
            prerequisites=prerequisites,
        )
    except DuplicateError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error creating pipeline from setup")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


# ============== Brain Runtime ==============


@router.post("/brain/analyze-contact", response_model=ActionRecommendation)
async def analyze_contact(
    data: ContactAnalyzeRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Analyze a contact and get next action recommendation."""
    try:
        from app.engagement.brain import EngagementBrain

        # Get enrollment
        enrollment_service = EnrollmentService(db)
        enrollment = await enrollment_service.get_by_id(tenant_id, data.enrollment_id)

        # Get recent activities
        activity_service = ActivityService(db)
        activities = await activity_service.list_for_enrollment(tenant_id, data.enrollment_id)

        # Analyze
        brain = EngagementBrain(db, tenant_id)
        recommendation = await brain.analyze_contact(enrollment, activities)

        return ActionRecommendation(
            channel=recommendation.channel,
            action=recommendation.action,
            content_suggestion=recommendation.content_suggestion,
            new_stage=recommendation.new_stage,
            needs_approval=recommendation.needs_approval,
            reasoning=recommendation.reasoning,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error analyzing contact")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.post("/brain/analyze-response", response_model=ResponseAnalysis)
async def analyze_response(
    data: ResponseAnalyzeRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Analyze an incoming response from a contact."""
    try:
        from sqlalchemy import select

        from app.engagement.brain import EngagementBrain
        from app.engagement.models import ContactActivity

        # Get the incoming activity
        activity_service = ActivityService(db)
        incoming_activity = await activity_service.get_by_id(tenant_id, data.activity_id)

        if not incoming_activity.enrollment_id:
            raise ValidationError("Activity ist keinem Enrollment zugeordnet")

        # Get enrollment
        enrollment_service = EnrollmentService(db)
        enrollment = await enrollment_service.get_by_id(tenant_id, incoming_activity.enrollment_id)

        # Get last outbound activity
        result = await db.execute(
            select(ContactActivity)
            .where(
                ContactActivity.enrollment_id == incoming_activity.enrollment_id,
                ContactActivity.direction == "outbound",
                ContactActivity.performed_at < incoming_activity.performed_at,
            )
            .order_by(ContactActivity.performed_at.desc())
            .limit(1)
        )
        last_outbound = result.scalar_one_or_none()

        # Analyze
        brain = EngagementBrain(db, tenant_id)
        analysis = await brain.analyze_response(enrollment, incoming_activity, last_outbound)

        return ResponseAnalysis(
            sentiment=analysis.sentiment,
            intent=analysis.intent,
            urgency=analysis.urgency,
            new_stage=analysis.new_stage,
            recommended_action=analysis.recommended_action,
            draft_response=analysis.draft_response,
            needs_human=analysis.needs_human,
            reasoning=analysis.reasoning,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error analyzing response")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


# ============== Statistics Engine ==============


@router.get("/statistics")
async def get_comprehensive_statistics(
    pipeline_id: int | None = None,
    days: int = Query(default=30, ge=1, le=365),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive engagement statistics.

    Returns channel performance, conversion funnel, response analytics, and optimization insights.
    """
    try:
        from app.engagement.service import StatisticsService

        service = StatisticsService(db)
        return await service.get_comprehensive_stats(tenant_id, pipeline_id, days)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting comprehensive statistics")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/statistics/channels")
async def get_channel_performance(
    pipeline_id: int | None = None,
    days: int = Query(default=30, ge=1, le=365),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get performance metrics by channel."""
    try:
        from app.engagement.service import StatisticsService

        service = StatisticsService(db)
        return await service.get_channel_performance(tenant_id, pipeline_id, days)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting channel performance")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/statistics/funnel")
async def get_conversion_funnel(
    pipeline_id: int | None = None,
    days: int = Query(default=30, ge=1, le=365),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get conversion funnel metrics."""
    try:
        from app.engagement.service import StatisticsService

        service = StatisticsService(db)
        return await service.get_conversion_funnel(tenant_id, pipeline_id, days)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting conversion funnel")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/statistics/response-times")
async def get_response_time_analytics(
    pipeline_id: int | None = None,
    days: int = Query(default=30, ge=1, le=365),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get response time analytics."""
    try:
        from app.engagement.service import StatisticsService

        service = StatisticsService(db)
        return await service.get_response_time_analytics(tenant_id, pipeline_id, days)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting response time analytics")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/statistics/optimization")
async def get_optimization_insights(
    pipeline_id: int | None = None,
    days: int = Query(default=90, ge=1, le=365),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get optimization insights - what's working best."""
    try:
        from app.engagement.service import StatisticsService

        service = StatisticsService(db)
        return await service.get_best_performing_patterns(tenant_id, pipeline_id, days)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting optimization insights")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


# ============== A/B Testing ==============


@router.post("/ab-tests", response_model=ABTestDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_ab_test(
    data: ABTestCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new A/B test."""
    try:
        service = ABTestService(db)
        ab_test = await service.create(tenant_id, data)
        await db.commit()
        # Refresh to get variants
        ab_test = await service.get_by_id(tenant_id, ab_test.id)
        return _build_ab_test_detail_response(ab_test)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error creating A/B test")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/ab-tests", response_model=list[ABTestResponse])
async def list_ab_tests(
    pipeline_id: int | None = Query(None),
    status: str | None = Query(None),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """List A/B tests with optional filters."""
    try:
        service = ABTestService(db)
        tests = await service.list_tests(tenant_id, pipeline_id, status)
        return [_build_ab_test_response(t) for t in tests]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error listing A/B tests")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/ab-tests/{ab_test_id}", response_model=ABTestDetailResponse)
async def get_ab_test(
    ab_test_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get an A/B test by ID."""
    try:
        service = ABTestService(db)
        ab_test = await service.get_by_id(tenant_id, ab_test_id)
        return _build_ab_test_detail_response(ab_test)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting A/B test")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.put("/ab-tests/{ab_test_id}", response_model=ABTestDetailResponse)
async def update_ab_test(
    ab_test_id: int,
    data: ABTestUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Update an A/B test."""
    try:
        service = ABTestService(db)
        ab_test = await service.update(tenant_id, ab_test_id, data)
        await db.commit()
        return _build_ab_test_detail_response(ab_test)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error updating A/B test")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.delete("/ab-tests/{ab_test_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ab_test(
    ab_test_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete an A/B test."""
    try:
        service = ABTestService(db)
        await service.delete(tenant_id, ab_test_id)
        await db.commit()
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error deleting A/B test")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.post("/ab-tests/{ab_test_id}/start", response_model=ABTestDetailResponse)
async def start_ab_test(
    ab_test_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Start an A/B test."""
    try:
        service = ABTestService(db)
        ab_test = await service.start(tenant_id, ab_test_id)
        await db.commit()
        return _build_ab_test_detail_response(ab_test)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error starting A/B test")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.post("/ab-tests/{ab_test_id}/pause", response_model=ABTestDetailResponse)
async def pause_ab_test(
    ab_test_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Pause an A/B test."""
    try:
        service = ABTestService(db)
        ab_test = await service.pause(tenant_id, ab_test_id)
        await db.commit()
        return _build_ab_test_detail_response(ab_test)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error pausing A/B test")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.post("/ab-tests/{ab_test_id}/complete", response_model=ABTestDetailResponse)
async def complete_ab_test(
    ab_test_id: int,
    winner_variant_id: int | None = Query(None),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Complete an A/B test and optionally declare a winner."""
    try:
        service = ABTestService(db)
        ab_test = await service.complete(tenant_id, ab_test_id, winner_variant_id)
        await db.commit()
        return _build_ab_test_detail_response(ab_test)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error completing A/B test")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/ab-tests/{ab_test_id}/results")
async def get_ab_test_results(
    ab_test_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed results for an A/B test."""
    try:
        service = ABTestService(db)
        return await service.get_results(tenant_id, ab_test_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting A/B test results")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


def _build_ab_test_response(ab_test) -> ABTestResponse:
    """Build ABTestResponse from model."""
    total_impressions = sum(v.impressions for v in ab_test.variants) if ab_test.variants else 0
    return ABTestResponse(
        id=ab_test.id,
        tenant_id=ab_test.tenant_id,
        pipeline_id=ab_test.pipeline_id,
        name=ab_test.name,
        description=ab_test.description,
        test_type=ab_test.test_type,
        channel=ab_test.channel,
        action_type=ab_test.action_type,
        status=ab_test.status,
        is_active=ab_test.is_active,
        sample_size=ab_test.sample_size,
        traffic_split=ab_test.traffic_split,
        started_at=ab_test.started_at,
        ended_at=ab_test.ended_at,
        winner_variant_id=ab_test.winner_variant_id,
        results_summary=ab_test.results_summary,
        created_at=ab_test.created_at,
        updated_at=ab_test.updated_at,
        pipeline_name=ab_test.pipeline.name if ab_test.pipeline else None,
        variant_count=len(ab_test.variants) if ab_test.variants else 0,
        total_impressions=total_impressions,
    )


def _build_ab_test_detail_response(ab_test) -> ABTestDetailResponse:
    """Build ABTestDetailResponse from model."""
    from app.engagement.schemas import ABTestVariantResponse

    variants = []
    total_impressions = 0
    for v in ab_test.variants:
        impressions = max(v.impressions, 1)
        total_impressions += v.impressions
        variants.append(ABTestVariantResponse(
            id=v.id,
            ab_test_id=v.ab_test_id,
            name=v.name,
            description=v.description,
            content=v.content,
            subject=v.subject,
            config=v.config,
            weight=v.weight,
            impressions=v.impressions,
            clicks=v.clicks,
            conversions=v.conversions,
            responses=v.responses,
            is_control=v.is_control,
            created_at=v.created_at,
            updated_at=v.updated_at,
            click_rate=round((v.clicks / impressions) * 100, 2),
            conversion_rate=round((v.conversions / impressions) * 100, 2),
            response_rate=round((v.responses / impressions) * 100, 2),
        ))

    return ABTestDetailResponse(
        id=ab_test.id,
        tenant_id=ab_test.tenant_id,
        pipeline_id=ab_test.pipeline_id,
        name=ab_test.name,
        description=ab_test.description,
        test_type=ab_test.test_type,
        channel=ab_test.channel,
        action_type=ab_test.action_type,
        status=ab_test.status,
        is_active=ab_test.is_active,
        sample_size=ab_test.sample_size,
        traffic_split=ab_test.traffic_split,
        started_at=ab_test.started_at,
        ended_at=ab_test.ended_at,
        winner_variant_id=ab_test.winner_variant_id,
        results_summary=ab_test.results_summary,
        created_at=ab_test.created_at,
        updated_at=ab_test.updated_at,
        pipeline_name=ab_test.pipeline.name if ab_test.pipeline else None,
        variant_count=len(variants),
        total_impressions=total_impressions,
        variants=variants,
    )


# ============== Tracking Links ==============


@router.post("/tracking/links", response_model=TrackingLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_tracking_link(
    data: TrackingLinkCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a tracking link for a contact."""
    try:
        service = TrackingLinkService(db)
        link = await service.create(tenant_id, data)
        await db.commit()
        return _build_tracking_link_response(link, service)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error creating tracking link")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.post("/tracking/links/bulk", response_model=TrackingLinkBulkResponse)
async def bulk_create_tracking_links(
    data: TrackingLinkBulkCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Create tracking links for multiple contacts."""
    try:
        service = TrackingLinkService(db)
        links = await service.bulk_create(tenant_id, data)
        await db.commit()
        return TrackingLinkBulkResponse(
            created=len(links),
            links=[_build_tracking_link_response(l, service) for l in links],
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error bulk creating tracking links")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/tracking/links", response_model=list[TrackingLinkResponse])
async def list_tracking_links(
    contact_id: int | None = Query(None),
    pipeline_id: int | None = Query(None),
    is_active: bool | None = Query(None),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """List tracking links with optional filters."""
    try:
        service = TrackingLinkService(db)
        links = await service.list_links(tenant_id, contact_id, pipeline_id, is_active)
        return [_build_tracking_link_response(l, service) for l in links]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error listing tracking links")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/tracking/links/{link_id}", response_model=TrackingLinkResponse)
async def get_tracking_link(
    link_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a tracking link by ID."""
    try:
        service = TrackingLinkService(db)
        link = await service.get_by_id(tenant_id, link_id)
        return _build_tracking_link_response(link, service)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting tracking link")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.post("/tracking/links/{link_id}/deactivate", response_model=TrackingLinkResponse)
async def deactivate_tracking_link(
    link_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a tracking link."""
    try:
        service = TrackingLinkService(db)
        link = await service.deactivate(tenant_id, link_id)
        await db.commit()
        return _build_tracking_link_response(link, service)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error deactivating tracking link")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


def _build_tracking_link_response(link, service: TrackingLinkService) -> TrackingLinkResponse:
    """Build TrackingLinkResponse from model."""
    return TrackingLinkResponse(
        id=link.id,
        tenant_id=link.tenant_id,
        contact_id=link.contact_id,
        pipeline_id=link.pipeline_id,
        enrollment_id=link.enrollment_id,
        token=link.token,
        target_url=link.target_url,
        short_code=link.short_code,
        utm_source=link.utm_source,
        utm_medium=link.utm_medium,
        utm_campaign=link.utm_campaign,
        utm_content=link.utm_content,
        utm_term=link.utm_term,
        click_count=link.click_count,
        first_click_at=link.first_click_at,
        last_click_at=link.last_click_at,
        expires_at=link.expires_at,
        is_active=link.is_active,
        created_at=link.created_at,
        updated_at=link.updated_at,
        tracking_url=service.build_tracking_url(link),
        contact_name=link.contact.name if link.contact else None,
    )


# ============== Tracking Pixel & Events ==============


@router.post("/pixel")
async def receive_pixel_event(
    data: TrackingEventCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive tracking events from the website pixel.

    This endpoint is public (no auth) for pixel usage.
    """
    try:
        # Get client info
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Determine tenant from token if available
        tenant_id = "default"  # Fallback
        if data.ref:
            link_service = TrackingLinkService(db)
            link = await link_service.get_by_token(data.ref)
            if link:
                tenant_id = link.tenant_id

        service = TrackingEventService(db)
        await service.log_event(tenant_id, data, ip_address, user_agent)
        await db.commit()
        return {"status": "ok"}
    except Exception:
        logger.exception("Error logging pixel event")
        # Always return ok to not break the pixel
        return {"status": "ok"}


@router.get("/tracking/events", response_model=list[TrackingEventResponse])
async def list_tracking_events(
    contact_id: int | None = Query(None),
    tracking_link_id: int | None = Query(None),
    event_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """List tracking events with optional filters."""
    try:
        service = TrackingEventService(db)
        events = await service.list_events(tenant_id, contact_id, tracking_link_id, event_type, limit)
        return [
            TrackingEventResponse(
                id=e.id,
                tenant_id=e.tenant_id,
                tracking_link_id=e.tracking_link_id,
                contact_id=e.contact_id,
                event_type=e.event_type,
                url=e.url,
                referrer=e.referrer,
                utm_source=e.utm_source,
                utm_medium=e.utm_medium,
                utm_campaign=e.utm_campaign,
                utm_content=e.utm_content,
                device_type=e.device_type,
                event_time=e.event_time,
                created_at=e.created_at,
            )
            for e in events
        ]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error listing tracking events")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/tracking/events/summary")
async def get_event_summary(
    contact_id: int | None = Query(None),
    days: int = Query(30, ge=1, le=365),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get summary of tracking events."""
    try:
        service = TrackingEventService(db)
        return await service.get_event_summary(tenant_id, contact_id, days)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting event summary")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/tracking/pixel-code", response_model=PixelCodeResponse)
async def get_pixel_code(
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get the pixel code to embed on websites."""
    from app.config import settings

    base_url = getattr(settings, "api_base_url", None) or "https://api.go4energy.de"
    pixel_url = f"{base_url}/api/v1/engagement/pixel"

    pixel_code = f"""<!-- go4-automate Tracking Pixel -->
<script>
(function() {{
    var GO4_ENDPOINT = '{pixel_url}';
    var params = new URLSearchParams(window.location.search);
    var ref = params.get('ref');
    var utmSource = params.get('utm_source');
    var utmCampaign = params.get('utm_campaign');

    function trackEvent(eventType, data) {{
        var payload = {{
            event: eventType,
            ref: ref,
            utm_source: utmSource,
            utm_campaign: utmCampaign,
            url: window.location.href,
            referrer: document.referrer,
            timestamp: new Date().toISOString()
        }};
        if (data) Object.assign(payload, data);
        navigator.sendBeacon(GO4_ENDPOINT, JSON.stringify(payload));
    }}

    trackEvent('page_view');
    window.go4Track = function(event, data) {{ trackEvent(event, data); }};
}})();
</script>
<!-- End go4-automate Tracking Pixel -->"""

    return PixelCodeResponse(
        pixel_code=pixel_code,
        pixel_url=pixel_url,
        tenant_id=tenant_id,
    )


# ============== Attribution ==============


@router.post("/tracking/conversions")
async def record_conversion(
    contact_id: int,
    conversion_type: str,
    conversion_value: float | None = None,
    pipeline_id: int | None = None,
    enrollment_id: int | None = None,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Record a conversion for attribution tracking."""
    try:
        service = AttributionService(db)
        record = await service.record_conversion(
            tenant_id, contact_id, conversion_type, conversion_value, pipeline_id, enrollment_id
        )
        await db.commit()
        return {
            "id": record.id,
            "conversion_type": record.conversion_type,
            "first_touch_channel": record.first_touch_channel,
            "last_touch_channel": record.last_touch_channel,
            "touchpoint_count": record.touchpoint_count,
        }
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error recording conversion")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/tracking/attribution", response_model=AttributionDashboard)
async def get_attribution_dashboard(
    pipeline_id: int | None = Query(None),
    days: int = Query(30, ge=1, le=365),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get attribution dashboard with conversion data."""
    try:
        service = AttributionService(db)
        data = await service.get_attribution_dashboard(tenant_id, pipeline_id, days)
        return AttributionDashboard(
            total_conversions=data["total_conversions"],
            total_value=data["total_value"],
            conversion_by_channel=data["conversion_by_channel"],
            conversion_by_source=data["conversion_by_source"],
            avg_touchpoints=data["avg_touchpoints"],
            first_touch_attribution=data["first_touch_attribution"],
            last_touch_attribution=data["last_touch_attribution"],
            recent_conversions=[],  # Can be populated if needed
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error getting attribution dashboard")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None
