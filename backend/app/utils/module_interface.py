"""Base module interface for standardized config/status/metrics endpoints."""

from abc import ABC, abstractmethod

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.tenant import TenantService
from app.utils.dependencies import get_current_tenant_id

SECRET_REDACTED = "***configured***"


class ModuleInterface(ABC):
    """Base class for domain module interfaces.

    Each module (Collector, Creator, Distributor, CRM) implements this
    to provide standardized /config, /config/schema, /status, /metrics endpoints.
    """

    MODULE_NAME: str
    PARAMS: list[dict]
    ACTIONS: list[dict] = []
    ENDUSER_CONTROLS: list[dict] = []
    CREDENTIALS: list[dict] = []

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
        _, tenant_config, effective_config = await self._get_tenant_configs(
            db, tenant_id
        )
        module_config = tenant_config.get(self.MODULE_NAME, {})

        config = {}
        for param in self.PARAMS:
            key = param["key"]
            config[key] = module_config.get(key, param.get("default"))

        credentials = {}
        for item in self.get_credentials_schema():
            key = item["key"]
            value = self._get_credential_value(item, module_config, effective_config)
            if item.get("secret") and value not in (None, ""):
                value = SECRET_REDACTED
            credentials[key] = value

        return {
            "module": self.MODULE_NAME,
            "config": config,
            "credentials": credentials,
        }

    async def update_config(
        self, db: AsyncSession, tenant_id: str, updates: dict
    ) -> dict:
        """Update configuration (partial update)."""
        tenant, _, _ = await self._get_tenant_configs(db, tenant_id)
        if not tenant:
            from app.exceptions import NotFoundError

            raise NotFoundError("Tenant", tenant_id)

        config = dict(tenant.config or {})
        module_config = dict(config.get(self.MODULE_NAME, {}))

        valid_keys = {p["key"] for p in self.PARAMS}
        credential_defs = {item["key"]: item for item in self.get_credentials_schema()}
        system_updates = {}

        for key, value in updates.items():
            if key in valid_keys:
                module_config[key] = value
                continue
            if key not in credential_defs or value == SECRET_REDACTED:
                continue

            item = credential_defs[key]
            source = item.get("source", "module_config")
            if source == "module_config":
                module_config[key] = value
            elif source == "system_config":
                system_updates[key] = value
            else:
                from app.exceptions import ValidationError

                raise ValidationError(
                    f"Credential '{key}' mit source '{source}' ist ueber diesen Pfad nicht schreibbar"
                )

        config[self.MODULE_NAME] = module_config
        config.update(system_updates)
        tenant.config = config
        await db.flush()
        await db.refresh(tenant)

        if system_updates:
            TenantService.write_file_updates(tenant_id, system_updates)

        return await self.get_config(db, tenant_id)

    def get_config_schema(self) -> list[dict]:
        """Return parameter schema for this module."""
        return self.PARAMS

    def get_actions_schema(self) -> list[dict]:
        """Return module actions that can be invoked by AI or admin tooling."""
        return self.ACTIONS

    def get_enduser_controls(self) -> list[dict]:
        """Return the small set of controls intended for end users."""
        return self.ENDUSER_CONTROLS

    def get_credentials_schema(self) -> list[dict]:
        """Return credential definitions for AI/admin setup flows."""
        return self.CREDENTIALS

    async def get_setup_schema(self, db: AsyncSession, tenant_id: str) -> dict:
        """Return a unified setup schema for AI and admin workflows."""
        current_config = await self.get_config(db, tenant_id)
        current_values = current_config.get("config", {})
        current_credentials = current_config.get("credentials", {})

        parameters = []
        for param in self.get_config_schema():
            item = dict(param)
            key = item["key"]
            item["value"] = current_values.get(key, item.get("default"))
            item.setdefault("editable_by_ai", True)
            item.setdefault("editable_by_enduser", False)
            item.setdefault("secret", False)
            item.setdefault("requires_confirmation", False)
            item.setdefault("risk_level", "low")
            item.setdefault("source", "module_config")
            parameters.append(item)

        credentials = []
        for credential in self.get_credentials_schema():
            item = dict(credential)
            key = item["key"]
            value = current_credentials.get(key, item.get("default"))
            item["value"] = value
            item["configured"] = value not in (None, "", False)
            item.setdefault("editable_by_ai", True)
            item.setdefault("editable_by_enduser", False)
            item.setdefault("secret", False)
            item.setdefault("requires_confirmation", False)
            item.setdefault("risk_level", "low")
            credentials.append(item)

        return {
            "module": self.MODULE_NAME,
            "parameters": parameters,
            "actions": self.get_actions_schema(),
            "enduser_controls": self.get_enduser_controls(),
            "credentials": credentials,
        }

    async def execute_action(
        self,
        db: AsyncSession,
        tenant_id: str,
        action_key: str,
        payload: dict | None = None,
    ) -> dict:
        """Execute a declared module action."""
        from app.exceptions import ValidationError

        raise ValidationError(
            f"Aktion '{action_key}' ist fuer Modul '{self.MODULE_NAME}' nicht implementiert"
        )

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

        @router.get("/config/setup-schema")
        async def get_setup_schema(
            tenant_id: str = Depends(get_current_tenant_id),
            db: AsyncSession = Depends(get_db),
        ) -> dict:
            return await interface.get_setup_schema(db, tenant_id)

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

    async def _get_tenant_configs(
        self, db: AsyncSession, tenant_id: str
    ) -> tuple[object | None, dict, dict]:
        """Load tenant row plus DB/effective config views."""
        from sqlalchemy import select
        from sqlalchemy.orm import lazyload

        from app.models.tenant import Tenant

        result = await db.execute(
            select(Tenant).where(Tenant.tenant_id == tenant_id).options(lazyload("*"))
        )
        tenant = result.scalar_one_or_none()
        tenant_config = dict(tenant.config or {}) if tenant else {}
        effective_config = TenantService.merge_effective_config(tenant_id, tenant_config)
        return tenant, tenant_config, effective_config

    def _get_credential_value(
        self, item: dict, module_config: dict, effective_config: dict
    ):
        """Resolve current value for a credential definition."""
        key = item["key"]
        source = item.get("source", "module_config")
        if source == "module_config":
            return module_config.get(key, item.get("default"))
        if source == "system_config":
            return effective_config.get(key, item.get("default"))
        return item.get("default")
