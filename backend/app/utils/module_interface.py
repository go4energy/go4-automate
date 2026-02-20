"""Base module interface for standardized config/status/metrics endpoints."""

from abc import ABC, abstractmethod

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.utils.dependencies import get_current_tenant_id


class ModuleInterface(ABC):
    """Base class for domain module interfaces.

    Each module (Collector, Creator, Distributor, CRM) implements this
    to provide standardized /config, /config/schema, /status, /metrics endpoints.
    """

    MODULE_NAME: str
    PARAMS: list[dict]

    @abstractmethod
    async def get_status(self, db: AsyncSession, tenant_id: str) -> dict:
        """Return module health and operational status."""

    @abstractmethod
    async def get_metrics(self, db: AsyncSession, tenant_id: str, days: int) -> dict:
        """Return module KPIs for the given time period."""

    async def get_config(self, db: AsyncSession, tenant_id: str) -> dict:
        """Return current configuration (all parameters + values).

        Default: reads from tenant config JSON, falls back to PARAMS defaults.
        """
        from sqlalchemy import select

        from app.models.tenant import Tenant

        result = await db.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))
        tenant = result.scalar_one_or_none()
        tenant_config = (tenant.config or {}) if tenant else {}
        module_config = tenant_config.get(self.MODULE_NAME, {})

        config = {}
        for param in self.PARAMS:
            key = param["key"]
            config[key] = module_config.get(key, param.get("default"))

        return {
            "module": self.MODULE_NAME,
            "config": config,
        }

    async def update_config(
        self, db: AsyncSession, tenant_id: str, updates: dict
    ) -> dict:
        """Update configuration (partial update)."""
        from sqlalchemy import select

        from app.models.tenant import Tenant

        result = await db.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            from app.exceptions import NotFoundError

            raise NotFoundError("Tenant", tenant_id)

        config = dict(tenant.config or {})
        module_config = dict(config.get(self.MODULE_NAME, {}))

        valid_keys = {p["key"] for p in self.PARAMS}
        for key, value in updates.items():
            if key in valid_keys:
                module_config[key] = value

        config[self.MODULE_NAME] = module_config
        tenant.config = config
        await db.flush()
        await db.refresh(tenant)

        return await self.get_config(db, tenant_id)

    def get_config_schema(self) -> list[dict]:
        """Return parameter schema for this module."""
        return self.PARAMS

    def register_endpoints(self, router: APIRouter) -> None:
        """Register standardized /config, /config/schema, /status, /metrics endpoints."""
        interface = self

        @router.get("/config")
        async def get_config(
            tenant_id: str = Depends(get_current_tenant_id),
            db: AsyncSession = Depends(get_db),
        ) -> dict:
            return await interface.get_config(db, tenant_id)

        @router.put("/config")
        async def update_config(
            updates: dict,
            tenant_id: str = Depends(get_current_tenant_id),
            db: AsyncSession = Depends(get_db),
        ) -> dict:
            return await interface.update_config(db, tenant_id, updates)

        @router.get("/config/schema")
        async def get_config_schema() -> list[dict]:
            return interface.get_config_schema()

        @router.get("/status")
        async def get_status(
            tenant_id: str = Depends(get_current_tenant_id),
            db: AsyncSession = Depends(get_db),
        ) -> dict:
            return await interface.get_status(db, tenant_id)

        @router.get("/metrics")
        async def get_metrics(
            tenant_id: str = Depends(get_current_tenant_id),
            db: AsyncSession = Depends(get_db),
            days: int = Query(7, ge=1, le=365),
        ) -> dict:
            return await interface.get_metrics(db, tenant_id, days)
