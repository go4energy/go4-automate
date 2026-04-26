"""Licensing API: read enabled modules, grant/revoke per-tenant licenses."""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.licensing.models import TenantModuleLicense
from app.licensing.schemas import (
    EnabledModulesResponse,
    GrantModuleRequest,
    ModuleLicenseResponse,
)
from app.licensing.service import LicensingService
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/licensing", tags=["licensing"])


def _to_response(row: TenantModuleLicense) -> ModuleLicenseResponse:
    return ModuleLicenseResponse(
        module_key=row.module_key,
        enabled_at=row.enabled_at,
        expires_at=row.expires_at,
        plan_tier=row.plan_tier,
        metadata=dict(row.license_metadata or {}),
        is_active=row.is_active(),
    )


@router.get("/enabled", response_model=EnabledModulesResponse)
async def list_enabled_modules(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EnabledModulesResponse:
    """Which modules is this tenant currently licensed for?

    ``permissive=True`` means the tenant has no license rows yet —
    legacy mode where every module works regardless of this list.
    """
    service = LicensingService(db)
    enabled = await service.enabled_modules(tenant_id)
    if "*" in enabled:
        return EnabledModulesResponse(enabled=["*"], permissive=True)
    return EnabledModulesResponse(
        enabled=sorted(enabled), permissive=False
    )


@router.get("/licenses", response_model=list[ModuleLicenseResponse])
async def list_licenses(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[ModuleLicenseResponse]:
    service = LicensingService(db)
    rows = await service.list_for_tenant(tenant_id)
    return [_to_response(r) for r in rows]


@router.post(
    "/licenses",
    response_model=ModuleLicenseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def grant_license(
    data: GrantModuleRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ModuleLicenseResponse:
    """Activate a module for the current tenant. Idempotent (re-grant
    refreshes ``enabled_at`` + ``expires_at``)."""
    service = LicensingService(db)
    row = await service.grant(
        tenant_id,
        data.module_key,
        plan_tier=data.plan_tier,
        expires_at=data.expires_at,
        metadata=data.metadata,
    )
    await db.commit()
    logger.info(
        "Module {m} granted for tenant {t} (tier={tier})",
        m=data.module_key,
        t=tenant_id,
        tier=data.plan_tier,
    )
    return _to_response(row)


@router.delete(
    "/licenses/{module_key}", status_code=status.HTTP_204_NO_CONTENT
)
async def revoke_license(
    module_key: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = LicensingService(db)
    if not await service.revoke(tenant_id, module_key):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Modul '{module_key}' ist nicht aktiviert.",
        )
    await db.commit()
    logger.info("Module {m} revoked for tenant {t}", m=module_key, t=tenant_id)
