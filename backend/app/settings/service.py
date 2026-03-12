"""Settings service - module and global config management."""

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import lazyload

from app.config import settings
from app.exceptions import NotFoundError
from app.models.tenant import Tenant
from app.settings.config_schema import GLOBAL_PARAMS, GLOBAL_PARAMS_BY_KEY
from app.services.tenant import TenantService
from app.utils.module_registry import get_module

SECRET_REDACTED = "***configured***"


class SettingsService:
    """Service for reading and updating platform and module settings."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # --- Module config ---

    async def get_module_config(self, name: str, tenant_id: str) -> dict:
        """Return current config for a module."""
        interface = get_module(name)
        if not interface:
            raise NotFoundError("Modul", name)
        return await interface.get_config(self.db, tenant_id)

    async def update_module_config(
        self, name: str, tenant_id: str, updates: dict
    ) -> dict:
        """Update config for a module."""
        interface = get_module(name)
        if not interface:
            raise NotFoundError("Modul", name)
        return await interface.update_config(self.db, tenant_id, updates)

    async def get_module_status(self, name: str, tenant_id: str) -> dict:
        """Return health status for a module."""
        interface = get_module(name)
        if not interface:
            raise NotFoundError("Modul", name)
        return await interface.get_status(self.db, tenant_id)

    # --- Global config ---

    async def get_global_config(self, tenant_id: str) -> dict:
        """Return current global config values (secrets redacted)."""
        tenant = await self._get_tenant(tenant_id)
        tenant_config = (tenant.config or {}) if tenant else {}

        config = {}
        for param in GLOBAL_PARAMS:
            key = param["key"]
            # Tenant override first, then settings, then default
            if key in tenant_config:
                value = tenant_config[key]
            elif hasattr(settings, key):
                value = getattr(settings, key)
            else:
                value = param.get("default")

            # Redact secrets
            if param["type"] == "secret" and value:
                value = SECRET_REDACTED

            # Convert list to comma-separated string for display
            if isinstance(value, list):
                value = ",".join(str(v) for v in value)

            config[key] = value

        return {"config": config}

    async def update_global_config(self, tenant_id: str, updates: dict) -> dict:
        """Update global config (writes to tenant.config + tenant.env)."""
        # Filter out redacted secrets (user didn't change them)
        filtered = {}
        for key, value in updates.items():
            if value == SECRET_REDACTED:
                continue
            if key not in GLOBAL_PARAMS_BY_KEY:
                continue
            param = GLOBAL_PARAMS_BY_KEY[key]
            if not param.get("editable", True):
                continue
            filtered[key] = value

        if not filtered:
            return await self.get_global_config(tenant_id)

        # Update tenant.config in DB with tenant-facing runtime overrides
        tenant = await self._get_tenant(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant", tenant_id)

        config = dict(tenant.config or {})
        config.update(filtered)
        tenant.config = config
        await self.db.flush()
        await self.db.refresh(tenant)

        TenantService.write_file_updates(tenant_id, filtered)

        logger.info(
            "Global config updated: {keys} for tenant {tenant}",
            keys=list(filtered.keys()),
            tenant=tenant_id,
        )

        return await self.get_global_config(tenant_id)

    # --- Helpers ---

    async def _get_tenant(self, tenant_id: str) -> Tenant | None:
        """Fetch tenant from DB (without eager-loading relationships)."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.tenant_id == tenant_id).options(lazyload("*"))
        )
        return result.scalar_one_or_none()

    # --- Desktop Layout ---

    async def get_desktop_layout(self, tenant_id: str) -> dict:
        """Get desktop layout overrides for modules."""
        tenant = await self._get_tenant(tenant_id)
        if not tenant:
            return {"modules": {}}
        config = tenant.config or {}
        return {"modules": config.get("desktop_layout", {})}

    async def bulk_update_desktop_order(self, tenant_id: str, order_map: dict) -> dict:
        """Bulk update desktop tile order in a single transaction."""
        tenant = await self._get_tenant(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant", tenant_id)

        config = dict(tenant.config or {})
        desktop_layout = dict(config.get("desktop_layout", {}))

        for module_name, order in order_map.items():
            if not isinstance(order, int):
                continue
            module_overrides = dict(desktop_layout.get(module_name, {}))
            module_overrides["order"] = order
            desktop_layout[module_name] = module_overrides

        config["desktop_layout"] = desktop_layout
        tenant.config = config
        await self.db.flush()
        await self.db.refresh(tenant)

        logger.info(
            "Desktop order bulk-updated for {count} modules (tenant: {tenant})",
            count=len(order_map),
            tenant=tenant_id,
        )
        return {"modules": desktop_layout}

    async def update_desktop_layout(
        self, tenant_id: str, module_name: str, updates: dict
    ) -> dict:
        """Update desktop layout for a specific module."""
        tenant = await self._get_tenant(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant", tenant_id)

        config = dict(tenant.config or {})
        desktop_layout = dict(config.get("desktop_layout", {}))

        # Get current module overrides or empty dict
        module_overrides = dict(desktop_layout.get(module_name, {}))

        # Apply updates (only valid keys)
        valid_keys = {"icon", "label", "color", "visible", "order", "external_url"}
        for key, value in updates.items():
            if key in valid_keys:
                if value is None:
                    # Remove override if value is None
                    module_overrides.pop(key, None)
                else:
                    module_overrides[key] = value

        # Update or remove module entry
        if module_overrides:
            desktop_layout[module_name] = module_overrides
        else:
            desktop_layout.pop(module_name, None)

        config["desktop_layout"] = desktop_layout
        tenant.config = config
        await self.db.flush()
        await self.db.refresh(tenant)

        logger.info(
            "Desktop layout updated for {module} (tenant: {tenant})",
            module=module_name,
            tenant=tenant_id,
        )
        return {"modules": desktop_layout}

    async def delete_desktop_override(self, tenant_id: str, module_name: str) -> dict:
        """Remove all desktop overrides for a module (reset to defaults)."""
        tenant = await self._get_tenant(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant", tenant_id)

        config = dict(tenant.config or {})
        desktop_layout = dict(config.get("desktop_layout", {}))
        desktop_layout.pop(module_name, None)

        config["desktop_layout"] = desktop_layout
        tenant.config = config
        await self.db.flush()
        await self.db.refresh(tenant)

        logger.info(
            "Desktop override removed for {module} (tenant: {tenant})",
            module=module_name,
            tenant=tenant_id,
        )
        return {"modules": desktop_layout}
