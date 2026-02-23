"""Creator schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreatorPieceCreate(BaseModel):
    """Schema for creating a content piece."""

    title: str
    topic: str | None = None
    content_type: str
    platform: str
    caption: str | None = None
    short: str | None = None
    hashtags: str | None = None
    hook: str | None = None
    cta: str | None = None
    media_urls: list[str] | None = None
    status: str = "draft"
    scheduled_at: datetime | None = None
    funnel_stage: str | None = None
    buyer_persona: str | None = None
    created_by: str | None = None
    ai_model: str | None = None
    tags: list[str] = Field(default_factory=list)
    streams: list[str] = Field(default_factory=list)


class CreatorPieceUpdate(BaseModel):
    """Schema for updating a content piece."""

    title: str | None = None
    topic: str | None = None
    content_type: str | None = None
    platform: str | None = None
    caption: str | None = None
    short: str | None = None
    hashtags: str | None = None
    hook: str | None = None
    cta: str | None = None
    media_urls: list[str] | None = None
    status: str | None = None
    scheduled_at: datetime | None = None
    posted_at: datetime | None = None
    funnel_stage: str | None = None
    buyer_persona: str | None = None
    reach: int | None = None
    impressions: int | None = None
    engagement: int | None = None
    engagement_rate: float | None = None
    link_clicks: int | None = None
    leads_generated: int | None = None
    meta_post_id: str | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    error_message: str | None = None
    tags: list[str] | None = None
    streams: list[str] | None = None


class CreatorPieceResponse(BaseModel):
    """Schema for content piece response."""

    id: int
    tenant_id: str
    title: str
    topic: str | None = None
    content_type: str
    platform: str
    caption: str | None = None
    short: str | None = None
    hashtags: str | None = None
    hook: str | None = None
    cta: str | None = None
    media_urls: list | None = None
    status: str
    scheduled_at: datetime | None = None
    posted_at: datetime | None = None
    funnel_stage: str | None = None
    buyer_persona: str | None = None
    reach: int
    impressions: int
    engagement: int
    engagement_rate: float
    link_clicks: int
    leads_generated: int
    created_by: str | None = None
    ai_model: str | None = None
    meta_post_id: str | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    error_message: str | None = None
    tags: list[str] = Field(default_factory=list)
    streams: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreatorGenerate(BaseModel):
    """Schema for AI content generation request."""

    topic: str
    platform: str
    content_type: str
    funnel_stage: str | None = None
    buyer_persona: str | None = None
    additional_instructions: str | None = None


class CreatorGenerateFromTopic(BaseModel):
    """Schema for generating content from a collector topic."""

    title: str
    description: str
    platform: str = "facebook"
    content_type: str = "post"
    image_url: str | None = None


class CreatorApprove(BaseModel):
    """Schema for approving a content piece."""

    approved_by: str
    scheduled_at: datetime


class CreatorPublishResult(BaseModel):
    """Schema for content publish result."""

    id: int
    platform: str
    status: str
    meta_post_id: str | None = None
    error_message: str | None = None
    posted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ThemeRotation(BaseModel):
    """Schema for theme rotation response."""

    next_topic: str
    topics: list[str]
    last_used_index: int


class CreatorCalendarCreate(BaseModel):
    """Schema for creating a calendar entry."""

    content_id: int
    platform: str
    scheduled_at: datetime
    time_slot: str | None = None


class CreatorCalendarResponse(BaseModel):
    """Schema for calendar entry response."""

    id: int
    tenant_id: str
    content_id: int
    platform: str
    scheduled_at: datetime
    time_slot: str | None = None
    is_posted: bool
    posted_platform_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
