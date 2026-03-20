"""Assistant module Pydantic schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


class AssistantProfileCreate(BaseModel):
    """Create / ensure profile for current user."""

    timezone: str = "Europe/Vienna"
    delivery_time: str | None = None
    llm_provider: str = "anthropic"
    llm_model: str | None = None
    tts_provider: str = "piper"
    tts_voice: str | None = None
    stt_provider: str = "faster-whisper"
    max_items_per_run: int = Field(default=30, ge=1, le=200)
    default_reply_mode: str = "draft"
    autopilot_min_confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    autopilot_max_rule_risk: Literal["low", "medium", "high"] = "medium"
    suggestion_min_confidence: float = Field(default=0.70, ge=0.0, le=1.0)


class AssistantProfileUpdate(BaseModel):
    """Partial update for profile."""

    active: bool | None = None
    briefing_enabled: bool | None = None
    voice_enabled: bool | None = None
    autopilot_enabled: bool | None = None
    skip_confirmation: bool | None = None
    ai_suggestions_enabled: bool | None = None
    timezone: str | None = None
    delivery_time: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    tts_provider: str | None = None
    tts_voice: str | None = None
    stt_provider: str | None = None
    max_items_per_run: int | None = Field(default=None, ge=1, le=200)
    default_reply_mode: str | None = None
    autopilot_min_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    autopilot_max_rule_risk: Literal["low", "medium", "high"] | None = None
    suggestion_min_confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class AssistantProfileResponse(BaseModel):
    """Full profile response."""

    id: int
    tenant_id: str
    user_id: int
    active: bool
    briefing_enabled: bool
    voice_enabled: bool
    autopilot_enabled: bool
    skip_confirmation: bool
    ai_suggestions_enabled: bool
    timezone: str
    delivery_time: str | None
    llm_provider: str
    llm_model: str | None
    tts_provider: str
    tts_voice: str | None
    stt_provider: str
    max_items_per_run: int
    default_reply_mode: str
    autopilot_min_confidence: float
    autopilot_max_rule_risk: Literal["low", "medium", "high"]
    suggestion_min_confidence: float
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
    mailbox_address: str | None
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


class AssistantMailboxPolicyFolder(BaseModel):
    """Resolved folder mapping for one status."""

    status: str
    folder_id: str | None = None
    display_name: str | None = None
    configured: bool = False
    system: bool = False


class AssistantMailboxPolicyResponse(BaseModel):
    """Mailbox policy state for one assistant source."""

    source_id: int
    connection_id: int
    mailbox_address: str | None
    provider: str
    setup_complete: bool
    status_folders: dict[str, AssistantMailboxPolicyFolder]
    configured_folder_names: dict[str, str]
    available_folders: list[dict]


class AssistantMailboxPolicySetupRequest(BaseModel):
    """Setup or repair status-folder mapping for a mailbox."""

    create_missing: bool = True
    folder_names: dict[str, str] | None = None


# ---------------------------------------------------------------------------
# Category registry
# ---------------------------------------------------------------------------


class AssistantCategoryCreate(BaseModel):
    """Create a tenant category for assistant email policy."""

    name: str = Field(..., min_length=1, max_length=120)
    category_type: str = "fixed"
    color: str | None = Field(default=None, max_length=30)
    active: bool = True
    metadata_json: dict | None = None


class AssistantCategoryUpdate(BaseModel):
    """Partial update for a tenant category."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    color: str | None = Field(default=None, max_length=30)
    active: bool | None = None
    metadata_json: dict | None = None


class AssistantCategoryResponse(BaseModel):
    """Tenant category configuration."""

    id: int
    tenant_id: str
    user_id: int | None
    name: str
    category_type: str
    color: str | None
    active: bool
    system_default: bool
    metadata_json: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# TEMP tracking
# ---------------------------------------------------------------------------


class AssistantTempTrackingResponse(BaseModel):
    """Tracked TEMP email with expiry metadata."""

    id: int
    tenant_id: str
    user_id: int
    connection_id: int | None
    message_external_id: str
    thread_external_id: str | None
    mailbox_address: str | None
    subject: str | None
    sender: str | None
    expires_at: datetime
    last_reviewed_at: datetime | None
    resolved_at: datetime | None
    resolution_status: str | None
    metadata_json: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Mailbox review / triage
# ---------------------------------------------------------------------------


class AssistantMailboxReviewItemResponse(BaseModel):
    """Mailbox item returned by review or triage endpoints."""

    source_id: int
    connection_id: int
    mailbox_address: str | None
    status: str
    message_id: str
    thread_id: str | None
    subject: str
    sender: str | None
    received_at: datetime | None
    snippet: str | None
    is_unread: bool
    has_attachments: bool = False


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


class AssistantDraftUpdate(BaseModel):
    """Partial update for an assistant draft."""

    subject: str | None = Field(default=None, max_length=500)
    body_text: str | None = None
    to_recipients: list[str] | None = None


class AssistantDraftResponse(BaseModel):
    """Persisted reply or send draft."""

    id: int
    tenant_id: str
    user_id: int
    conversation_id: int | None
    connection_id: int | None
    draft_type: str
    status: str
    target_external_id: str | None
    thread_external_id: str | None
    to_recipients_json: dict | None
    cc_recipients_json: dict | None
    bcc_recipients_json: dict | None
    subject: str | None
    body_text: str | None
    body_html: str | None
    provider_draft_id: str | None
    sent_at: datetime | None
    discarded_at: datetime | None
    metadata_json: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssistantPendingIntentResponse(BaseModel):
    """Pending voice/UI action that awaits confirmation."""

    id: int
    tenant_id: str
    user_id: int
    conversation_id: int | None
    connection_id: int | None
    intent_type: str
    status: str
    target_type: str | None
    target_ref_json: dict | None
    payload_json: dict | None
    confirmation_token: str | None
    expires_at: datetime | None
    confirmed_at: datetime | None
    executed_at: datetime | None
    cancelled_at: datetime | None
    error_message: str | None
    metadata_json: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssistantConversationTurnResponse(BaseModel):
    """Single persisted conversation turn."""

    id: int
    tenant_id: str
    user_id: int
    conversation_id: int
    role: str
    turn_type: str
    content_text: str | None
    tool_name: str | None
    tool_args_json: dict | None
    tool_result_text: str | None
    latency_ms: int | None
    metadata_json: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssistantUndoLogResponse(BaseModel):
    """Undo/audit record for an executed assistant action."""

    id: int
    tenant_id: str
    user_id: int
    conversation_id: int | None
    connection_id: int | None
    draft_id: int | None
    pending_intent_id: int | None
    action_type: str
    status: str
    can_undo: bool
    undone_at: datetime | None
    target_ref_json: dict | None
    before_state_json: dict | None
    after_state_json: dict | None
    metadata_json: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssistantMailboxHealthResponse(BaseModel):
    """Mailbox health snapshot for dashboard and triage."""

    connection_id: int
    mailbox_address: str | None
    account_label: str | None
    provider: str
    unread_count: int
    recent_sample_count: int
    cleanup_candidate_count: int
    cleanup_recommended: bool
    health_score: int
    summary: str


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


# ---------------------------------------------------------------------------
# Voice Chat
# ---------------------------------------------------------------------------


class VoiceChatRequest(BaseModel):
    """Voice chat text input."""

    text: str = Field(..., min_length=1, max_length=2000)
    conversation_id: int | None = None
    tts_enabled: bool = True


class VoiceChatContext(BaseModel):
    """Current conversation context for frontend."""

    current_email: dict | None = None
    email_count: int = 0
    current_index: int = 0
    pending_draft_id: int | None = None
    pending_intent_id: int | None = None
    cleanup_preview_summary: str | None = None


class VoiceChatResponse(BaseModel):
    """Voice chat response with optional audio."""

    text: str
    audio_base64: str | None = None
    conversation_id: int
    context: VoiceChatContext
    transcribed_text: str | None = None


class TranscribeResponse(BaseModel):
    """STT transcription result."""

    text: str
