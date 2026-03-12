"""FastAPI dependencies for tenant resolution and common patterns."""

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.tenant import TenantService


async def get_current_tenant_id(
    x_tenant_id: str | None = Header(None),
) -> str:
    """Resolve tenant ID from X-Tenant-ID header.

    Protected API routes should already enforce the header in middleware.
    The default fallback remains for public/special flows that still call this
    dependency without tenant-scoped auth requirements.
    """
    return x_tenant_id or settings.default_tenant_id


async def get_tenant_config(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Load tenant configuration (DB config merged with .env file config)."""
    service = TenantService(db)
    try:
        tenant = await service.get_by_id(tenant_id)
        return TenantService.merge_effective_config(tenant_id, tenant.config or {})
    except Exception:
        return TenantService.load_file_config(tenant_id)
