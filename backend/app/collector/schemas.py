"""Collector schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# --- Group ---


class CollectorGroupCreate(BaseModel):
    """Input for creating a collector group."""

    name: str = Field(..., max_length=200)
    slug: str = Field(..., max_length=100, pattern="^[a-z0-9-]+$")
    description: str | None = None
    fetch_interval_hours: int = 24
    distribution_channels: list[dict] | None = None
    tags: list[str] = Field(default_factory=list)
    streams: list[str] = Field(default_factory=list)
    analysis_prompt_slugs: list[str] = Field(default_factory=list)


class CollectorGroupUpdate(BaseModel):
    """Partial update for a collector group."""

    name: str | None = Field(None, max_length=200)
    description: str | None = None
    fetch_interval_hours: int | None = None
    distribution_channels: list[dict] | None = None
    active: bool | None = None
    tags: list[str] | None = None
    streams: list[str] | None = None
    analysis_prompt_slugs: list[str] | None = None


class CollectorGroupResponse(BaseModel):
    """Full response for a collector group."""

    id: int
    tenant_id: str
    name: str
    slug: str
    description: str | None = None
    fetch_interval_hours: int
    distribution_channels: list[dict] | None = None
    active: bool
    tags: list[str] = Field(default_factory=list)
    streams: list[str] = Field(default_factory=list)
    analysis_prompt_slugs: list[str] = Field(default_factory=list)
    source_count: int = 0
    finding_count: int = 0
    topic_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CollectorGroupListItem(BaseModel):
    """Lightweight response for group lists."""

    id: int
    name: str
    slug: str
    active: bool
    analysis_prompt_slugs: list[str] = Field(default_factory=list)
    source_count: int = 0
    finding_count: int = 0
    topic_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroupPromptAddRequest(BaseModel):
    """Request to add a new prompt to a group."""

    purpose: str = Field(..., max_length=50, pattern="^[a-z0-9-]+$")
    source_slug: str | None = None


class GroupPromptAddResponse(BaseModel):
    """Response after adding a prompt to a group."""

    prompt_slug: str
    analysis_prompt_slugs: list[str]


class GroupPromptRunResponse(BaseModel):
    """Response after running a prompt for a group."""

    topics_created: int
    topics_deleted: int


# --- Source ---


class CollectorSourceCreate(BaseModel):
    """Input for creating a collector source."""

    name: str = Field(..., max_length=200)
    url: str = ""
    source_type: str = Field(..., pattern="^(rss|website|websearch|inbox)$")
    keywords: list[str] = Field(default_factory=list)
    fetch_interval_hours: int = 24
    config: dict | None = None
    tags: list[str] = Field(default_factory=list)
    streams: list[str] = Field(default_factory=list)
    change_detection_enabled: bool = False
    group_id: int | None = None


class CollectorSourceUpdate(BaseModel):
    """Partial update for a collector source."""

    name: str | None = Field(None, max_length=200)
    url: str | None = None
    source_type: str | None = Field(None, pattern="^(rss|website|websearch|inbox)$")
    keywords: list[str] | None = None
    active: bool | None = None
    fetch_interval_hours: int | None = None
    config: dict | None = None
    tags: list[str] | None = None
    streams: list[str] | None = None
    change_detection_enabled: bool | None = None
    group_id: int | None = None


class CollectorSourceResponse(BaseModel):
    """Full response for a collector source."""

    id: int
    tenant_id: str
    name: str
    url: str
    source_type: str
    keywords: list[str] | None = None
    active: bool
    fetch_interval_hours: int
    last_fetched_at: datetime | None = None
    config: dict | None = None
    tags: list[str] = Field(default_factory=list)
    streams: list[str] = Field(default_factory=list)
    change_detection_enabled: bool = False
    group_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Finding ---


class CollectorFindingResponse(BaseModel):
    """Full response for a collector finding."""

    id: int
    tenant_id: str
    source_id: int | None = None
    group_id: int | None = None
    title: str
    summary: str | None = None
    url: str
    content_snippet: str | None = None
    found_at: datetime
    topics_extracted: list | None = None
    relevance_score: float | None = None
    status: str
    tags: list[str] = Field(default_factory=list)
    streams: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CollectorFindingListItem(BaseModel):
    """Lightweight response for finding lists."""

    id: int
    source_id: int | None = None
    group_id: int | None = None
    title: str
    summary: str | None = None
    url: str
    found_at: datetime
    relevance_score: float | None = None
    status: str
    tags: list[str] = Field(default_factory=list)
    streams: list[str] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CollectorFindingUpdate(BaseModel):
    """Partial update for a finding (status and/or group)."""

    status: str | None = Field(None, pattern="^(new|reviewed|used|dismissed)$")
    group_id: int | None = None
    streams: list[str] | None = None


# --- Topic ---


class CollectorTopicCreate(BaseModel):
    """Input for creating a topic (manual / eigene Themen)."""

    title: str = Field(..., max_length=300)
    description: str
    detail: str | None = None
    category: str = "general"
    platforms: list[str] | None = None
    priority: int = Field(default=3, ge=1, le=5)
    source_type: str = "manual"
    image_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    streams: list[str] = Field(default_factory=list)
    group_id: int | None = None


class CollectorTopicUpdate(BaseModel):
    """Partial update for a topic."""

    status: str | None = Field(
        None, pattern="^(suggested|approved|rejected|generating|generated)$"
    )
    priority: int | None = Field(None, ge=1, le=5)
    platforms: list[str] | None = None
    title: str | None = Field(None, max_length=300)
    description: str | None = None
    detail: str | None = None
    image_url: str | None = None
    tags: list[str] | None = None
    streams: list[str] | None = None
    group_id: int | None = None
    prompt_slug: str | None = None


class CollectorTopicResponse(BaseModel):
    """Full response for a topic."""

    id: int
    tenant_id: str
    finding_id: int | None = None
    group_id: int | None = None
    title: str
    description: str
    detail: str | None = None
    category: str
    platforms: list[str] | None = None
    priority: int
    source_type: str
    status: str
    content_piece_id: int | None = None
    image_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    streams: list[str] = Field(default_factory=list)
    target_modules: list[str] | None = None
    prompt_slug: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CollectorTopicListItem(BaseModel):
    """Lightweight response for topic lists."""

    id: int
    finding_id: int | None = None
    group_id: int | None = None
    title: str
    description: str
    detail: str | None = None
    category: str
    platforms: list[str] | None = None
    priority: int
    source_type: str
    status: str
    content_piece_id: int | None = None
    image_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    streams: list[str] = Field(default_factory=list)
    prompt_slug: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CollectorTopicDetailResponse(CollectorTopicResponse):
    """Extended response for topic detail view with finding info."""

    finding_url: str | None = None
    finding_title: str | None = None


# --- Run ---


class CollectorRunRequest(BaseModel):
    """Request to trigger a collector run."""

    source_id: int | None = None


class CollectorRunResponse(BaseModel):
    """Result summary of a collector run."""

    findings_count: int
    suggestions_count: int
    errors: list[str] = Field(default_factory=list)


# --- Topic Generate ---


class TopicGenerateRequest(BaseModel):
    """Request to generate content from a topic."""

    platform: str = "facebook"
    content_type: str = "post"


# --- Finding Import (generic, for n8n) ---


class FindingImport(BaseModel):
    """Generic finding import for external systems (n8n, webhooks)."""

    title: str = Field(..., max_length=500)
    url: str
    summary: str | None = None
    content_snippet: str | None = None
    tags: list[str] = Field(default_factory=list)
    source_id: int | None = None
    group_id: int | None = None


# --- Inbox ---


class InboxItemCreate(BaseModel):
    """Input for content inbox (WhatsApp/Email)."""

    text: str
    image_url: str | None = None
    source_channel: str = "whatsapp"
    tags: list[str] = Field(default_factory=list)


# --- Bulk Operations ---


class BulkDeleteRequest(BaseModel):
    """Request to bulk delete items."""

    ids: list[int] = Field(..., min_length=1)


class BulkDeleteResponse(BaseModel):
    """Response for bulk delete."""

    deleted: int


class AnalyzeFindingResponse(BaseModel):
    """Response for analyzing a single finding."""

    topics_count: int


# --- Snapshot ---


class PageSnapshotResponse(BaseModel):
    """Response for a page snapshot."""

    id: int
    tenant_id: str
    source_id: int
    url: str
    content_hash: str
    snapshot_at: datetime
    diff_from_previous: str | None = None
    change_summary: str | None = None
    change_significance: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChangeDetectionResponse(BaseModel):
    """Result of a change detection run."""

    changed: bool
    significance: str | None = None
    summary: str | None = None
    snapshot_id: int | None = None
