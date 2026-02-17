"""Content API router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError
from app.schemas.content import (
    ContentApprove,
    ContentCalendarCreate,
    ContentCalendarResponse,
    ContentGenerate,
    ContentPieceCreate,
    ContentPieceResponse,
    ContentPieceUpdate,
    ContentPublishResult,
    ThemeRotation,
)
from app.services.content import ContentService
from app.utils.dependencies import get_current_tenant_id, get_tenant_config

router = APIRouter(prefix="/content", tags=["content"])


@router.post(
    "/pieces/generate",
    response_model=ContentPieceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_piece(
    data: ContentGenerate,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ContentPieceResponse:
    """Generate a new content piece via AI."""
    try:
        service = ContentService(db)
        return await service.generate_content(tenant_id, data, tenant_config)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in generate_piece")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/pieces",
    response_model=ContentPieceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_piece(
    data: ContentPieceCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ContentPieceResponse:
    """Create a new content piece."""
    try:
        service = ContentService(db)
        return await service.create_piece(tenant_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_piece")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/pieces", response_model=list[ContentPieceResponse])
async def list_pieces(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    status_filter: str | None = Query(None, alias="status"),
    platform: str | None = Query(None),
    due: bool = Query(False),
    published_last_days: int | None = Query(None),
) -> list[ContentPieceResponse]:
    """List content pieces for the current tenant."""
    try:
        service = ContentService(db)
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


@router.get("/pieces/{piece_id}", response_model=ContentPieceResponse)
async def get_piece(
    piece_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ContentPieceResponse:
    """Get a single content piece."""
    try:
        service = ContentService(db)
        return await service.get_piece_by_id(tenant_id, piece_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_piece")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/pieces/{piece_id}", response_model=ContentPieceResponse)
async def update_piece(
    piece_id: int,
    data: ContentPieceUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ContentPieceResponse:
    """Update a content piece."""
    try:
        service = ContentService(db)
        return await service.update_piece(tenant_id, piece_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_piece")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.patch(
    "/pieces/{piece_id}/approve",
    response_model=ContentPieceResponse,
)
async def approve_piece(
    piece_id: int,
    data: ContentApprove,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ContentPieceResponse:
    """Approve a content piece and set scheduled_at."""
    try:
        service = ContentService(db)
        return await service.approve_content(tenant_id, piece_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in approve_piece")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/pieces/{piece_id}/publish",
    response_model=ContentPublishResult,
)
async def publish_piece(
    piece_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ContentPublishResult:
    """Publish a scheduled content piece immediately."""
    try:
        service = ContentService(db)
        return await service.publish_content(tenant_id, piece_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in publish_piece")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/pieces/{piece_id}/engagement",
    response_model=ContentPieceResponse,
)
async def update_engagement(
    piece_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ContentPieceResponse:
    """Update engagement metrics for a published content piece."""
    try:
        service = ContentService(db)
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
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    """Delete a content piece."""
    try:
        service = ContentService(db)
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
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ThemeRotation:
    """Get the next topic from a round-robin rotation."""
    try:
        service = ContentService(db)
        return await service.get_next_topic(tenant_id, topics)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in theme_rotation")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/calendar",
    response_model=ContentCalendarResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_calendar_entry(
    data: ContentCalendarCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ContentCalendarResponse:
    """Create a calendar entry."""
    try:
        service = ContentService(db)
        return await service.create_calendar_entry(tenant_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_calendar_entry")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/calendar", response_model=list[ContentCalendarResponse])
async def list_calendar(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[ContentCalendarResponse]:
    """List calendar entries for the current tenant."""
    try:
        service = ContentService(db)
        return await service.list_calendar(tenant_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_calendar")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
