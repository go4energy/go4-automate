"""Tenant service - manages tenant configuration and lifecycle."""

import time
from pathlib import Path
from typing import ClassVar

from dotenv import dotenv_values
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import DuplicateError, NotFoundError
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate


class TenantService:
    """Service for tenant CRUD and config loading."""

    # Class-level TTL cache for tenant configs
    _config_cache: ClassVar[dict[str, tuple[dict, float]]] = {}
    _cache_ttl: ClassVar[int] = 300  # 5 minutes

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_tenants(self) -> list[Tenant]:
        """List all tenants."""
        result = await self.db.execute(select(Tenant).order_by(Tenant.tenant_id))
        return list(result.scalars().all())

    async def get_by_id(self, tenant_id: str) -> Tenant:
        """Get tenant by tenant_id."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.tenant_id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise NotFoundError("Tenant", tenant_id)
        return tenant

    async def create(self, data: TenantCreate) -> Tenant:
        """Create a new tenant."""
        existing = await self.db.execute(
            select(Tenant).where(Tenant.tenant_id == data.tenant_id)
        )
        if existing.scalar_one_or_none():
            raise DuplicateError("Tenant", "tenant_id")

        config = data.config or self.load_file_config(data.tenant_id)
        tenant = Tenant(
            tenant_id=data.tenant_id,
            tenant_name=data.tenant_name,
            config=config,
            active=data.active,
        )
        self.db.add(tenant)
        await self.db.flush()
        await self.db.refresh(tenant)
        logger.info("Tenant erstellt: {tenant_id}", tenant_id=data.tenant_id)
        return tenant

    @classmethod
    def load_file_config(cls, tenant_id: str) -> dict:
        """Load tenant config from config/tenants/*.env with TTL cache."""
        now = time.time()
        cached = cls._config_cache.get(tenant_id)
        if cached and (now - cached[1]) < cls._cache_ttl:
            return cached[0]

        config_dir = Path(settings.tenant_config_dir)
        # Try tenant-specific file first, then fall back to default
        for filename in [f"{tenant_id}.env", "default.env"]:
            env_path = config_dir / filename
            if env_path.exists():
                values = dotenv_values(env_path)
                config = dict(values)
                cls._config_cache[tenant_id] = (config, now)
                logger.debug("Tenant-Config geladen: {path}", path=str(env_path))
                return config

        logger.warning(
            "Keine Tenant-Config gefunden für {tenant_id}", tenant_id=tenant_id
        )
        return {}

    @classmethod
    def load_env_config(cls, tenant_id: str) -> dict:
        """Backward-compatible alias for file-based tenant config loading."""
        return cls.load_file_config(tenant_id)

    @classmethod
    def merge_effective_config(
        cls, tenant_id: str, db_config: dict | None = None
    ) -> dict:
        """Return effective tenant config.

        Precedence:
        1. File-based tenant config in config/tenants/*.env
        2. Runtime overrides stored in tenant.config
        """
        file_config = cls.load_file_config(tenant_id)
        return {**file_config, **(db_config or {})}

    @classmethod
    def write_file_updates(cls, tenant_id: str, updates: dict) -> None:
        """Persist tenant-facing config updates to config/tenants/<tenant>.env."""
        env_path = Path(settings.tenant_config_dir) / f"{tenant_id}.env"
        env_path.parent.mkdir(parents=True, exist_ok=True)

        existing: dict[str, str] = {}
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    existing[key.strip()] = value.strip()

        existing.update({str(k): str(v) for k, v in updates.items()})
        lines = [f"{k}={v}" for k, v in sorted(existing.items())]
        env_path.write_text("\n".join(lines) + "\n")

        cls.clear_config_cache(tenant_id)

    @classmethod
    def clear_config_cache(cls, tenant_id: str | None = None) -> None:
        """Clear cached tenant config for one tenant or all tenants."""
        if tenant_id is None:
            cls._config_cache.clear()
        else:
            cls._config_cache.pop(tenant_id, None)
