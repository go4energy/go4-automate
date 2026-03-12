"""FastAPI dependencies for tenant resolution and common patterns."""

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.tenant import TenantService


async def get_current_tenant_id(
    x_tenant_id: str | None = Header(None),
) -> str:
    """Resolve tenant ID from X-Tenant-ID header or fallback to default."""
    return x_tenant_id or settings.default_tenant_id


async def get_tenant_config(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Load tenant configuration (DB config merged with .env file config)."""
    service = TenantService(db)
    try:
        tenant = await service.get_by_id(tenant_id)
        # Merge .env config with DB config (DB takes precedence)
        env_config = TenantService.load_env_config(tenant_id)
        merged = {**env_config, **(tenant.config or {})}
        return merged
    except Exception:
        # Fallback to .env file config only
        return TenantService.load_env_config(tenant_id)
