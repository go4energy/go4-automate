"""Activity log API router."""

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError
from app.schemas.activity import ActivityLogResponse, ActivityStatsResponse
from app.services.activity import ActivityService
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("", response_model=list[ActivityLogResponse])
async def list_activities(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    module: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[ActivityLogResponse]:
    """List activity log entries."""
    try:
        service = ActivityService(db)
        return await service.list_activities(
            tenant_id, module=module, limit=limit, offset=offset
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_activities")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/stats", response_model=list[ActivityStatsResponse])
async def get_activity_stats(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    days: int = Query(7, ge=1, le=90),
) -> list[ActivityStatsResponse]:
    """Get aggregated activity stats per module."""
    try:
        service = ActivityService(db)
        return await service.get_module_stats(tenant_id, days=days)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_activity_stats")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
