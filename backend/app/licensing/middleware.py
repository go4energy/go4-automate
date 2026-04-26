"""FastAPI dependency that gates a request on per-tenant module licensing.

Default contract is **permissive** — see ``LicensingService.enabled_modules``.
A tenant without any license rows behaves like before this feature existed
(everything works). Once a tenant has at least one row, the middleware
becomes restrictive for that tenant only.

Usage in a router:

    from app.licensing.middleware import require_module

    @router.get("/some-endpoint", dependencies=[Depends(require_module("leadgen"))])
    async def ...

NOT wired into existing routers yet. Existing modules continue to work
without licensing checks. Wiring is opt-in per route, so we can roll
this out gradually after validating on go4.energy.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.licensing.service import LicensingService
from app.utils.dependencies import get_current_tenant_id


def require_module(module_key: str):
    """Return a FastAPI dependency that 403s when the tenant lacks the module.

    Permissive: tenants with zero license rows pass through.
    """

    async def _dep(
        tenant_id: str = Depends(get_current_tenant_id),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        service = LicensingService(db)
        if await service.has_access(tenant_id, module_key):
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Modul '{module_key}' ist für diesen Tenant nicht aktiviert. "
                "Bitte im Settings-Bereich aktivieren oder Plan upgraden."
            ),
        )

    return _dep


__all__ = ["require_module"]
