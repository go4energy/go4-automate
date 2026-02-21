"""CRM API router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.crm.config_schema import crm_interface
from app.crm.schemas import (
    CrmContactCreate,
    CrmContactResponse,
    CrmContactStatusUpdate,
    CrmFollowupPause,
)
from app.crm.service import CrmService
from app.database import get_db
from app.exceptions import AppError, DuplicateError
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/crm", tags=["crm"])

# Register standardized /config, /config/schema, /status, /metrics endpoints
crm_interface.register_endpoints(router)


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
