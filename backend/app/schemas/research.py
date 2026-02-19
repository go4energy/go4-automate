"""Pydantic schemas for research agent."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# --- ResearchSource ---


class ResearchSourceCreate(BaseModel):
    """Input for creating a research source."""

    name: str = Field(..., max_length=200)
    url: str
    source_type: str = Field(..., pattern="^(rss|website|websearch)$")
    keywords: list[str] = Field(default_factory=list)
    fetch_interval_hours: int = 24
    config: dict | None = None


class ResearchSourceUpdate(BaseModel):
    """Partial update for a research source."""

    name: str | None = Field(None, max_length=200)
    url: str | None = None
    source_type: str | None = Field(None, pattern="^(rss|website|websearch)$")
    keywords: list[str] | None = None
    active: bool | None = None
    fetch_interval_hours: int | None = None
    config: dict | None = None


class ResearchSourceResponse(BaseModel):
    """Full response for a research source."""

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
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- ResearchFinding ---


class ResearchFindingResponse(BaseModel):
    """Full response for a research finding."""

    id: int
    tenant_id: str
    source_id: int | None = None
    title: str
    summary: str | None = None
    url: str
    content_snippet: str | None = None
    found_at: datetime
    topics_extracted: list | None = None
    relevance_score: float | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResearchFindingListItem(BaseModel):
    """Lightweight response for finding lists."""

    id: int
    source_id: int | None = None
    title: str
    summary: str | None = None
    url: str
    found_at: datetime
    relevance_score: float | None = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResearchFindingStatusUpdate(BaseModel):
    """Update finding status."""

    status: str = Field(..., pattern="^(new|reviewed|used|dismissed)$")


# --- TopicSuggestion ---


class TopicSuggestionCreate(BaseModel):
    """Input for creating a topic suggestion (manual / eigene Themen)."""

    title: str = Field(..., max_length=300)
    description: str
    category: str = "general"
    platforms: list[str] | None = None
    priority: int = Field(default=3, ge=1, le=5)
    source_type: str = "manual"
    image_url: str | None = None


class TopicSuggestionUpdate(BaseModel):
    """Partial update for a topic suggestion."""

    status: str | None = Field(
        None, pattern="^(suggested|approved|rejected|generating|generated)$"
    )
    priority: int | None = Field(None, ge=1, le=5)
    platforms: list[str] | None = None
    title: str | None = Field(None, max_length=300)
    description: str | None = None
    image_url: str | None = None


class TopicSuggestionResponse(BaseModel):
    """Full response for a topic suggestion."""

    id: int
    tenant_id: str
    finding_id: int | None = None
    title: str
    description: str
    category: str
    platforms: list[str] | None = None
    priority: int
    source_type: str
    status: str
    content_piece_id: int | None = None
    image_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TopicSuggestionListItem(BaseModel):
    """Lightweight response for topic lists."""

    id: int
    finding_id: int | None = None
    title: str
    description: str
    category: str
    platforms: list[str] | None = None
    priority: int
    source_type: str
    status: str
    content_piece_id: int | None = None
    image_url: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Research Run ---


class ResearchRunRequest(BaseModel):
    """Request to trigger a research run."""

    source_id: int | None = None


class ResearchRunResponse(BaseModel):
    """Result summary of a research run."""

    findings_count: int
    suggestions_count: int
    errors: list[str] = Field(default_factory=list)


# --- Topic Generate ---


class TopicGenerateRequest(BaseModel):
    """Request to generate content from a topic."""

    platform: str = "facebook"
    content_type: str = "post"
