"""Ad management schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr


class UserData(BaseModel):
    """User data for Meta Conversion API matching."""

    email: EmailStr | None = None
    phone: str | None = None
    fbc: str | None = None
    fbp: str | None = None
    client_ip: str | None = None
    client_user_agent: str | None = None


class ConversionEventCreate(BaseModel):
    """Schema for incoming conversion events from pixel/website."""

    event_name: Literal[
        "PageView",
        "ViewContent",
        "Lead",
        "InitiateCheckout",
        "Purchase",
        "CompleteRegistration",
    ]
    event_time: datetime
    source_url: str | None = None
    user_agent: str | None = None
    fbc: str | None = None
    fbp: str | None = None
    user_data: UserData | None = None
    custom_data: dict | None = None


class ConversionEventResponse(BaseModel):
    """Schema for conversion event response."""

    id: int
    tenant_id: str
    event_name: str
    event_time: datetime
    sent_to_meta: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdPerformanceResponse(BaseModel):
    """Schema for ad performance response."""

    id: int
    tenant_id: str
    platform: str
    campaign_id: str
    campaign_name: str | None = None
    date: date
    impressions: int
    clicks: int
    spend: Decimal
    leads: int
    cpl: Decimal
    conversions: int
    conversion_value: Decimal
    cpc: Decimal | None = None
    ctr: Decimal | None = None
    frequency: Decimal | None = None
    reach: int | None = None
    budget_applied: Decimal | None = None
    weather_boosted: bool
    optimization_action: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignSummary(BaseModel):
    """Summary of a single campaign for the dashboard."""

    campaign_id: str
    campaign_name: str | None = None
    status: str
    spend: Decimal
    leads: int
    cpl: Decimal
    ctr: Decimal | None = None
    daily_budget: Decimal | None = None


class PeriodStats(BaseModel):
    """Stats for a time period."""

    spend: Decimal = Decimal("0")
    leads: int = 0
    cpl: Decimal = Decimal("0")
    impressions: int = 0


class AdDashboardStats(BaseModel):
    """Aggregated stats for the frontend dashboard."""

    today: PeriodStats
    this_week: PeriodStats
    this_month: PeriodStats
    trend: Literal["improving", "stable", "declining"]
    campaigns: list[CampaignSummary]


class CampaignConfigCreate(BaseModel):
    """Schema for creating a campaign config."""

    campaign_id: str
    campaign_name: str | None = None
    platform: str = "meta"
    target_cpl: Decimal | None = None
    max_cpl: Decimal | None = None
    daily_budget_min: Decimal | None = None
    daily_budget_max: Decimal | None = None
    weather_boost_enabled: bool = True
    weather_boost_factor: Decimal = Decimal("1.5")
    auto_optimize: bool = True
    optimization_rules: dict | None = None
    tags: list[str] = []
    streams: list[str] = []


class CampaignConfigUpdate(BaseModel):
    """Schema for updating a campaign config."""

    campaign_name: str | None = None
    status: str | None = None
    target_cpl: Decimal | None = None
    max_cpl: Decimal | None = None
    daily_budget_min: Decimal | None = None
    daily_budget_max: Decimal | None = None
    weather_boost_enabled: bool | None = None
    weather_boost_factor: Decimal | None = None
    auto_optimize: bool | None = None
    optimization_rules: dict | None = None
    tags: list[str] | None = None
    streams: list[str] | None = None


class CampaignConfigResponse(BaseModel):
    """Schema for campaign config response."""

    id: int
    tenant_id: str
    campaign_id: str
    campaign_name: str | None = None
    platform: str
    status: str
    target_cpl: Decimal | None = None
    max_cpl: Decimal | None = None
    daily_budget_min: Decimal | None = None
    daily_budget_max: Decimal | None = None
    weather_boost_enabled: bool
    weather_boost_factor: Decimal
    auto_optimize: bool
    optimization_rules: dict | None = None
    tags: list[str] = []
    streams: list[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OptimizationResult(BaseModel):
    """Result of a single campaign optimization."""

    campaign_id: str
    campaign_name: str | None = None
    action: str
    previous_budget: Decimal | None = None
    new_budget: Decimal | None = None
    cpl: Decimal | None = None
    leads: int = 0
    weather_boosted: bool = False
    reason: str = ""


class WeatherData(BaseModel):
    """Weather data from OpenWeather API."""

    temp: float
    description: str
    clouds_percent: int
    is_sunny: bool
