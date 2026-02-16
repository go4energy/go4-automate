"""Leads API router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError, DuplicateError
from app.schemas.lead import (
    LeadCreate,
    LeadFollowupPause,
    LeadResponse,
    LeadStatusUpdate,
)
from app.services.lead import LeadService
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("/", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    data: LeadCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> LeadResponse:
    """Create a new lead."""
    try:
        service = LeadService(db)
        return await service.create(tenant_id, data)
    except DuplicateError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_lead")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/", response_model=list[LeadResponse])
async def list_leads(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    status_filter: str | None = Query(None, alias="status"),
    source: str | None = Query(None),
) -> list[LeadResponse]:
    """List leads for the current tenant."""
    try:
        service = LeadService(db)
        return await service.list_leads(tenant_id, status=status_filter, source=source)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_leads")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.patch("/{lead_id}/status", response_model=LeadResponse)
async def update_lead_status(
    lead_id: int,
    data: LeadStatusUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> LeadResponse:
    """Update a lead's status."""
    try:
        service = LeadService(db)
        return await service.update_status(tenant_id, lead_id, data.status)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_lead_status")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.patch("/{lead_id}/pause-followup", response_model=LeadResponse)
async def pause_followup(
    lead_id: int,
    data: LeadFollowupPause,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> LeadResponse:
    """Pause or resume follow-up for a lead."""
    try:
        service = LeadService(db)
        return await service.toggle_followup_pause(tenant_id, lead_id, data.paused)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in pause_followup")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
