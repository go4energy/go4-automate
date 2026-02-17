"""Content API router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError
from app.schemas.content import (
    ContentCalendarCreate,
    ContentCalendarResponse,
    ContentPieceCreate,
    ContentPieceResponse,
    ContentPieceUpdate,
)
from app.services.content import ContentService
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/content", tags=["content"])


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
) -> list[ContentPieceResponse]:
    """List content pieces for the current tenant."""
    try:
        service = ContentService(db)
        return await service.list_pieces(
            tenant_id, status=status_filter, platform=platform
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
