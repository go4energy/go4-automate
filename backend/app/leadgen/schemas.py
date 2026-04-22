"""Leadgen Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ---- Campaign ----


class CampaignBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    queries: list[str] = Field(default_factory=list)
    language: str = "de"
    region: str = "DE"
    pv_relevance_threshold: int = Field(default=5, ge=0, le=10)
    target_engagement_pipeline_id: int | None = None


class CampaignCreate(CampaignBase):
    pass


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    queries: list[str] | None = None
    language: str | None = None
    region: str | None = None
    pv_relevance_threshold: int | None = Field(default=None, ge=0, le=10)
    target_engagement_pipeline_id: int | None = None
    status: str | None = None


class CampaignResponse(CampaignBase):
    id: int
    tenant_id: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---- Run ----


class RunResponse(BaseModel):
    id: int
    campaign_id: int
    current_stage: str
    status: str
    processed_count: int
    success_count: int
    error_count: int
    cost_cents: int
    started_at: datetime | None
    completed_at: datetime | None
    last_error: str | None

    model_config = ConfigDict(from_attributes=True)


# ---- Place (minimal for list) ----


class PlaceResponse(BaseModel):
    id: int
    campaign_id: int
    name: str
    address_city: str | None
    address_zip: str | None
    website: str | None
    phone: str | None
    status: str
    contact_id: int | None

    model_config = ConfigDict(from_attributes=True)
