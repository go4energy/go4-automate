"""Ad campaigns API router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError
from app.schemas.ad_campaign import (
    AdCampaignCreate,
    AdCampaignResponse,
    AdCampaignUpdate,
)
from app.services.ad_campaign import AdCampaignService
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/ad-campaigns", tags=["ad-campaigns"])


@router.post(
    "/", response_model=AdCampaignResponse, status_code=status.HTTP_201_CREATED
)
async def create_campaign(
    data: AdCampaignCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> AdCampaignResponse:
    """Create a new ad campaign."""
    try:
        service = AdCampaignService(db)
        return await service.create(tenant_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_campaign")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/", response_model=list[AdCampaignResponse])
async def list_campaigns(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    status_filter: str | None = Query(None, alias="status"),
) -> list[AdCampaignResponse]:
    """List ad campaigns for the current tenant."""
    try:
        service = AdCampaignService(db)
        return await service.list_campaigns(tenant_id, status=status_filter)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_campaigns")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/{campaign_id}", response_model=AdCampaignResponse)
async def get_campaign(
    campaign_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> AdCampaignResponse:
    """Get a single ad campaign."""
    try:
        service = AdCampaignService(db)
        return await service.get_by_id(tenant_id, campaign_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_campaign")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/{campaign_id}", response_model=AdCampaignResponse)
async def update_campaign(
    campaign_id: int,
    data: AdCampaignUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> AdCampaignResponse:
    """Update an ad campaign."""
    try:
        service = AdCampaignService(db)
        return await service.update(tenant_id, campaign_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_campaign")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    """Delete an ad campaign."""
    try:
        service = AdCampaignService(db)
        await service.delete(tenant_id, campaign_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_campaign")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
