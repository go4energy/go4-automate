"""CRM schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class CrmContactCreate(BaseModel):
    """Schema for creating a new contact."""

    email: EmailStr
    name: str
    phone: str | None = None
    source: str | None = None
    konfigurator_data: dict | None = None
    notes: str | None = None


class CrmContactResponse(BaseModel):
    """Schema for contact response."""

    id: int
    tenant_id: str
    email: str
    name: str
    phone: str | None = None
    source: str | None = None
    score: int
    status: str
    konfigurator_data: dict | None = None
    followup_step: int
    followup_paused: bool
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CrmContactStatusUpdate(BaseModel):
    """Schema for updating contact status."""

    status: str


class CrmFollowupPause(BaseModel):
    """Schema for pausing/resuming follow-up."""

    paused: bool
