"""CRM API router."""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.crm.config_schema import crm_interface
from app.crm.schemas import (
    ActivityCreate,
    ActivityResponse,
    CallActionResponse,
    CallLogRequest,
    CallStatsResponse,
    CrmContactCreate,
    CrmContactResponse,
    CrmContactStatusUpdate,
    CrmFollowupPause,
    DealCreate,
    DealListResponse,
    DealMoveRequest,
    DealResponse,
    DealUpdate,
    KanbanBoardResponse,
    KanbanStageResponse,
    PipelineCreate,
    PipelineListResponse,
    PipelineResponse,
    PipelineStageCreate,
    PipelineStageResponse,
    PipelineStageUpdate,
    PipelineUpdate,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from app.crm.service import (
    ActivityService,
    CallQueueService,
    CrmService,
    DealService,
    PipelineService,
    TaskService,
)
from app.database import get_db
from app.exceptions import AppError, DuplicateError, NotFoundError, ValidationError
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/crm", tags=["crm"])

# Register standardized /config, /config/schema, /status, /metrics endpoints
crm_interface.register_endpoints(router)


# ============== Legacy Contact Endpoints ==============


@router.post(
    "/", response_model=CrmContactResponse, status_code=status.HTTP_201_CREATED
)
async def create_contact(
    data: CrmContactCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CrmContactResponse:
    """Create a new contact."""
    try:
        service = CrmService(db)
        return await service.create(tenant_id, data)
    except DuplicateError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_contact")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/", response_model=list[CrmContactResponse])
async def list_contacts(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
    source: str | None = Query(None),
) -> list[CrmContactResponse]:
    """List contacts for the current tenant."""
    try:
        service = CrmService(db)
        return await service.list_contacts(
            tenant_id, status=status_filter, source=source
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_contacts")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.patch("/{contact_id}/status", response_model=CrmContactResponse)
async def update_contact_status(
    contact_id: int,
    data: CrmContactStatusUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CrmContactResponse:
    """Update a contact's status."""
    try:
        service = CrmService(db)
        return await service.update_status(tenant_id, contact_id, data.status)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_contact_status")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.patch("/{contact_id}/pause-followup", response_model=CrmContactResponse)
async def pause_followup(
    contact_id: int,
    data: CrmFollowupPause,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CrmContactResponse:
    """Pause or resume follow-up for a contact."""
    try:
        service = CrmService(db)
        return await service.toggle_followup_pause(tenant_id, contact_id, data.paused)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in pause_followup")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Pipeline Endpoints ==============


@router.get("/pipelines", response_model=list[PipelineListResponse])
async def list_pipelines(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[PipelineListResponse]:
    """List all pipelines for the tenant."""
    try:
        service = PipelineService(db)
        # Ensure default pipeline exists
        await service.ensure_default_pipeline(tenant_id)
        pipelines = await service.list_pipelines(tenant_id)

        result = []
        for p in pipelines:
            deal_count = await service.get_deal_count(p.id)
            result.append(
                PipelineListResponse(
                    id=p.id,
                    name=p.name,
                    is_default=p.is_default,
                    color=p.color,
                    stage_count=len(p.stages),
                    deal_count=deal_count,
                )
            )
        return result
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_pipelines")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/pipelines", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED
)
async def create_pipeline(
    data: PipelineCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PipelineResponse:
    """Create a new pipeline."""
    try:
        service = PipelineService(db)
        pipeline = await service.create(tenant_id, data)
        deal_count = await service.get_deal_count(pipeline.id)
        return PipelineResponse(
            **{**pipeline.__dict__, "deal_count": deal_count}
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_pipeline")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/pipelines/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(
    pipeline_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PipelineResponse:
    """Get a pipeline by ID."""
    try:
        service = PipelineService(db)
        pipeline = await service.get_by_id(tenant_id, pipeline_id)
        deal_count = await service.get_deal_count(pipeline_id)
        return PipelineResponse(
            **{**pipeline.__dict__, "deal_count": deal_count}
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_pipeline")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/pipelines/{pipeline_id}", response_model=PipelineResponse)
async def update_pipeline(
    pipeline_id: int,
    data: PipelineUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PipelineResponse:
    """Update a pipeline."""
    try:
        service = PipelineService(db)
        pipeline = await service.update(tenant_id, pipeline_id, data)
        deal_count = await service.get_deal_count(pipeline_id)
        return PipelineResponse(
            **{**pipeline.__dict__, "deal_count": deal_count}
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_pipeline")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/pipelines/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline(
    pipeline_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a pipeline."""
    try:
        service = PipelineService(db)
        await service.delete(tenant_id, pipeline_id)
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_pipeline")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# Stage endpoints
@router.post(
    "/pipelines/{pipeline_id}/stages",
    response_model=PipelineStageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_stage(
    pipeline_id: int,
    data: PipelineStageCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PipelineStageResponse:
    """Add a stage to a pipeline."""
    try:
        service = PipelineService(db)
        stage = await service.add_stage(tenant_id, pipeline_id, data)
        return PipelineStageResponse.model_validate(stage)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in add_stage")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/stages/{stage_id}", response_model=PipelineStageResponse)
async def update_stage(
    stage_id: int,
    data: PipelineStageUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PipelineStageResponse:
    """Update a pipeline stage."""
    try:
        service = PipelineService(db)
        stage = await service.update_stage(tenant_id, stage_id, data)
        return PipelineStageResponse.model_validate(stage)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_stage")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/stages/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stage(
    stage_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a pipeline stage."""
    try:
        service = PipelineService(db)
        await service.delete_stage(tenant_id, stage_id)
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_stage")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Deal Endpoints ==============


@router.get("/deals", response_model=list[DealListResponse])
async def list_deals(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    pipeline_id: int | None = Query(None),
    stage_id: int | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
) -> list[DealListResponse]:
    """List deals with optional filters."""
    try:
        service = DealService(db)
        deals = await service.list_deals(
            tenant_id,
            pipeline_id=pipeline_id,
            stage_id=stage_id,
            status=status_filter,
        )

        result = []
        for deal in deals:
            result.append(
                DealListResponse(
                    id=deal.id,
                    title=deal.title,
                    pipeline_id=deal.pipeline_id,
                    stage_id=deal.stage_id,
                    value=deal.value,
                    currency=deal.currency,
                    probability=deal.probability,
                    expected_close=deal.expected_close,
                    status=deal.status,
                    priority=deal.priority,
                    tags=deal.tags,
                    contact_name=deal.contact.name if deal.contact else None,
                    company_name=deal.company.name if deal.company else None,
                    stage_name=deal.stage.name if deal.stage else None,
                    created_at=deal.created_at,
                )
            )
        return result
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_deals")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/deals/kanban/{pipeline_id}", response_model=KanbanBoardResponse)
async def get_kanban_board(
    pipeline_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> KanbanBoardResponse:
    """Get Kanban board view for a pipeline."""
    try:
        service = DealService(db)
        board = await service.get_kanban_board(tenant_id, pipeline_id)

        # Build response
        stages = []
        for stage_data in board["stages"]:
            deals = [
                DealListResponse(
                    id=d.id,
                    title=d.title,
                    pipeline_id=d.pipeline_id,
                    stage_id=d.stage_id,
                    value=d.value,
                    currency=d.currency,
                    probability=d.probability,
                    expected_close=d.expected_close,
                    status=d.status,
                    priority=d.priority,
                    tags=d.tags,
                    contact_name=d.contact.name if d.contact else None,
                    company_name=d.company.name if d.company else None,
                    stage_name=d.stage.name if d.stage else None,
                    created_at=d.created_at,
                )
                for d in stage_data["deals"]
            ]
            stages.append(
                KanbanStageResponse(
                    id=stage_data["id"],
                    name=stage_data["name"],
                    position=stage_data["position"],
                    probability=stage_data["probability"],
                    color=stage_data["color"],
                    is_won=stage_data["is_won"],
                    is_lost=stage_data["is_lost"],
                    deals=deals,
                    total_value=stage_data["total_value"],
                    deal_count=stage_data["deal_count"],
                )
            )

        pipeline = board["pipeline"]
        return KanbanBoardResponse(
            pipeline=PipelineListResponse(
                id=pipeline.id,
                name=pipeline.name,
                is_default=pipeline.is_default,
                color=pipeline.color,
                stage_count=len(pipeline.stages),
                deal_count=sum(s.deal_count for s in stages),
            ),
            stages=stages,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_kanban_board")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/deals", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
async def create_deal(
    data: DealCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> DealResponse:
    """Create a new deal."""
    try:
        service = DealService(db)
        deal = await service.create(tenant_id, data)
        deal = await service.get_by_id(tenant_id, deal.id)
        return DealResponse(
            **{
                **deal.__dict__,
                "contact_name": deal.contact.name if deal.contact else None,
                "company_name": deal.company.name if deal.company else None,
                "stage_name": deal.stage.name if deal.stage else None,
                "owner_name": deal.owner.display_name if deal.owner else None,
            }
        )
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_deal")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/deals/{deal_id}", response_model=DealResponse)
async def get_deal(
    deal_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> DealResponse:
    """Get a deal by ID."""
    try:
        service = DealService(db)
        deal = await service.get_by_id(tenant_id, deal_id)
        return DealResponse(
            **{
                **deal.__dict__,
                "contact_name": deal.contact.name if deal.contact else None,
                "company_name": deal.company.name if deal.company else None,
                "stage_name": deal.stage.name if deal.stage else None,
                "owner_name": deal.owner.display_name if deal.owner else None,
            }
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_deal")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/deals/{deal_id}", response_model=DealResponse)
async def update_deal(
    deal_id: int,
    data: DealUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> DealResponse:
    """Update a deal."""
    try:
        service = DealService(db)
        deal = await service.update(tenant_id, deal_id, data)
        deal = await service.get_by_id(tenant_id, deal_id)
        return DealResponse(
            **{
                **deal.__dict__,
                "contact_name": deal.contact.name if deal.contact else None,
                "company_name": deal.company.name if deal.company else None,
                "stage_name": deal.stage.name if deal.stage else None,
                "owner_name": deal.owner.display_name if deal.owner else None,
            }
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_deal")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.patch("/deals/{deal_id}/move", response_model=DealResponse)
async def move_deal(
    deal_id: int,
    data: DealMoveRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> DealResponse:
    """Move a deal to a different stage."""
    try:
        service = DealService(db)
        deal = await service.move(tenant_id, deal_id, data)
        deal = await service.get_by_id(tenant_id, deal_id)
        return DealResponse(
            **{
                **deal.__dict__,
                "contact_name": deal.contact.name if deal.contact else None,
                "company_name": deal.company.name if deal.company else None,
                "stage_name": deal.stage.name if deal.stage else None,
                "owner_name": deal.owner.display_name if deal.owner else None,
            }
        )
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in move_deal")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/deals/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deal(
    deal_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a deal."""
    try:
        service = DealService(db)
        await service.delete(tenant_id, deal_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_deal")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Activity Endpoints ==============


@router.post(
    "/activities", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED
)
async def create_activity(
    data: ActivityCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ActivityResponse:
    """Create a new activity."""
    try:
        service = ActivityService(db)
        activity = await service.create(tenant_id, None, data)  # TODO: get user_id
        return ActivityResponse(
            **{
                **activity.__dict__,
                "metadata": activity.metadata_,
                "user_name": None,
            }
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_activity")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/activities/contact/{contact_id}", response_model=list[ActivityResponse])
async def list_contact_activities(
    contact_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[ActivityResponse]:
    """List activities for a contact."""
    try:
        service = ActivityService(db)
        activities = await service.list_for_contact(tenant_id, contact_id)
        return [
            ActivityResponse(
                **{
                    **a.__dict__,
                    "metadata": a.metadata_,
                    "user_name": a.user.display_name if a.user else None,
                }
            )
            for a in activities
        ]
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_contact_activities")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/activities/deal/{deal_id}", response_model=list[ActivityResponse])
async def list_deal_activities(
    deal_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[ActivityResponse]:
    """List activities for a deal."""
    try:
        service = ActivityService(db)
        activities = await service.list_for_deal(tenant_id, deal_id)
        return [
            ActivityResponse(
                **{
                    **a.__dict__,
                    "metadata": a.metadata_,
                    "user_name": a.user.display_name if a.user else None,
                }
            )
            for a in activities
        ]
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_deal_activities")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Task Endpoints ==============


@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    assigned_to: int | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
) -> list[TaskResponse]:
    """List tasks with optional filters."""
    try:
        service = TaskService(db)
        tasks = await service.list_tasks(
            tenant_id, assigned_to=assigned_to, status=status_filter
        )
        return [
            TaskResponse(
                **{
                    **t.__dict__,
                    "assignee_name": t.assignee.display_name if t.assignee else None,
                    "creator_name": t.creator.display_name if t.creator else None,
                }
            )
            for t in tasks
        ]
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_tasks")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Create a new task."""
    try:
        service = TaskService(db)
        task = await service.create(tenant_id, None, data)  # TODO: get user_id
        task = await service.get_by_id(tenant_id, task.id)
        return TaskResponse(
            **{
                **task.__dict__,
                "assignee_name": task.assignee.display_name if task.assignee else None,
                "creator_name": task.creator.display_name if task.creator else None,
            }
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_task")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Get a task by ID."""
    try:
        service = TaskService(db)
        task = await service.get_by_id(tenant_id, task_id)
        return TaskResponse(
            **{
                **task.__dict__,
                "assignee_name": task.assignee.display_name if task.assignee else None,
                "creator_name": task.creator.display_name if task.creator else None,
            }
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_task")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Update a task."""
    try:
        service = TaskService(db)
        task = await service.update(tenant_id, task_id, data)
        return TaskResponse(
            **{
                **task.__dict__,
                "assignee_name": task.assignee.display_name if task.assignee else None,
                "creator_name": task.creator.display_name if task.creator else None,
            }
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_task")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a task."""
    try:
        service = TaskService(db)
        await service.delete(tenant_id, task_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_task")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Call Queue Endpoints ==============


@router.get("/calls", response_model=list[CallActionResponse])
async def list_calls(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
) -> list[CallActionResponse]:
    """List pending phone actions from the engagement queue."""
    try:
        service = CallQueueService(db)
        return await service.list_calls(tenant_id, status=status_filter, limit=limit)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_calls")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/calls/stats", response_model=CallStatsResponse)
async def get_call_stats(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CallStatsResponse:
    """Get call queue statistics."""
    try:
        service = CallQueueService(db)
        stats = await service.get_stats(tenant_id)
        return CallStatsResponse(**stats)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_call_stats")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/calls/{action_id}/generate-script")
async def generate_call_script(
    action_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate a call script for a phone action via LLM."""
    try:
        service = CallQueueService(db)
        script = await service.generate_call_script(tenant_id, action_id)
        return {"action_id": action_id, "script": script}
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in generate_call_script")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/calls/{action_id}/log")
async def log_call(
    action_id: int,
    data: CallLogRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Log a call result and complete the engagement action."""
    try:
        service = CallQueueService(db)
        return await service.log_call(tenant_id, action_id, data)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in log_call")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
