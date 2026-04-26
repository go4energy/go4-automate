"""Pydantic schemas for licensing API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModuleLicenseResponse(BaseModel):
    module_key: str
    enabled_at: datetime
    expires_at: datetime | None = None
    plan_tier: str | None = None
    metadata: dict = Field(default_factory=dict)
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class GrantModuleRequest(BaseModel):
    module_key: str = Field(min_length=1, max_length=50)
    plan_tier: str | None = Field(default=None, max_length=30)
    expires_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)


class EnabledModulesResponse(BaseModel):
    """List of module keys this tenant has access to.

    The ``permissive`` flag is True when the tenant has no licence rows
    yet (legacy mode — every module works).
    """

    enabled: list[str]
    permissive: bool
