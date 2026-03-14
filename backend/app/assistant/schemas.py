"""Assistant module Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


class AssistantProfileCreate(BaseModel):
    """Create / ensure profile for current user."""

    timezone: str = "Europe/Vienna"
    delivery_time: str | None = None
    llm_provider: str = "ollama"
    llm_model: str | None = None
    tts_provider: str = "piper"
    tts_voice: str | None = None
    stt_provider: str = "faster-whisper"
    max_items_per_run: int = Field(default=30, ge=1, le=200)
    default_reply_mode: str = "draft"


class AssistantProfileUpdate(BaseModel):
    """Partial update for profile."""

    active: bool | None = None
    briefing_enabled: bool | None = None
    voice_enabled: bool | None = None
    autopilot_enabled: bool | None = None
    timezone: str | None = None
    delivery_time: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    tts_provider: str | None = None
    tts_voice: str | None = None
    stt_provider: str | None = None
    max_items_per_run: int | None = Field(default=None, ge=1, le=200)
    default_reply_mode: str | None = None


class AssistantProfileResponse(BaseModel):
    """Full profile response."""

    id: int
    tenant_id: str
    user_id: int
    active: bool
    briefing_enabled: bool
    voice_enabled: bool
    autopilot_enabled: bool
    timezone: str
    delivery_time: str | None
    llm_provider: str
    llm_model: str | None
    tts_provider: str
    tts_voice: str | None
    stt_provider: str
    max_items_per_run: int
    default_reply_mode: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Source
# ---------------------------------------------------------------------------


class AssistantSourceCreate(BaseModel):
    """Link an integration connection as assistant source."""

    connection_id: int
    briefing_enabled: bool = True
    voice_enabled: bool = False
    reply_enabled: bool = False
    autopilot_enabled: bool = False
    priority: int = Field(default=0, ge=0, le=100)
    settings_json: dict | None = None


class AssistantSourceUpdate(BaseModel):
    """Partial update for source."""

    briefing_enabled: bool | None = None
    voice_enabled: bool | None = None
    reply_enabled: bool | None = None
    autopilot_enabled: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=100)
    settings_json: dict | None = None


class ConnectionInfo(BaseModel):
    """Nested connection details for source response."""

    id: int
    provider: str
    integration_type: str
    connected_email: str | None
    account_label: str | None
    status: str
    last_synced_at: datetime | None
    last_error: str | None

    model_config = ConfigDict(from_attributes=True)


class AssistantSourceResponse(BaseModel):
    """Full source response with connection details."""

    id: int
    tenant_id: str
    user_id: int
    connection_id: int
    briefing_enabled: bool
    voice_enabled: bool
    reply_enabled: bool
    autopilot_enabled: bool
    priority: int
    settings_json: dict | None
    created_at: datetime
    updated_at: datetime
    connection: ConnectionInfo | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Item
# ---------------------------------------------------------------------------


class AssistantItemResponse(BaseModel):
    """Normalised mail / calendar item."""

    id: int
    item_type: str
    external_id: str
    thread_id: str | None
    mailbox_address: str | None
    title: str | None
    summary: str | None
    content_snippet: str | None
    sender: str | None
    occurred_at: datetime | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Rule
# ---------------------------------------------------------------------------


class AssistantRuleCreate(BaseModel):
    """Create a triage rule."""

    name: str = Field(..., max_length=200)
    scope: str = "user"
    priority: int = Field(default=0, ge=0, le=1000)
    match_criteria_json: dict | None = None
    action_type: str = Field(..., max_length=50)
    action_payload_json: dict | None = None
    risk_level: str = "low"


class AssistantRuleUpdate(BaseModel):
    """Partial update for rule."""

    name: str | None = Field(default=None, max_length=200)
    enabled: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=1000)
    match_criteria_json: dict | None = None
    action_type: str | None = None
    action_payload_json: dict | None = None
    risk_level: str | None = None


class AssistantRuleResponse(BaseModel):
    """Full rule response."""

    id: int
    tenant_id: str
    user_id: int
    name: str
    enabled: bool
    scope: str
    priority: int
    match_criteria_json: dict | None
    action_type: str
    action_payload_json: dict | None
    risk_level: str
    origin: str
    confidence: float | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------


class AssistantActionResponse(BaseModel):
    """Proposed or executed action."""

    id: int
    item_id: int
    action_type: str
    status: str
    risk_level: str
    requires_confirmation: bool
    executed_at: datetime | None
    error_message: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------


class AssistantFeedbackCreate(BaseModel):
    """User feedback on an item."""

    feedback_type: str = Field(..., max_length=50)
    feedback_payload_json: dict | None = None


class AssistantFeedbackResponse(BaseModel):
    """Feedback response."""

    id: int
    item_id: int | None
    feedback_type: str
    feedback_payload_json: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------


class AssistantDecisionResponse(BaseModel):
    """Classification decision."""

    id: int
    item_id: int
    decision_type: str
    decision_value: str | None
    confidence: float | None
    reason: str | None
    source: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Briefing
# ---------------------------------------------------------------------------


class BriefingRunRequest(BaseModel):
    """Trigger a briefing run."""

    max_items: int | None = Field(default=None, ge=1, le=200)
    include_calendar: bool = True
    include_email: bool = True


class BriefingRunResponse(BaseModel):
    """Result of a briefing run."""

    items_processed: int
    briefing_text: str
    audio_url: str | None = None
    generated_at: datetime
