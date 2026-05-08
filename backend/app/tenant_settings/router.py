"""Tenant-Stammdaten REST-Endpoints."""

from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.tenant_settings.schemas import (
    ImpressumPreviewResponse,
    TenantMasterDataResponse,
    TenantMasterDataUpdate,
)
from app.tenant_settings.service import (
    TenantMasterDataService,
    build_disclaimer_block,
    build_impressum_block,
)
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/tenant-settings", tags=["tenant-settings"])


@router.get("/master-data", response_model=TenantMasterDataResponse | None)
async def get_master_data(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> TenantMasterDataResponse | None:
    """Aktuelle Stammdaten zurückgeben (oder null, wenn noch nichts gepflegt)."""
    row = await TenantMasterDataService(db).get(tenant_id)
    if row is None:
        return None
    return TenantMasterDataResponse.model_validate(row)


@router.put("/master-data", response_model=TenantMasterDataResponse)
async def update_master_data(
    data: TenantMasterDataUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> TenantMasterDataResponse:
    """Stammdaten aktualisieren oder anlegen (Upsert)."""
    service = TenantMasterDataService(db)
    row = await service.upsert(tenant_id, data)
    await db.commit()
    logger.info(
        "Tenant-Stammdaten aktualisiert für {tenant}",
        tenant=tenant_id,
    )
    return TenantMasterDataResponse.model_validate(row)


@router.get("/preview-impressum", response_model=ImpressumPreviewResponse)
async def preview_impressum(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ImpressumPreviewResponse:
    """Live-Vorschau des generierten (oder Override-)Impressum-Blocks."""
    service = TenantMasterDataService(db)
    row = await service.get(tenant_id)
    missing = await service.missing_fields(tenant_id)
    html = build_impressum_block(row)
    return ImpressumPreviewResponse(
        impressum_html=html,
        is_override=bool(row and row.impressum_html_override),
        is_complete=len(missing) == 0,
        missing_fields=missing,
    )


@router.get("/preview-disclaimer")
async def preview_disclaimer(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Live-Vorschau des Cold-Mail-DSGVO-Disclaimers."""
    row = await TenantMasterDataService(db).get(tenant_id)
    return {"disclaimer_html": build_disclaimer_block(row)}
