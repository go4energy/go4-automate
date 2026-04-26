"""Leadgen module API router."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.database import get_db
from app.exceptions import AppError
from app.leadgen.intake import (
    IntakeRequest,
    IntakeSuggestion,
    LeadgenIntakeService,
)
from app.leadgen.schemas import (
    CampaignCreate,
    CampaignResponse,
    CampaignStats,
    CampaignUpdate,
    EnrichRunRequest,
    ExportFilter,
    ExportPreview,
    HandoffPreview,
    HandoffRequest,
    HandoffResponse,
    PlaceListResponse,
    PlaceRejectRequest,
    PlaceResponse,
    RunResponse,
    RunResumeRequest,
)
from app.leadgen.service import (
    CampaignService,
    HandoffService,
    LeadgenExportService,
    PlaceService,
    RunService,
)
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/leadgen", tags=["leadgen"])


# ---------------- Health ----------------


@router.get("/health")
async def health() -> dict:
    """Module health probe."""
    return {"module": "leadgen", "healthy": True}


# ---------------- LLM Intake ----------------


@router.post("/intake", response_model=IntakeSuggestion)
async def intake(
    data: IntakeRequest,
    _tenant_id: str = Depends(get_current_tenant_id),
    _user: User = Depends(get_current_user),
) -> IntakeSuggestion:
    """Turn a free-text goal into structured Leadgen parameters via Claude Haiku.

    The caller shows the suggestion to the user for review before it is used
    in a campaign's source_config.
    """
    svc = LeadgenIntakeService()
    try:
        return await svc.suggest(data.text)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ---------------- Campaigns ----------------


@router.get("/campaigns", response_model=list[CampaignResponse])
async def list_campaigns(
    status_filter: str | None = Query(default=None, alias="status"),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[CampaignResponse]:
    """List all leadgen campaigns for the tenant."""
    svc = CampaignService(db)
    campaigns = await svc.list_campaigns(tenant_id, status=status_filter)
    return [CampaignResponse.model_validate(c) for c in campaigns]


@router.post(
    "/campaigns",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign(
    data: CampaignCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> CampaignResponse:
    """Create a new leadgen campaign. Optionally auto-creates the engagement pipeline."""
    svc = CampaignService(db)
    try:
        campaign = await svc.create(tenant_id, data)
        await db.commit()
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    return CampaignResponse.model_validate(campaign)


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> CampaignResponse:
    """Get a single campaign."""
    svc = CampaignService(db)
    try:
        campaign = await svc.get_by_id(tenant_id, campaign_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    return CampaignResponse.model_validate(campaign)


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    data: CampaignUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> CampaignResponse:
    """Update campaign."""
    svc = CampaignService(db)
    try:
        campaign = await svc.update(tenant_id, campaign_id, data)
        await db.commit()
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    return CampaignResponse.model_validate(campaign)


@router.delete(
    "/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_campaign(
    campaign_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> None:
    """Delete campaign (cascades to runs and places)."""
    svc = CampaignService(db)
    try:
        await svc.delete(tenant_id, campaign_id)
        await db.commit()
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/campaigns/{campaign_id}/stats", response_model=CampaignStats)
async def get_campaign_stats(
    campaign_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> CampaignStats:
    """Aggregated place status counts, cost, and run count for the campaign."""
    svc = CampaignService(db)
    try:
        return await svc.get_stats(tenant_id, campaign_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ---------------- Runs ----------------


@router.post(
    "/campaigns/{campaign_id}/runs",
    response_model=RunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_run(
    campaign_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> RunResponse:
    """Queue a new pipeline run for a campaign. Worker picks it up."""
    svc = RunService(db)
    try:
        run = await svc.start(tenant_id, campaign_id)
        await db.commit()
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    return RunResponse.model_validate(run)


@router.post(
    "/campaigns/{campaign_id}/runs/enrich",
    response_model=RunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_enrich_run(
    campaign_id: int,
    data: EnrichRunRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> RunResponse:
    """Queue an LLM-only enrichment run on already-discovered places.

    Skips Stage 1 (Google Places) and Stage 2 (Impressum-Scraping) entirely.
    Pulls ``limit`` places from the eligible pool (status discovered/
    impressum_*, website not null, no llm_insights yet) using either
    ``top_rated`` or ``random`` sampling.
    """
    svc = RunService(db)
    try:
        run = await svc.start_enrich(
            tenant_id,
            campaign_id,
            limit=data.limit,
            sampling=data.sampling,
        )
        await db.commit()
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    return RunResponse.model_validate(run)


@router.get(
    "/campaigns/{campaign_id}/runs", response_model=list[RunResponse]
)
async def list_runs_for_campaign(
    campaign_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[RunResponse]:
    """List all runs for a campaign (newest first)."""
    svc = RunService(db)
    runs = await svc.list_for_campaign(tenant_id, campaign_id)
    return [RunResponse.model_validate(r) for r in runs]


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> RunResponse:
    """Get a single run."""
    svc = RunService(db)
    try:
        run = await svc.get_by_id(tenant_id, run_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    return RunResponse.model_validate(run)


@router.post("/runs/{run_id}/pause", response_model=RunResponse)
async def pause_run(
    run_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> RunResponse:
    """Pause a queued or running run."""
    svc = RunService(db)
    try:
        run = await svc.pause(tenant_id, run_id)
        await db.commit()
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    return RunResponse.model_validate(run)


@router.post("/runs/{run_id}/advance-stage", response_model=RunResponse)
async def advance_run_stage(
    run_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> RunResponse:
    """Advance a paused run from *_pending to the actual stage and queue it.

    Used to kick off Stage 2 (impressum_pending -> impressum) and Stage 3
    (llm_pending -> llm) once the previous stage reported completion.
    """
    svc = RunService(db)
    try:
        run = await svc.advance_stage(tenant_id, run_id)
        await db.commit()
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    return RunResponse.model_validate(run)


@router.post("/runs/{run_id}/resume", response_model=RunResponse)
async def resume_run(
    run_id: int,
    body: RunResumeRequest | None = None,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> RunResponse:
    """Resume a paused run, optionally raising the campaign's max_api_calls budget."""
    svc = RunService(db)
    additional = body.additional_budget if body else None
    try:
        run = await svc.resume(
            tenant_id, run_id, additional_budget=additional
        )
        await db.commit()
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    return RunResponse.model_validate(run)


# ---------------- Places ----------------


@router.get(
    "/campaigns/{campaign_id}/places", response_model=PlaceListResponse
)
async def list_places_for_campaign(
    campaign_id: int,
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
    order_by: str = Query(
        default="created_at",
        pattern=r"^(name|city|status|rating|match|created_at)$",
    ),
    order_dir: str = Query(default="desc", pattern=r"^(asc|desc)$"),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> PlaceListResponse:
    """List places for a campaign with pagination, status filter, and sort."""
    svc = PlaceService(db)
    items, total = await svc.list_for_campaign(
        tenant_id,
        campaign_id,
        status=status_filter,
        page=page,
        size=size,
        order_by=order_by,
        order_dir=order_dir,
    )
    return PlaceListResponse(
        items=[PlaceResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/places/{place_id}", response_model=PlaceResponse)
async def get_place(
    place_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> PlaceResponse:
    """Get a single place (with impressum + insights eager-loaded)."""
    svc = PlaceService(db)
    try:
        place = await svc.get_by_id(tenant_id, place_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    return PlaceResponse.model_validate(place)


@router.post("/places/{place_id}/reject", response_model=PlaceResponse)
async def reject_place(
    place_id: int,
    data: PlaceRejectRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> PlaceResponse:
    """Mark a place as rejected (keeps data for audit but excludes from handoff)."""
    svc = PlaceService(db)
    try:
        place = await svc.reject(tenant_id, place_id, data.reason)
        await db.commit()
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    return PlaceResponse.model_validate(place)


# ---------------- Handoff to Engagement ----------------


@router.post(
    "/campaigns/{campaign_id}/handoff/preview",
    response_model=HandoffPreview,
)
async def handoff_preview(
    campaign_id: int,
    data: HandoffRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> HandoffPreview:
    """Dry-run: how many places match the filter and would be enrolled."""
    svc = HandoffService(db)
    try:
        preview = await svc.preview(
            tenant_id, campaign_id, min_score=data.min_score, limit=data.limit
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    return HandoffPreview(**preview)


@router.post(
    "/campaigns/{campaign_id}/handoff",
    response_model=HandoffResponse,
)
async def handoff_to_engagement(
    campaign_id: int,
    data: HandoffRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> HandoffResponse:
    """Convert qualifying places to contacts and bulk-enroll them in the
    campaign's linked engagement pipeline."""
    svc = HandoffService(db)
    try:
        result = await svc.handoff(
            tenant_id,
            campaign_id,
            min_score=data.min_score,
            limit=data.limit,
            pipeline_id=data.pipeline_id,
        )
        await db.commit()
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    return HandoffResponse(**result)


# ---------------- LinkedIn Sales Nav export ----------------


@router.post(
    "/campaigns/{campaign_id}/export/preview",
    response_model=ExportPreview,
)
async def export_preview(
    campaign_id: int,
    flt: ExportFilter,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ExportPreview:
    """Pre-flight: how many rows the two CSV exports would contain."""
    svc = LeadgenExportService(db)
    data = await svc.preview(tenant_id, campaign_id, flt=flt)
    return ExportPreview(**data)


def _csv_response(content: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/campaigns/{campaign_id}/export/sales-nav-accounts.csv",
    response_class=Response,
)
async def export_accounts_csv(
    campaign_id: int,
    min_score: int = Query(default=7, ge=0, le=10),
    limit: int = Query(default=10_000, ge=1, le=50_000),
    only_enrolled: bool = Query(default=False),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Response:
    flt = ExportFilter(
        min_score=min_score, limit=limit, only_enrolled=only_enrolled
    )
    svc = LeadgenExportService(db)
    csv_text = await svc.build_accounts_csv(tenant_id, campaign_id, flt=flt)
    return _csv_response(csv_text, f"sales_nav_accounts_camp_{campaign_id}.csv")


@router.get(
    "/campaigns/{campaign_id}/export/sales-nav-leads.csv",
    response_class=Response,
)
async def export_leads_csv(
    campaign_id: int,
    min_score: int = Query(default=7, ge=0, le=10),
    limit: int = Query(default=10_000, ge=1, le=50_000),
    only_enrolled: bool = Query(default=False),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Response:
    flt = ExportFilter(
        min_score=min_score, limit=limit, only_enrolled=only_enrolled
    )
    svc = LeadgenExportService(db)
    csv_text = await svc.build_leads_csv(tenant_id, campaign_id, flt=flt)
    return _csv_response(csv_text, f"sales_nav_leads_camp_{campaign_id}.csv")
