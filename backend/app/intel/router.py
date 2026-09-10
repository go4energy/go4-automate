"""Intel module API router — /intel/*."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError, NotFoundError
from app.intel.schemas import (
    BriefingResponse,
    ChangeEventResponse,
    SourceCreate,
    SourceResponse,
    SourceUpdate,
    WatchTargetCreate,
    WatchTargetResponse,
    WatchTargetUpdate,
)
from app.intel.services.embedding_client import get_embedding_client
from app.intel.services.intel_service import (
    BriefingService,
    EventService,
    SourceService,
    WatchTargetService,
)
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/intel", tags=["intel"])


# ============== Watch-Targets ==============


@router.get("/targets", response_model=list[WatchTargetResponse])
async def list_targets(
    include_inactive: bool = Query(default=False),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await WatchTargetService(db).list(
            tenant_id, include_inactive=include_inactive
        )
    except Exception:
        logger.exception("Error listing intel targets")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.post(
    "/targets",
    response_model=WatchTargetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_target(
    data: WatchTargetCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        target = await WatchTargetService(db).create(tenant_id, data)
        await db.commit()
        return target
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception:
        logger.exception("Error creating intel target")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from None


@router.get("/targets/{target_id}", response_model=WatchTargetResponse)
async def get_target(
    target_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await WatchTargetService(db).get(tenant_id, target_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.put("/targets/{target_id}", response_model=WatchTargetResponse)
async def update_target(
    target_id: int,
    data: WatchTargetUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        target = await WatchTargetService(db).update(tenant_id, target_id, data)
        await db.commit()
        return target
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete("/targets/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target(
    target_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        await WatchTargetService(db).delete(tenant_id, target_id)
        await db.commit()
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ============== Sources ==============


@router.get("/targets/{target_id}/sources", response_model=list[SourceResponse])
async def list_sources(
    target_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    return await SourceService(db).list_for_target(tenant_id, target_id)


@router.post(
    "/targets/{target_id}/sources",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_source(
    target_id: int,
    data: SourceCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        source = await SourceService(db).create(tenant_id, target_id, data)
        await db.commit()
        return source
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.put("/sources/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: int,
    data: SourceUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        source = await SourceService(db).update(tenant_id, source_id, data)
        await db.commit()
        return source
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        await SourceService(db).delete(tenant_id, source_id)
        await db.commit()
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ============== Briefings ==============


@router.get("/briefings", response_model=list[BriefingResponse])
async def list_briefings(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    return await BriefingService(db).list(tenant_id, limit=limit, offset=offset)


@router.get("/briefings/{briefing_id}", response_model=BriefingResponse)
async def get_briefing(
    briefing_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await BriefingService(db).get(tenant_id, briefing_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ============== Events ==============


@router.get("/events", response_model=list[ChangeEventResponse])
async def list_events(
    min_significance: float | None = Query(default=None, ge=0.0, le=1.0),
    change_type: str | None = Query(default=None, max_length=50),
    target_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    return await EventService(db).list(
        tenant_id,
        min_significance=min_significance,
        change_type=change_type,
        target_id=target_id,
        limit=limit,
        offset=offset,
    )


# ============== Admin / Operations ==============


@router.get("/admin/embed-health")
async def embed_health(
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Probe the embedding service (Ollama). Useful to debug outages."""
    client = get_embedding_client()
    healthy = await client.health()
    return {
        "backend": "ollama",
        "url": client._ollama_url,
        "model": client._ollama_model,
        "healthy": healthy,
    }


# Backwards-compat alias for the old endpoint name
@router.get("/admin/tei-health", include_in_schema=False)
async def tei_health_compat(
    tenant_id: str = Depends(get_current_tenant_id),
):
    return await embed_health(tenant_id)


@router.post("/admin/run-now", status_code=status.HTTP_202_ACCEPTED)
async def run_now(
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Manually trigger one pipeline tick. Returns immediately."""
    from app.intel.tasks import run_pipeline_tick

    background_tasks.add_task(run_pipeline_tick)
    return {"ok": True, "queued": True}
