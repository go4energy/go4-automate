"""Settings service - module and global config management."""

from pathlib import Path

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import lazyload

from app.config import settings
from app.exceptions import NotFoundError
from app.models.tenant import Tenant
from app.settings.config_schema import GLOBAL_PARAMS, GLOBAL_PARAMS_BY_KEY
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

        # Update tenant.config in DB
        tenant = await self._get_tenant(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant", tenant_id)

        config = dict(tenant.config or {})
        config.update(filtered)
        tenant.config = config
        await self.db.flush()
        await self.db.refresh(tenant)

        # Write to tenant env file
        self._update_env_file(tenant_id, filtered)

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

    def _update_env_file(self, tenant_id: str, updates: dict) -> None:
        """Write updated values to tenant env file."""
        env_path = Path(settings.tenant_config_dir) / f"{tenant_id}.env"
        env_path.parent.mkdir(parents=True, exist_ok=True)

        existing: dict[str, str] = {}
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    existing[key.strip()] = value.strip()

        for key, value in updates.items():
            existing[key.upper()] = str(value)

        lines = [f"{k}={v}" for k, v in sorted(existing.items())]
        env_path.write_text("\n".join(lines) + "\n")
