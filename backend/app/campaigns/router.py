"""Campaigns API router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.campaigns.config_schema import campaigns_interface
from app.campaigns.schemas import (
    CampaignConfigCreate,
    CampaignConfigResponse,
    CampaignConfigUpdate,
    CampaignDashboardStats,
    CampaignPerformanceResponse,
    ConversionEventCreate,
    ConversionEventResponse,
    OptimizationResult,
    WeatherData,
)
from app.campaigns.service import CampaignService
from app.campaigns.templates.pixel_snippet import generate_pixel_snippet
from app.config import settings
from app.database import get_db
from app.exceptions import AppError
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

# Register standardized /config, /config/schema, /status, /metrics endpoints
campaigns_interface.register_endpoints(router)


# --- Conversion Tracking ---


@router.post(
    "/conversions",
    response_model=ConversionEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def track_conversion(
    data: ConversionEventCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ConversionEventResponse:
    """Track a conversion event (from pixel or server-side)."""
    try:
        service = CampaignService(db)
        return await service.track_conversion(tenant_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in track_conversion")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Dashboard ---


@router.get("/dashboard", response_model=CampaignDashboardStats)
async def get_dashboard(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CampaignDashboardStats:
    """Get aggregated campaign dashboard stats."""
    try:
        service = CampaignService(db)
        return await service.get_dashboard_stats(tenant_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_dashboard")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Performance History ---


@router.get("/performance", response_model=list[CampaignPerformanceResponse])
async def get_performance(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    campaign_id: str | None = Query(None),
) -> list[CampaignPerformanceResponse]:
    """Get daily performance history."""
    try:
        service = CampaignService(db)
        return await service.get_performance_history(
            tenant_id, days=days, campaign_id=campaign_id
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_performance")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Campaign Config ---


@router.get("/list", response_model=list[CampaignConfigResponse])
async def list_campaigns(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    pipeline_id: int | None = Query(None),
) -> list[CampaignConfigResponse]:
    """List all configured campaigns."""
    try:
        service = CampaignService(db)
        return await service.list_campaign_configs(tenant_id, pipeline_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_campaigns")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/config",
    response_model=CampaignConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign_config(
    data: CampaignConfigCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CampaignConfigResponse:
    """Create a new campaign configuration."""
    try:
        service = CampaignService(db)
        return await service.configure_campaign(tenant_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_campaign_config")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.patch(
    "/{config_id}/config",
    response_model=CampaignConfigResponse,
)
async def update_campaign_config(
    config_id: int,
    data: CampaignConfigUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CampaignConfigResponse:
    """Update a campaign configuration."""
    try:
        service = CampaignService(db)
        return await service.update_campaign_config(tenant_id, config_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_campaign_config")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Campaign Actions ---


@router.post("/{config_id}/pause")
async def pause_campaign_action(
    config_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Pause a campaign on Meta."""
    try:
        service = CampaignService(db)
        config = await service.get_campaign_config(tenant_id, config_id)
        from app.campaigns.meta_ads_client import pause_campaign

        result = await pause_campaign(
            config.campaign_id, settings.meta_system_user_token
        )
        config.status = "paused"
        await db.flush()
        return {"status": "paused", "meta_response": result}
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in pause_campaign_action")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/{config_id}/resume")
async def resume_campaign_action(
    config_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Resume a paused campaign on Meta."""
    try:
        service = CampaignService(db)
        config = await service.get_campaign_config(tenant_id, config_id)
        from app.campaigns.meta_ads_client import resume_campaign

        result = await resume_campaign(
            config.campaign_id, settings.meta_system_user_token
        )
        config.status = "active"
        await db.flush()
        return {"status": "active", "meta_response": result}
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in resume_campaign_action")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Optimization ---


@router.post("/optimize", response_model=list[OptimizationResult])
async def run_optimization(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[OptimizationResult]:
    """Run budget optimization for all active campaigns."""
    try:
        service = CampaignService(db)
        return await service.run_optimization(tenant_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in run_optimization")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Weather ---


@router.get("/weather", response_model=WeatherData)
async def get_weather(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> WeatherData:
    """Get current weather data for budget boost decisions."""
    try:
        service = CampaignService(db)
        return await service.get_weather()
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_weather")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Pixel Snippet ---


@router.get("/pixel-snippet")
async def get_pixel_snippet() -> dict:
    """Get the Meta Pixel JavaScript snippet for embedding."""
    pixel_id = settings.meta_pixel_id
    if not pixel_id:
        raise HTTPException(status_code=400, detail="Meta Pixel ID nicht konfiguriert")
    snippet = generate_pixel_snippet(pixel_id, f"https://{settings.domain}")
    return {"pixel_id": pixel_id, "snippet": snippet}
