"""Lead schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class LeadCreate(BaseModel):
    """Schema for creating a new lead."""

    email: EmailStr
    name: str
    phone: str | None = None
    source: str | None = None
    konfigurator_data: dict | None = None
    notes: str | None = None


class LeadResponse(BaseModel):
    """Schema for lead response."""

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


class LeadStatusUpdate(BaseModel):
    """Schema for updating lead status."""

    status: str


class LeadFollowupPause(BaseModel):
    """Schema for pausing/resuming follow-up."""

    paused: bool
