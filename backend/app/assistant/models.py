"""Assistant module database models."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin

# ---------------------------------------------------------------------------
# A. Platform integration tables
# ---------------------------------------------------------------------------


class IntegrationConnection(TimestampMixin, Base):
    """General-purpose OAuth/API connection (provider-agnostic)."""

    __tablename__ = "integration_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    integration_type: Mapped[str] = mapped_column(String(50), nullable=False)
    auth_mode: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="delegated"
    )
    external_account_id: Mapped[str | None] = mapped_column(String(255))
    mailbox_address: Mapped[str | None] = mapped_column(String(255))
    connected_email: Mapped[str | None] = mapped_column(String(255))
    account_label: Mapped[str | None] = mapped_column(String(200))
    encrypted_token: Mapped[str | None] = mapped_column(Text)
    scopes: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="pending"
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_error: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "user_id",
            "provider",
            "integration_type",
            "mailbox_address",
            name="uq_integration_conn_tenant_user_provider_type_mailbox",
        ),
        Index("ix_integration_conn_tenant", "tenant_id"),
        Index("ix_integration_conn_user", "tenant_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<IntegrationConnection {self.provider}/{self.integration_type} [{self.status}]>"


class IntegrationConnectionCapability(Base):
    """Granted capability for an integration connection."""

    __tablename__ = "integration_connection_capabilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    connection_id: Mapped[int] = mapped_column(
        ForeignKey("integration_connections.id", ondelete="CASCADE"), nullable=False
    )
    capability: Mapped[str] = mapped_column(String(50), nullable=False)
    granted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )

    __table_args__ = (
        UniqueConstraint("connection_id", "capability", name="uq_conn_capability"),
        Index("ix_conn_cap_connection", "connection_id"),
    )

    def __repr__(self) -> str:
        return f"<Capability {self.capability} granted={self.granted}>"


# ---------------------------------------------------------------------------
# B. Assistant-specific tables
# ---------------------------------------------------------------------------


class AssistantProfile(TimestampMixin, Base):
    """Per-user assistant configuration."""

    __tablename__ = "assistant_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    briefing_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )
    voice_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )
    autopilot_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )
    timezone: Mapped[str] = mapped_column(
        String(50), server_default="Europe/Vienna", nullable=False
    )
    delivery_time: Mapped[str | None] = mapped_column(String(10))
    llm_provider: Mapped[str] = mapped_column(
        String(50), server_default="ollama", nullable=False
    )
    llm_model: Mapped[str | None] = mapped_column(String(100))
    tts_provider: Mapped[str] = mapped_column(
        String(50), server_default="piper", nullable=False
    )
    tts_voice: Mapped[str | None] = mapped_column(String(100))
    stt_provider: Mapped[str] = mapped_column(
        String(50), server_default="faster-whisper", nullable=False
    )
    max_items_per_run: Mapped[int] = mapped_column(
        Integer, server_default="30", nullable=False
    )
    default_reply_mode: Mapped[str] = mapped_column(
        String(20), server_default="draft", nullable=False
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_assistant_profile_user"),
        Index("ix_assistant_profile_tenant", "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<AssistantProfile user={self.user_id} active={self.active}>"


class AssistantSource(TimestampMixin, Base):
    """Links an integration connection to the assistant for a user."""

    __tablename__ = "assistant_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    connection_id: Mapped[int] = mapped_column(
        ForeignKey("integration_connections.id", ondelete="CASCADE"), nullable=False
    )
    briefing_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )
    voice_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )
    reply_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )
    autopilot_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    settings_json: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "user_id",
            "connection_id",
            name="uq_assistant_source_user_conn",
        ),
        Index("ix_assistant_source_tenant_user", "tenant_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<AssistantSource conn={self.connection_id} user={self.user_id}>"


class AssistantEvent(TimestampMixin, Base):
    """Raw normalised event for idempotent intake."""

    __tablename__ = "assistant_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    connection_id: Mapped[int] = mapped_column(
        ForeignKey("integration_connections.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(500), nullable=False)
    thread_id: Mapped[str | None] = mapped_column(String(500))
    raw_payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(JSONB)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "connection_id",
            "external_id",
            "raw_payload_hash",
            name="uq_assistant_event_dedup",
        ),
        Index("ix_assistant_event_tenant_user", "tenant_id", "user_id"),
        Index("ix_assistant_event_unprocessed", "processed_at"),
    )

    def __repr__(self) -> str:
        return f"<AssistantEvent {self.event_type} ext={self.external_id}>"


class AssistantItem(TimestampMixin, Base):
    """Normalised mail/calendar item for classification and briefing."""

    __tablename__ = "assistant_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    connection_id: Mapped[int] = mapped_column(
        ForeignKey("integration_connections.id", ondelete="CASCADE"), nullable=False
    )
    item_type: Mapped[str] = mapped_column(String(30), nullable=False)
    external_id: Mapped[str] = mapped_column(String(500), nullable=False)
    thread_id: Mapped[str | None] = mapped_column(String(500))
    mailbox_address: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)
    content_snippet: Mapped[str | None] = mapped_column(Text)
    sender: Mapped[str | None] = mapped_column(String(255))
    recipients_json: Mapped[dict | None] = mapped_column(JSONB)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime)
    raw_metadata_json: Mapped[dict | None] = mapped_column(JSONB)
    raw_payload_hash: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        String(30), server_default="new", nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "connection_id",
            "external_id",
            name="uq_assistant_item_ext",
        ),
        Index("ix_assistant_item_tenant_user", "tenant_id", "user_id"),
        Index("ix_assistant_item_status", "status"),
        Index("ix_assistant_item_occurred", "occurred_at"),
    )

    def __repr__(self) -> str:
        return f"<AssistantItem {self.item_type} '{self.title}'>"


class AssistantDecision(TimestampMixin, Base):
    """Classification / relevance decision for an item."""

    __tablename__ = "assistant_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("assistant_items.id", ondelete="CASCADE"), nullable=False
    )
    decision_type: Mapped[str] = mapped_column(String(50), nullable=False)
    decision_value: Mapped[str | None] = mapped_column(String(100))
    confidence: Mapped[float | None] = mapped_column(Float)
    reason: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(
        String(20), server_default="rule", nullable=False
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        Index("ix_assistant_decision_item", "item_id"),
        Index("ix_assistant_decision_tenant", "tenant_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<AssistantDecision {self.decision_type}={self.decision_value}>"


class AssistantRule(TimestampMixin, Base):
    """Explicit or learned rule for mail triage."""

    __tablename__ = "assistant_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )
    scope: Mapped[str] = mapped_column(
        String(30), server_default="user", nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    match_criteria_json: Mapped[dict | None] = mapped_column(JSONB)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    action_payload_json: Mapped[dict | None] = mapped_column(JSONB)
    risk_level: Mapped[str] = mapped_column(
        String(10), server_default="low", nullable=False
    )
    origin: Mapped[str] = mapped_column(
        String(20), server_default="manual", nullable=False
    )
    confidence: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (
        Index("ix_assistant_rule_tenant_user", "tenant_id", "user_id"),
        Index("ix_assistant_rule_enabled", "enabled"),
    )

    def __repr__(self) -> str:
        return f"<AssistantRule '{self.name}' [{self.risk_level}]>"


class AssistantAction(TimestampMixin, Base):
    """Proposed or executed action on an item."""

    __tablename__ = "assistant_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("assistant_items.id", ondelete="CASCADE"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), server_default="suggested", nullable=False
    )
    risk_level: Mapped[str] = mapped_column(
        String(10), server_default="low", nullable=False
    )
    requires_confirmation: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )
    executed_at: Mapped[datetime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        Index("ix_assistant_action_item", "item_id"),
        Index("ix_assistant_action_status", "status"),
        Index("ix_assistant_action_tenant", "tenant_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<AssistantAction {self.action_type} [{self.status}]>"


class AssistantFeedback(Base):
    """User feedback for learning engine."""

    __tablename__ = "assistant_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[int | None] = mapped_column(
        ForeignKey("assistant_items.id", ondelete="SET NULL"), nullable=True
    )
    feedback_type: Mapped[str] = mapped_column(String(50), nullable=False)
    feedback_payload_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default="now()", nullable=False
    )

    __table_args__ = (
        Index("ix_assistant_feedback_tenant", "tenant_id", "user_id"),
        Index("ix_assistant_feedback_item", "item_id"),
    )

    def __repr__(self) -> str:
        return f"<AssistantFeedback {self.feedback_type}>"


class AssistantConversation(TimestampMixin, Base):
    """Voice / chat dialogue state."""

    __tablename__ = "assistant_conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(
        String(30), server_default="web_chat", nullable=False
    )
    state: Mapped[str] = mapped_column(
        String(20), server_default="active", nullable=False
    )
    context_json: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (Index("ix_assistant_conv_tenant_user", "tenant_id", "user_id"),)

    def __repr__(self) -> str:
        return f"<AssistantConversation {self.channel} [{self.state}]>"
