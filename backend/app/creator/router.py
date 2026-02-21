"""Creator API router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.creator.config_schema import creator_interface
from app.creator.schemas import (
    CreatorApprove,
    CreatorCalendarCreate,
    CreatorCalendarResponse,
    CreatorGenerate,
    CreatorGenerateFromTopic,
    CreatorPieceCreate,
    CreatorPieceResponse,
    CreatorPieceUpdate,
    CreatorPublishResult,
    ThemeRotation,
)
from app.creator.service import CreatorService
from app.database import get_db
from app.exceptions import AppError
from app.utils.dependencies import get_current_tenant_id, get_tenant_config

router = APIRouter(prefix="/creator", tags=["creator"])

# Register standardized /config, /config/schema, /status, /metrics endpoints
creator_interface.register_endpoints(router)


@router.post(
    "/pieces/generate",
    response_model=CreatorPieceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_piece(
    data: CreatorGenerate,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),
    db: AsyncSession = Depends(get_db),
) -> CreatorPieceResponse:
    """Generate a new content piece via AI."""
    try:
        service = CreatorService(db)
        return await service.generate_content(tenant_id, data, tenant_config)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in generate_piece")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/pieces/generate-from-topic",
    response_model=CreatorPieceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_from_topic(
    data: CreatorGenerateFromTopic,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),
    db: AsyncSession = Depends(get_db),
) -> CreatorPieceResponse:
    """Generate content from a topic (decoupled endpoint)."""
    try:
        service = CreatorService(db)
        return await service.generate_from_topic(tenant_id, data, tenant_config)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in generate_from_topic")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/pieces",
    response_model=CreatorPieceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_piece(
    data: CreatorPieceCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CreatorPieceResponse:
    """Create a new content piece."""
    try:
        service = CreatorService(db)
        return await service.create_piece(tenant_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_piece")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/pieces", response_model=list[CreatorPieceResponse])
async def list_pieces(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
    platform: str | None = Query(None),
    due: bool = Query(False),
    published_last_days: int | None = Query(None),
) -> list[CreatorPieceResponse]:
    """List content pieces for the current tenant."""
    try:
        service = CreatorService(db)
        return await service.list_pieces(
            tenant_id,
            status=status_filter,
            platform=platform,
            due=due,
            published_last_days=published_last_days,
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_pieces")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/pieces/{piece_id}", response_model=CreatorPieceResponse)
async def get_piece(
    piece_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CreatorPieceResponse:
    """Get a single content piece."""
    try:
        service = CreatorService(db)
        return await service.get_piece_by_id(tenant_id, piece_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_piece")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/pieces/{piece_id}", response_model=CreatorPieceResponse)
async def update_piece(
    piece_id: int,
    data: CreatorPieceUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CreatorPieceResponse:
    """Update a content piece."""
    try:
        service = CreatorService(db)
        return await service.update_piece(tenant_id, piece_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_piece")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.patch(
    "/pieces/{piece_id}/approve",
    response_model=CreatorPieceResponse,
)
async def approve_piece(
    piece_id: int,
    data: CreatorApprove,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CreatorPieceResponse:
    """Approve a content piece and set scheduled_at."""
    try:
        service = CreatorService(db)
        return await service.approve_content(tenant_id, piece_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in approve_piece")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/pieces/{piece_id}/publish",
    response_model=CreatorPublishResult,
)
async def publish_piece(
    piece_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CreatorPublishResult:
    """Publish a scheduled content piece immediately."""
    try:
        service = CreatorService(db)
        return await service.publish_content(tenant_id, piece_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in publish_piece")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/pieces/{piece_id}/engagement",
    response_model=CreatorPieceResponse,
)
async def update_engagement(
    piece_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CreatorPieceResponse:
    """Update engagement metrics for a published content piece."""
    try:
        service = CreatorService(db)
        return await service.update_engagement(tenant_id, piece_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_engagement")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/pieces/{piece_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_piece(
    piece_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a content piece."""
    try:
        service = CreatorService(db)
        await service.delete_piece(tenant_id, piece_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_piece")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/themes/rotation", response_model=ThemeRotation)
async def theme_rotation(
    topics: list[str],
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ThemeRotation:
    """Get the next topic from a round-robin rotation."""
    try:
        service = CreatorService(db)
        return await service.get_next_topic(tenant_id, topics)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in theme_rotation")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/calendar",
    response_model=CreatorCalendarResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_calendar_entry(
    data: CreatorCalendarCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CreatorCalendarResponse:
    """Create a calendar entry."""
    try:
        service = CreatorService(db)
        return await service.create_calendar_entry(tenant_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_calendar_entry")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/calendar", response_model=list[CreatorCalendarResponse])
async def list_calendar(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[CreatorCalendarResponse]:
    """List calendar entries for the current tenant."""
    try:
        service = CreatorService(db)
        return await service.list_calendar(tenant_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_calendar")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
