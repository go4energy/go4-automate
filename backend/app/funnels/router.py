"""Funnels API router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError, NotFoundError, ValidationError
from app.funnels.dedup import DeduplicationService
from app.funnels.handoff_service import HandoffService
from app.funnels.schemas import (
    BulkImportRequest,
    BulkImportResult,
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    FunnelActivityCreate,
    FunnelActivityResponse,
    FunnelCompanyCreate,
    FunnelCompanyListResponse,
    FunnelCompanyResponse,
    FunnelCompanyUpdate,
    FunnelCreate,
    FunnelHandoffResponse,
    FunnelListResponse,
    FunnelProspectCreate,
    FunnelProspectListResponse,
    FunnelProspectResponse,
    FunnelProspectUpdate,
    FunnelResponse,
    FunnelStageCreate,
    FunnelStageResponse,
    FunnelStageUpdate,
    FunnelUpdate,
    HandoffInitiateRequest,
    KanbanBoardResponse,
    KanbanStageResponse,
    ProspectMoveRequest,
)
from app.funnels.service import (
    ActivityService,
    CompanyService,
    FunnelService,
    ProspectService,
)
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/funnels", tags=["funnels"])


# ============== Funnel Endpoints ==============


@router.get("", response_model=list[FunnelListResponse])
async def list_funnels(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
) -> list[FunnelListResponse]:
    """List all funnels for the tenant."""
    try:
        service = FunnelService(db)
        funnels = await service.list_funnels(tenant_id, status=status_filter)

        result = []
        for f in funnels:
            stats = await service.get_stats(tenant_id, f.id)
            result.append(
                FunnelListResponse(
                    id=f.id,
                    name=f.name,
                    description=f.description,
                    status=f.status,
                    color=f.color,
                    tags=f.tags,
                    stage_count=len(f.stages),
                    prospect_count=stats["prospect_count"],
                    company_count=stats["company_count"],
                    created_at=f.created_at,
                )
            )
        return result
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_funnels")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("", response_model=FunnelResponse, status_code=status.HTTP_201_CREATED)
async def create_funnel(
    data: FunnelCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FunnelResponse:
    """Create a new funnel."""
    try:
        service = FunnelService(db)
        funnel = await service.create(tenant_id, data)
        stats = await service.get_stats(tenant_id, funnel.id)

        stages = [
            FunnelStageResponse(
                id=s.id,
                funnel_id=s.funnel_id,
                name=s.name,
                position=s.position,
                color=s.color,
                is_handoff=s.is_handoff,
                is_disqualified=s.is_disqualified,
                auto_actions=s.auto_actions,
                prospect_count=0,
            )
            for s in funnel.stages
        ]

        return FunnelResponse(
            **{
                **funnel.__dict__,
                "stages": stages,
                "prospect_count": stats["prospect_count"],
                "company_count": stats["company_count"],
            }
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_funnel")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/{funnel_id}", response_model=FunnelResponse)
async def get_funnel(
    funnel_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FunnelResponse:
    """Get a funnel by ID."""
    try:
        service = FunnelService(db)
        funnel = await service.get_by_id(tenant_id, funnel_id)
        stats = await service.get_stats(tenant_id, funnel_id)

        # Build stage responses with counts
        stage_counts = {s["id"]: s["count"] for s in stats["stages"]}
        stages = [
            FunnelStageResponse(
                id=s.id,
                funnel_id=s.funnel_id,
                name=s.name,
                position=s.position,
                color=s.color,
                is_handoff=s.is_handoff,
                is_disqualified=s.is_disqualified,
                auto_actions=s.auto_actions,
                prospect_count=stage_counts.get(s.id, 0),
            )
            for s in funnel.stages
        ]

        return FunnelResponse(
            **{
                **funnel.__dict__,
                "stages": stages,
                "prospect_count": stats["prospect_count"],
                "company_count": stats["company_count"],
            }
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_funnel")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/{funnel_id}", response_model=FunnelResponse)
async def update_funnel(
    funnel_id: int,
    data: FunnelUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FunnelResponse:
    """Update a funnel."""
    try:
        service = FunnelService(db)
        funnel = await service.update(tenant_id, funnel_id, data)
        stats = await service.get_stats(tenant_id, funnel_id)

        stages = [
            FunnelStageResponse(
                id=s.id,
                funnel_id=s.funnel_id,
                name=s.name,
                position=s.position,
                color=s.color,
                is_handoff=s.is_handoff,
                is_disqualified=s.is_disqualified,
                auto_actions=s.auto_actions,
                prospect_count=0,
            )
            for s in funnel.stages
        ]

        return FunnelResponse(
            **{
                **funnel.__dict__,
                "stages": stages,
                "prospect_count": stats["prospect_count"],
                "company_count": stats["company_count"],
            }
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_funnel")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/{funnel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_funnel(
    funnel_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a funnel."""
    try:
        service = FunnelService(db)
        await service.delete(tenant_id, funnel_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_funnel")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Stage Endpoints ==============


@router.post(
    "/{funnel_id}/stages",
    response_model=FunnelStageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_stage(
    funnel_id: int,
    data: FunnelStageCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FunnelStageResponse:
    """Add a stage to a funnel."""
    try:
        service = FunnelService(db)
        stage = await service.add_stage(tenant_id, funnel_id, data)
        return FunnelStageResponse(
            id=stage.id,
            funnel_id=stage.funnel_id,
            name=stage.name,
            position=stage.position,
            color=stage.color,
            is_handoff=stage.is_handoff,
            is_disqualified=stage.is_disqualified,
            auto_actions=stage.auto_actions,
            prospect_count=0,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in add_stage")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/stages/{stage_id}", response_model=FunnelStageResponse)
async def update_stage(
    stage_id: int,
    data: FunnelStageUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FunnelStageResponse:
    """Update a funnel stage."""
    try:
        service = FunnelService(db)
        stage = await service.update_stage(tenant_id, stage_id, data)
        return FunnelStageResponse(
            id=stage.id,
            funnel_id=stage.funnel_id,
            name=stage.name,
            position=stage.position,
            color=stage.color,
            is_handoff=stage.is_handoff,
            is_disqualified=stage.is_disqualified,
            auto_actions=stage.auto_actions,
            prospect_count=0,
        )
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
    """Delete a funnel stage."""
    try:
        service = FunnelService(db)
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


# ============== Company Endpoints ==============


@router.get("/{funnel_id}/companies", response_model=list[FunnelCompanyListResponse])
async def list_companies(
    funnel_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    verified: bool | None = Query(None),
    industry: str | None = Query(None),
) -> list[FunnelCompanyListResponse]:
    """List companies in a funnel."""
    try:
        service = CompanyService(db)
        companies = await service.list_companies(
            tenant_id, funnel_id, verified=verified, industry=industry
        )
        return [
            FunnelCompanyListResponse(
                id=c.id,
                funnel_id=c.funnel_id,
                name=c.name,
                domain=c.domain,
                industry=c.industry,
                size=c.size,
                verified=c.verified,
                tags=c.tags,
                prospect_count=len(c.prospects) if hasattr(c, "prospects") else 0,
                created_at=c.created_at,
            )
            for c in companies
        ]
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_companies")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/{funnel_id}/companies",
    response_model=FunnelCompanyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_company(
    funnel_id: int,
    data: FunnelCompanyCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FunnelCompanyResponse:
    """Create a company in a funnel."""
    try:
        service = CompanyService(db)
        company = await service.create(tenant_id, funnel_id, data)
        return FunnelCompanyResponse(
            **{**company.__dict__, "prospect_count": 0}
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_company")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/companies/{company_id}", response_model=FunnelCompanyResponse)
async def get_company(
    company_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FunnelCompanyResponse:
    """Get a company by ID."""
    try:
        service = CompanyService(db)
        company = await service.get_by_id(tenant_id, company_id)
        return FunnelCompanyResponse(
            **{**company.__dict__, "prospect_count": len(company.prospects)}
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_company")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/companies/{company_id}", response_model=FunnelCompanyResponse)
async def update_company(
    company_id: int,
    data: FunnelCompanyUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FunnelCompanyResponse:
    """Update a company."""
    try:
        service = CompanyService(db)
        company = await service.update(tenant_id, company_id, data)
        return FunnelCompanyResponse(
            **{**company.__dict__, "prospect_count": 0}
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_company")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/companies/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a company."""
    try:
        service = CompanyService(db)
        await service.delete(tenant_id, company_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_company")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Prospect Endpoints ==============


@router.get("/{funnel_id}/prospects", response_model=list[FunnelProspectListResponse])
async def list_prospects(
    funnel_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    stage_id: int | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    owner_id: int | None = Query(None),
    company_id: int | None = Query(None),
    is_duplicate: bool | None = Query(None),
) -> list[FunnelProspectListResponse]:
    """List prospects in a funnel."""
    try:
        service = ProspectService(db)
        prospects = await service.list_prospects(
            tenant_id,
            funnel_id,
            stage_id=stage_id,
            status=status_filter,
            owner_id=owner_id,
            company_id=company_id,
            is_duplicate=is_duplicate,
        )
        return [
            FunnelProspectListResponse(
                id=p.id,
                funnel_id=p.funnel_id,
                company_id=p.company_id,
                stage_id=p.stage_id,
                email=p.email,
                name=p.name,
                position=p.position,
                linkedin_url=p.linkedin_url,
                score=p.score,
                status=p.status,
                is_duplicate=p.is_duplicate,
                tags=p.tags,
                company_name=p.company.name if p.company else None,
                stage_name=p.stage.name if p.stage else None,
                created_at=p.created_at,
            )
            for p in prospects
        ]
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_prospects")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/{funnel_id}/kanban", response_model=KanbanBoardResponse)
async def get_kanban_board(
    funnel_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> KanbanBoardResponse:
    """Get Kanban board view for a funnel."""
    try:
        service = ProspectService(db)
        board = await service.get_kanban_board(tenant_id, funnel_id)

        # Build response
        stages = []
        for stage_data in board["stages"]:
            prospects = [
                FunnelProspectListResponse(
                    id=p.id,
                    funnel_id=p.funnel_id,
                    company_id=p.company_id,
                    stage_id=p.stage_id,
                    email=p.email,
                    name=p.name,
                    position=p.position,
                    linkedin_url=p.linkedin_url,
                    score=p.score,
                    status=p.status,
                    is_duplicate=p.is_duplicate,
                    tags=p.tags,
                    company_name=p.company.name if p.company else None,
                    stage_name=p.stage.name if p.stage else None,
                    created_at=p.created_at,
                )
                for p in stage_data["prospects"]
            ]
            stages.append(
                KanbanStageResponse(
                    id=stage_data["id"],
                    name=stage_data["name"],
                    position=stage_data["position"],
                    color=stage_data["color"],
                    is_handoff=stage_data["is_handoff"],
                    is_disqualified=stage_data["is_disqualified"],
                    prospects=prospects,
                    prospect_count=stage_data["prospect_count"],
                )
            )

        funnel = board["funnel"]
        return KanbanBoardResponse(
            funnel=FunnelListResponse(
                id=funnel.id,
                name=funnel.name,
                description=funnel.description,
                status=funnel.status,
                color=funnel.color,
                tags=funnel.tags,
                stage_count=len(funnel.stages),
                prospect_count=sum(s.prospect_count for s in stages),
                company_count=0,
                created_at=funnel.created_at,
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


@router.post(
    "/{funnel_id}/prospects",
    response_model=FunnelProspectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prospect(
    funnel_id: int,
    data: FunnelProspectCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FunnelProspectResponse:
    """Create a prospect in a funnel."""
    try:
        service = ProspectService(db)
        prospect = await service.create(tenant_id, funnel_id, data)
        prospect = await service.get_by_id(tenant_id, prospect.id)
        return FunnelProspectResponse(
            **{
                **prospect.__dict__,
                "company_name": prospect.company.name if prospect.company else None,
                "stage_name": prospect.stage.name if prospect.stage else None,
                "owner_name": prospect.owner.display_name if prospect.owner else None,
            }
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_prospect")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/prospects/{prospect_id}", response_model=FunnelProspectResponse)
async def get_prospect(
    prospect_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FunnelProspectResponse:
    """Get a prospect by ID."""
    try:
        service = ProspectService(db)
        prospect = await service.get_by_id(tenant_id, prospect_id)
        return FunnelProspectResponse(
            **{
                **prospect.__dict__,
                "company_name": prospect.company.name if prospect.company else None,
                "stage_name": prospect.stage.name if prospect.stage else None,
                "owner_name": prospect.owner.display_name if prospect.owner else None,
            }
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_prospect")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/prospects/{prospect_id}", response_model=FunnelProspectResponse)
async def update_prospect(
    prospect_id: int,
    data: FunnelProspectUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FunnelProspectResponse:
    """Update a prospect."""
    try:
        service = ProspectService(db)
        prospect = await service.update(tenant_id, prospect_id, data)
        prospect = await service.get_by_id(tenant_id, prospect_id)
        return FunnelProspectResponse(
            **{
                **prospect.__dict__,
                "company_name": prospect.company.name if prospect.company else None,
                "stage_name": prospect.stage.name if prospect.stage else None,
                "owner_name": prospect.owner.display_name if prospect.owner else None,
            }
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_prospect")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.patch("/prospects/{prospect_id}/move", response_model=FunnelProspectResponse)
async def move_prospect(
    prospect_id: int,
    data: ProspectMoveRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FunnelProspectResponse:
    """Move a prospect to a different stage."""
    try:
        service = ProspectService(db)
        prospect = await service.move_to_stage(tenant_id, prospect_id, data)
        prospect = await service.get_by_id(tenant_id, prospect_id)
        return FunnelProspectResponse(
            **{
                **prospect.__dict__,
                "company_name": prospect.company.name if prospect.company else None,
                "stage_name": prospect.stage.name if prospect.stage else None,
                "owner_name": prospect.owner.display_name if prospect.owner else None,
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
        logger.exception("Unerwarteter Fehler in move_prospect")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/prospects/{prospect_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prospect(
    prospect_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a prospect."""
    try:
        service = ProspectService(db)
        await service.delete(tenant_id, prospect_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_prospect")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Duplicate Check Endpoint ==============


@router.post("/prospects/check-duplicate", response_model=DuplicateCheckResponse)
async def check_duplicate(
    data: DuplicateCheckRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> DuplicateCheckResponse:
    """Check for duplicate prospects."""
    try:
        service = DeduplicationService(db)
        return await service.check_duplicates(
            tenant_id,
            email=data.email,
            linkedin_url=data.linkedin_url,
            phone=data.phone,
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in check_duplicate")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Bulk Import Endpoint ==============


@router.post("/{funnel_id}/prospects/import", response_model=BulkImportResult)
async def bulk_import_prospects(
    funnel_id: int,
    data: BulkImportRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> BulkImportResult:
    """Bulk import prospects into a funnel."""
    try:
        prospect_service = ProspectService(db)
        company_service = CompanyService(db)

        imported = 0
        skipped = 0
        duplicates = 0
        errors = []
        prospect_ids = []

        for item in data.items:
            try:
                # Handle company if provided
                company_id = None
                if item.company_name or item.company_domain:
                    company = await company_service.find_or_create_by_domain(
                        tenant_id,
                        funnel_id,
                        item.company_name or item.company_domain,
                        item.company_domain,
                    )
                    if company:
                        company_id = company.id

                # Check duplicates if configured
                if data.skip_duplicates and item.email:
                    dedup = DeduplicationService(db)
                    check = await dedup.check_duplicates(
                        tenant_id, email=item.email, linkedin_url=item.linkedin_url
                    )
                    if check.has_duplicates:
                        duplicates += 1
                        skipped += 1
                        continue

                # Create prospect
                prospect = await prospect_service.create(
                    tenant_id,
                    funnel_id,
                    FunnelProspectCreate(
                        name=item.name,
                        email=item.email,
                        phone=item.phone,
                        position=item.position,
                        linkedin_url=item.linkedin_url,
                        company_id=company_id,
                        stage_id=data.stage_id,
                        owner_id=data.owner_id,
                        source=item.source,
                        tags=item.tags,
                        custom_fields=item.custom_fields,
                    ),
                    check_duplicates=False,  # Already checked above
                )
                prospect_ids.append(prospect.id)
                imported += 1

            except Exception as e:
                errors.append(f"{item.name}: {e!s}")
                skipped += 1

        return BulkImportResult(
            total=len(data.items),
            imported=imported,
            skipped=skipped,
            duplicates=duplicates,
            errors=errors,
            prospect_ids=prospect_ids,
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in bulk_import_prospects")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Activity Endpoints ==============


@router.post(
    "/prospects/{prospect_id}/activities",
    response_model=FunnelActivityResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_activity(
    prospect_id: int,
    data: FunnelActivityCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FunnelActivityResponse:
    """Log an activity for a prospect."""
    try:
        service = ActivityService(db)
        activity = await service.create(tenant_id, prospect_id, data)
        return FunnelActivityResponse(
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


@router.get(
    "/prospects/{prospect_id}/activities",
    response_model=list[FunnelActivityResponse],
)
async def list_activities(
    prospect_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[FunnelActivityResponse]:
    """Get activity timeline for a prospect."""
    try:
        service = ActivityService(db)
        activities = await service.list_for_prospect(tenant_id, prospect_id)
        return [
            FunnelActivityResponse(
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
        logger.exception("Unerwarteter Fehler in list_activities")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Handoff Endpoints ==============


@router.post(
    "/prospects/{prospect_id}/handoff",
    response_model=FunnelHandoffResponse,
    status_code=status.HTTP_201_CREATED,
)
async def initiate_handoff(
    prospect_id: int,
    data: HandoffInitiateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FunnelHandoffResponse:
    """Initiate handoff for a prospect to CRM."""
    try:
        service = HandoffService(db)
        handoff = await service.initiate_handoff(tenant_id, prospect_id, data)
        return FunnelHandoffResponse(
            **{
                **handoff.__dict__,
                "prospect_name": handoff.prospect.name if handoff.prospect else None,
                "company_name": handoff.company.name if handoff.company else None,
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
        logger.exception("Unerwarteter Fehler in initiate_handoff")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/handoffs", response_model=list[FunnelHandoffResponse])
async def list_handoffs(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    funnel_id: int | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
) -> list[FunnelHandoffResponse]:
    """List handoffs."""
    try:
        service = HandoffService(db)
        handoffs = await service.list_handoffs(
            tenant_id, funnel_id=funnel_id, status=status_filter
        )
        return [
            FunnelHandoffResponse(
                **{
                    **h.__dict__,
                    "prospect_name": h.prospect.name if h.prospect else None,
                    "company_name": h.company.name if h.company else None,
                }
            )
            for h in handoffs
        ]
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_handoffs")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/handoffs/{handoff_id}/retry", response_model=FunnelHandoffResponse)
async def retry_handoff(
    handoff_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FunnelHandoffResponse:
    """Retry a failed handoff."""
    try:
        service = HandoffService(db)
        handoff = await service.retry_handoff(tenant_id, handoff_id)
        return FunnelHandoffResponse(
            **{
                **handoff.__dict__,
                "prospect_name": handoff.prospect.name if handoff.prospect else None,
                "company_name": handoff.company.name if handoff.company else None,
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
        logger.exception("Unerwarteter Fehler in retry_handoff")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
