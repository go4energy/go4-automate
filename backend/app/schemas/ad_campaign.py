"""Ad campaign schemas."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AdCampaignCreate(BaseModel):
    """Schema for creating an ad campaign."""

    platform: str
    platform_campaign_id: str | None = None
    name: str
    objective: str | None = None
    status: str = "draft"
    daily_budget: Decimal | None = None
    total_budget: Decimal | None = None
    start_date: date | None = None
    end_date: date | None = None


class AdCampaignUpdate(BaseModel):
    """Schema for updating an ad campaign."""

    platform: str | None = None
    platform_campaign_id: str | None = None
    name: str | None = None
    objective: str | None = None
    status: str | None = None
    daily_budget: Decimal | None = None
    total_budget: Decimal | None = None
    start_date: date | None = None
    end_date: date | None = None
    spend: Decimal | None = None
    impressions: int | None = None
    clicks: int | None = None
    ctr: Decimal | None = None
    cpc: Decimal | None = None
    conversions: int | None = None
    cost_per_lead: Decimal | None = None
    roas: Decimal | None = None


class AdCampaignResponse(BaseModel):
    """Schema for ad campaign response."""

    id: int
    tenant_id: str
    platform: str
    platform_campaign_id: str | None = None
    name: str
    objective: str | None = None
    status: str
    daily_budget: Decimal | None = None
    total_budget: Decimal | None = None
    start_date: date | None = None
    end_date: date | None = None
    spend: Decimal
    impressions: int
    clicks: int
    ctr: Decimal
    cpc: Decimal
    conversions: int
    cost_per_lead: Decimal
    roas: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
