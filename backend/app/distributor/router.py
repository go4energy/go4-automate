"""Distributor API router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.distributor.config_schema import distributor_interface
from app.distributor.schemas import (
    AdDashboardStats,
    AdPerformanceResponse,
    CampaignConfigCreate,
    CampaignConfigResponse,
    CampaignConfigUpdate,
    ConversionEventCreate,
    ConversionEventResponse,
    OptimizationResult,
    WeatherData,
)
from app.distributor.service import AdService
from app.distributor.templates.pixel_snippet import generate_pixel_snippet
from app.exceptions import AppError
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/distributor", tags=["distributor"])

# Register standardized /config, /config/schema, /status, /metrics endpoints
distributor_interface.register_endpoints(router)


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
        service = AdService(db)
        return await service.track_conversion(tenant_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in track_conversion")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Dashboard ---


@router.get("/dashboard", response_model=AdDashboardStats)
async def get_dashboard(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> AdDashboardStats:
    """Get aggregated ad dashboard stats."""
    try:
        service = AdService(db)
        return await service.get_dashboard_stats(tenant_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_dashboard")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Performance History ---


@router.get("/performance", response_model=list[AdPerformanceResponse])
async def get_performance(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    campaign_id: str | None = Query(None),
) -> list[AdPerformanceResponse]:
    """Get daily performance history."""
    try:
        service = AdService(db)
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


@router.get("/campaigns", response_model=list[CampaignConfigResponse])
async def list_campaigns(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[CampaignConfigResponse]:
    """List all configured campaigns."""
    try:
        service = AdService(db)
        return await service.list_campaign_configs(tenant_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_campaigns")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/campaigns/config",
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
        service = AdService(db)
        return await service.configure_campaign(tenant_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_campaign_config")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.patch(
    "/campaigns/{config_id}/config",
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
        service = AdService(db)
        return await service.update_campaign_config(tenant_id, config_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_campaign_config")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Campaign Actions ---


@router.post("/campaigns/{config_id}/pause")
async def pause_campaign_action(
    config_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Pause a campaign on Meta."""
    try:
        service = AdService(db)
        config = await service.get_campaign_config(tenant_id, config_id)
        from app.distributor.meta_ads_client import pause_campaign

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


@router.post("/campaigns/{config_id}/resume")
async def resume_campaign_action(
    config_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Resume a paused campaign on Meta."""
    try:
        service = AdService(db)
        config = await service.get_campaign_config(tenant_id, config_id)
        from app.distributor.meta_ads_client import resume_campaign

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
        service = AdService(db)
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
        service = AdService(db)
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
