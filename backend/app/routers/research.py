"""Research API router."""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError
from app.schemas.content import ContentPieceResponse
from app.schemas.research import (
    ResearchFindingListItem,
    ResearchFindingResponse,
    ResearchFindingStatusUpdate,
    ResearchRunRequest,
    ResearchRunResponse,
    ResearchSourceCreate,
    ResearchSourceResponse,
    ResearchSourceUpdate,
    TopicGenerateRequest,
    TopicSuggestionCreate,
    TopicSuggestionListItem,
    TopicSuggestionResponse,
    TopicSuggestionUpdate,
)
from app.services.research import ResearchService
from app.services.upload import UploadService
from app.utils.dependencies import get_current_tenant_id, get_tenant_config

router = APIRouter(prefix="/research", tags=["research"])


# --- Sources ---


@router.post(
    "/sources",
    response_model=ResearchSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_source(
    data: ResearchSourceCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ResearchSourceResponse:
    """Create a new research source."""
    try:
        service = ResearchService(db)
        return await service.create_source(tenant_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_source")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/sources", response_model=list[ResearchSourceResponse])
async def list_sources(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    source_type: str | None = Query(None),
    active: bool | None = Query(None),
) -> list[ResearchSourceResponse]:
    """List research sources."""
    try:
        service = ResearchService(db)
        return await service.list_sources(
            tenant_id, source_type=source_type, active=active
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_sources")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/sources/{source_id}", response_model=ResearchSourceResponse)
async def get_source(
    source_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ResearchSourceResponse:
    """Get a single research source."""
    try:
        service = ResearchService(db)
        return await service.get_source(tenant_id, source_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_source")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/sources/{source_id}", response_model=ResearchSourceResponse)
async def update_source(
    source_id: int,
    data: ResearchSourceUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ResearchSourceResponse:
    """Update a research source."""
    try:
        service = ResearchService(db)
        return await service.update_source(tenant_id, source_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_source")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    """Delete a research source."""
    try:
        service = ResearchService(db)
        await service.delete_source(tenant_id, source_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_source")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Research Run ---


@router.post("/run", response_model=ResearchRunResponse)
async def run_research(
    data: ResearchRunRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ResearchRunResponse:
    """Trigger a research run (n8n calls this)."""
    try:
        service = ResearchService(db)
        return await service.run_research(tenant_id, data.source_id, tenant_config)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in run_research")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Findings ---


@router.get("/findings", response_model=list[ResearchFindingListItem])
async def list_findings(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    status_filter: str | None = Query(None, alias="status"),
    source_id: int | None = Query(None),
) -> list[ResearchFindingListItem]:
    """List research findings."""
    try:
        service = ResearchService(db)
        return await service.list_findings(
            tenant_id, status=status_filter, source_id=source_id
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_findings")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.patch("/findings/{finding_id}", response_model=ResearchFindingResponse)
async def update_finding(
    finding_id: int,
    data: ResearchFindingStatusUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ResearchFindingResponse:
    """Update finding status."""
    try:
        service = ResearchService(db)
        return await service.update_finding_status(tenant_id, finding_id, data.status)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_finding")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Topic Suggestions ---


@router.post(
    "/topics",
    response_model=TopicSuggestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_topic(
    data: TopicSuggestionCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TopicSuggestionResponse:
    """Create a topic suggestion (Eigene Themen)."""
    try:
        service = ResearchService(db)
        return await service.create_topic(tenant_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_topic")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/topics", response_model=list[TopicSuggestionListItem])
async def list_topics(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    status_filter: str | None = Query(None, alias="status"),
    source_type: str | None = Query(None),
) -> list[TopicSuggestionListItem]:
    """List topic suggestions."""
    try:
        service = ResearchService(db)
        return await service.list_topics(
            tenant_id, status=status_filter, source_type=source_type
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_topics")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/topics/{topic_id}", response_model=TopicSuggestionResponse)
async def update_topic(
    topic_id: int,
    data: TopicSuggestionUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TopicSuggestionResponse:
    """Update a topic suggestion."""
    try:
        service = ResearchService(db)
        return await service.update_topic(tenant_id, topic_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_topic")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(
    topic_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    """Delete a topic suggestion."""
    try:
        service = ResearchService(db)
        await service.delete_topic(tenant_id, topic_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_topic")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/topics/{topic_id}/generate",
    response_model=ContentPieceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_from_topic(
    topic_id: int,
    data: TopicGenerateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ContentPieceResponse:
    """Generate content from a topic suggestion."""
    try:
        service = ResearchService(db)
        return await service.generate_from_topic(
            tenant_id, topic_id, data.platform, data.content_type, tenant_config
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in generate_from_topic")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Image Upload ---


@router.post("/upload/image")
async def upload_image(
    file: UploadFile,
    tenant_id: str = Depends(get_current_tenant_id),
) -> dict:
    """Upload an image for content pieces."""
    try:
        service = UploadService()
        url = await service.save_image(tenant_id, file)
        return {"url": url}
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in upload_image")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
