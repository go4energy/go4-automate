"""Licensing service: query, grant, revoke per-tenant module access."""

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.licensing.models import TenantModuleLicense

# Modules that are part of the "Core" tier — always usable, never gated.
# (contacts/CRM/funnels are the spine of the platform; integrations carries
# OAuth flows; auth/setup are infrastructural.)
CORE_MODULES: frozenset[str] = frozenset(
    {"auth", "setup", "settings", "integrations", "contacts", "crm", "funnels"}
)


class LicensingService:
    """Read + mutate ``tenant_module_licenses``.

    Permissive-by-default contract:
        if the tenant has *zero* rows in the table → every module is
        considered enabled (legacy / un-licensed tenants keep working).
        As soon as the tenant has any row, only those rows count.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_tenant(
        self, tenant_id: str
    ) -> list[TenantModuleLicense]:
        result = await self.db.execute(
            select(TenantModuleLicense).where(
                TenantModuleLicense.tenant_id == tenant_id
            )
        )
        return list(result.scalars().all())

    async def enabled_modules(self, tenant_id: str) -> set[str]:
        """Return the set of modules the tenant currently has access to.

        Always includes the CORE_MODULES.
        Permissive fallback: if the tenant has no license rows yet, ALL
        modules are returned (the caller is responsible for knowing the
        full module list — see ``app.licensing.middleware`` for how this
        is used).
        """
        rows = await self.list_for_tenant(tenant_id)
        if not rows:
            # Legacy / un-licensed tenant: return a sentinel that the
            # middleware interprets as "all modules allowed".
            return {"*"}
        now = datetime.utcnow()
        active = {r.module_key for r in rows if r.is_active(now)}
        return active | set(CORE_MODULES)

    async def has_access(self, tenant_id: str, module_key: str) -> bool:
        if module_key in CORE_MODULES:
            return True
        enabled = await self.enabled_modules(tenant_id)
        return "*" in enabled or module_key in enabled

    async def grant(
        self,
        tenant_id: str,
        module_key: str,
        *,
        plan_tier: str | None = None,
        expires_at: datetime | None = None,
        metadata: dict | None = None,
    ) -> TenantModuleLicense:
        """Idempotent: re-granting an existing module updates the row."""
        existing = (
            await self.db.execute(
                select(TenantModuleLicense).where(
                    TenantModuleLicense.tenant_id == tenant_id,
                    TenantModuleLicense.module_key == module_key,
                )
            )
        ).scalar_one_or_none()

        now = datetime.utcnow()
        if existing is not None:
            existing.enabled_at = now
            existing.expires_at = expires_at
            if plan_tier is not None:
                existing.plan_tier = plan_tier
            if metadata is not None:
                existing.license_metadata = dict(metadata)
            await self.db.flush()
            return existing

        row = TenantModuleLicense(
            tenant_id=tenant_id,
            module_key=module_key,
            enabled_at=now,
            expires_at=expires_at,
            plan_tier=plan_tier,
            license_metadata=dict(metadata or {}),
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def revoke(self, tenant_id: str, module_key: str) -> bool:
        existing = (
            await self.db.execute(
                select(TenantModuleLicense).where(
                    TenantModuleLicense.tenant_id == tenant_id,
                    TenantModuleLicense.module_key == module_key,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            return False
        await self.db.delete(existing)
        await self.db.flush()
        return True

    async def grant_many(
        self,
        tenant_id: str,
        module_keys: Iterable[str],
        *,
        plan_tier: str | None = None,
        expires_at: datetime | None = None,
    ) -> list[TenantModuleLicense]:
        out: list[TenantModuleLicense] = []
        for key in module_keys:
            row = await self.grant(
                tenant_id, key, plan_tier=plan_tier, expires_at=expires_at
            )
            out.append(row)
        return out


__all__ = ["CORE_MODULES", "LicensingService"]
