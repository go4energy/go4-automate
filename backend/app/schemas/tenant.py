"""Tenant schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TenantCreate(BaseModel):
    """Schema for creating a new tenant."""

    tenant_id: str
    tenant_name: str
    config: dict | None = None
    active: bool = True


class TenantResponse(BaseModel):
    """Schema for tenant response."""

    id: int
    tenant_id: str
    tenant_name: str
    config: dict | None = None
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
