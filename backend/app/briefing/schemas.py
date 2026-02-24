"""Briefing schemas - Admin + Listener API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# --- Speaker (XTTS Voice Cloning) ---


class SpeakerResponse(BaseModel):
    """Full response for a briefing speaker."""

    id: int
    tenant_id: str
    name: str
    description: str | None = None
    language: str
    file_size_bytes: int | None = None
    duration_seconds: int | None = None
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Channel (Admin) ---


class ChannelCreate(BaseModel):
    """Input for creating a briefing channel."""

    name: str = Field(..., max_length=200)
    slug: str = Field(..., max_length=100, pattern=r"^[a-z0-9][a-z0-9-]*$")
    description: str | None = None
    target_audience: str | None = Field(None, max_length=200)
    tags: list[str] = Field(default_factory=list)
    streams: list[str] = Field(default_factory=list)
    schedule: str | None = Field(None, max_length=50)
    voice: str = "de_DE-thorsten-high"
    language: str = "de"
    intro_text: str | None = None
    outro_text: str | None = None
    personal_context_enabled: bool = False
    max_items: int = Field(default=10, ge=1, le=50)
    max_duration_minutes: int = Field(default=5, ge=1, le=30)
    cover_image_url: str | None = None
    output_format: str = "audio"
    text_format: str = "markdown"
    tts_engine: str | None = None
    xtts_speaker_id: int | None = None


class ChannelUpdate(BaseModel):
    """Partial update for a briefing channel."""

    name: str | None = Field(None, max_length=200)
    description: str | None = None
    target_audience: str | None = Field(None, max_length=200)
    tags: list[str] | None = None
    streams: list[str] | None = None
    schedule: str | None = Field(None, max_length=50)
    voice: str | None = None
    language: str | None = None
    intro_text: str | None = None
    outro_text: str | None = None
    personal_context_enabled: bool | None = None
    max_items: int | None = Field(None, ge=1, le=50)
    max_duration_minutes: int | None = Field(None, ge=1, le=30)
    active: bool | None = None
    cover_image_url: str | None = None
    output_format: str | None = None
    text_format: str | None = None
    tts_engine: str | None = None
    xtts_speaker_id: int | None = None


class ChannelResponse(BaseModel):
    """Full response for a briefing channel."""

    id: int
    tenant_id: str
    user_id: int | None = None
    cloned_from_id: int | None = None
    name: str
    slug: str
    description: str | None = None
    target_audience: str | None = None
    tags: list[str] = Field(default_factory=list)
    streams: list[str] = Field(default_factory=list)
    schedule: str | None = None
    voice: str
    language: str
    intro_text: str | None = None
    outro_text: str | None = None
    personal_context_enabled: bool
    max_items: int
    max_duration_minutes: int
    active: bool
    cover_image_url: str | None = None
    output_format: str = "audio"
    text_format: str = "markdown"
    tts_engine: str | None = None
    xtts_speaker_id: int | None = None
    episode_count: int = 0
    subscriber_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChannelListItem(BaseModel):
    """Lightweight channel for list views."""

    id: int
    user_id: int | None = None
    cloned_from_id: int | None = None
    name: str
    slug: str
    target_audience: str | None = None
    active: bool
    episode_count: int = 0
    subscriber_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Episode (Admin + Listener) ---


class EpisodeResponse(BaseModel):
    """Full response for a briefing episode."""

    id: int
    tenant_id: str
    channel_id: int
    episode_number: int
    title: str
    transcript: str | None = None
    summary: str | None = None
    audio_url: str | None = None
    audio_duration_seconds: int | None = None
    audio_size_bytes: int | None = None
    audio_mime_type: str = "audio/wav"
    findings_used: list | None = None
    status: str
    error_message: str | None = None
    text_content: str | None = None
    output_format: str = "audio"
    generated_at: datetime | None = None
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EpisodeListItem(BaseModel):
    """Lightweight episode for list views."""

    id: int
    channel_id: int
    episode_number: int
    title: str
    summary: str | None = None
    audio_url: str | None = None
    audio_duration_seconds: int | None = None
    output_format: str = "audio"
    status: str
    published_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Listener User (Admin) ---


class ListenerUserCreate(BaseModel):
    """Input for creating a listener user (admin)."""

    email: str = Field(..., max_length=200)
    password: str = Field(..., min_length=6)
    display_name: str | None = Field(None, max_length=100)
    role: str | None = Field(None, max_length=50)


class ListenerUserResponse(BaseModel):
    """Full response for a listener user."""

    id: int
    tenant_id: str
    email: str
    display_name: str | None = None
    role: str | None = None
    active: bool
    last_login_at: datetime | None = None
    subscription_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Listener Auth ---


class RegisterRequest(BaseModel):
    """Self-registration request."""

    email: str = Field(..., max_length=200)
    password: str = Field(..., min_length=6)
    display_name: str | None = Field(None, max_length=100)
    role: str | None = Field(None, max_length=50)


class LoginRequest(BaseModel):
    """Login request."""

    email: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    user: "ListenerProfileResponse"


# --- Listener Profile ---


class ListenerProfileResponse(BaseModel):
    """Listener user profile response."""

    id: int
    email: str
    display_name: str | None = None
    role: str | None = None
    preferences: dict = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdate(BaseModel):
    """Update listener profile."""

    display_name: str | None = Field(None, max_length=100)
    role: str | None = Field(None, max_length=50)


# --- Listener Subscription ---


class SubscriptionCreate(BaseModel):
    """Subscribe to a channel."""

    channel_id: int


class SubscriptionResponse(BaseModel):
    """Subscription response with channel info."""

    id: int
    channel_id: int
    channel_name: str = ""
    channel_slug: str = ""
    subscribed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# --- Listener Feedback ---


class FeedbackCreate(BaseModel):
    """Submit feedback on an episode."""

    episode_id: int
    finding_id: int | None = None
    rating: str = Field(..., pattern=r"^(interesting|irrelevant|more)$")


class FeedbackResponse(BaseModel):
    """Feedback response."""

    id: int
    user_id: int
    episode_id: int
    finding_id: int | None = None
    rating: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Listener External Feed ---


class ExternalFeedCreate(BaseModel):
    """Add a personal RSS feed."""

    name: str = Field(..., max_length=200)
    url: str = Field(..., max_length=500)


class ExternalFeedResponse(BaseModel):
    """External feed response."""

    id: int
    name: str
    url: str
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Briefing Source ---


class BriefingSourceCreate(BaseModel):
    """Input for creating a briefing source."""

    name: str = Field(..., max_length=200)
    source_type: str = Field(
        ..., pattern=r"^(rss|website|websearch|calendar|email|kpi)$"
    )
    url: str | None = None
    keywords: list[str] = Field(default_factory=list)
    active: bool = True
    fetch_interval_hours: int = Field(default=24, ge=1, le=720)
    config: dict | None = None
    tags: list[str] = Field(default_factory=list)
    streams: list[str] = Field(default_factory=list)


class BriefingSourceUpdate(BaseModel):
    """Partial update for a briefing source."""

    name: str | None = Field(None, max_length=200)
    url: str | None = None
    keywords: list[str] | None = None
    active: bool | None = None
    fetch_interval_hours: int | None = Field(None, ge=1, le=720)
    config: dict | None = None
    tags: list[str] | None = None
    streams: list[str] | None = None


class BriefingSourceResponse(BaseModel):
    """Full response for a briefing source."""

    id: int
    tenant_id: str
    user_id: int | None = None
    name: str
    source_type: str
    url: str | None = None
    keywords: list[str] = Field(default_factory=list)
    active: bool
    fetch_interval_hours: int
    last_fetched_at: datetime | None = None
    config: dict | None = None
    tags: list[str] = Field(default_factory=list)
    streams: list[str] = Field(default_factory=list)
    oauth_connected: bool = False
    oauth_email: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Briefing Finding ---


class BriefingFindingResponse(BaseModel):
    """Full response for a briefing finding."""

    id: int
    tenant_id: str
    source_id: int | None = None
    title: str
    summary: str | None = None
    url: str
    content_snippet: str | None = None
    found_at: datetime
    relevance_score: float | None = None
    status: str
    source_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    streams: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BriefingFindingUpdate(BaseModel):
    """Update a briefing finding (status change)."""

    status: str = Field(..., pattern=r"^(new|used|dismissed)$")


class BulkDeleteRequest(BaseModel):
    """Bulk delete request."""

    ids: list[int] = Field(..., min_length=1)


class BulkDeleteResponse(BaseModel):
    """Bulk delete response."""

    deleted: int


class ChannelCloneRequest(BaseModel):
    """Request to clone an org channel as personal channel."""

    name: str | None = None
    slug: str | None = None


class BriefingRunResponse(BaseModel):
    """Response for source run operation."""

    sources_processed: int
    findings_new: int
    errors: list[str] = Field(default_factory=list)
