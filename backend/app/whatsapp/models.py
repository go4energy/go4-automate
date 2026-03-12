"""WhatsApp Business models - 6 tables for accounts, templates, conversations, messages, campaigns."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.contacts.models import Contact
    from app.models.tenant import Tenant


class WhatsAppAccount(TimestampMixin, Base):
    """WhatsApp Business Account configuration."""

    __tablename__ = "whatsapp_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )

    # Account identification
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    phone_number_id: Mapped[str] = mapped_column(String(50), nullable=False)
    waba_id: Mapped[str] = mapped_column(String(50), nullable=False)

    # Credentials (encrypted)
    access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Webhook configuration
    webhook_verify_token: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # active, inactive, error
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Rate limiting
    daily_limit: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    messages_sent_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_reset_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    templates: Mapped[list["WhatsAppTemplate"]] = relationship(
        "WhatsAppTemplate", back_populates="account", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["WhatsAppConversation"]] = relationship(
        "WhatsAppConversation", back_populates="account", cascade="all, delete-orphan"
    )
    campaigns: Mapped[list["WhatsAppCampaign"]] = relationship(
        "WhatsAppCampaign", back_populates="account", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_whatsapp_accounts_tenant_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<WhatsAppAccount {self.name!r} ({self.phone_number})>"


class WhatsAppTemplate(TimestampMixin, Base):
    """Meta-approved WhatsApp message template."""

    __tablename__ = "whatsapp_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("whatsapp_accounts.id", ondelete="CASCADE"), nullable=False
    )

    # Template identification (from Meta)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)  # de, en, etc.
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # UTILITY, MARKETING, AUTHENTICATION
    status: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # APPROVED, PENDING, REJECTED

    # Template structure
    components: Mapped[dict] = mapped_column(
        JSONB, nullable=False
    )  # Header, Body, Footer, Buttons
    variables: Mapped[list] = mapped_column(
        JSONB, default=list, nullable=False
    )  # List of variable names

    # Sync tracking
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    account: Mapped["WhatsAppAccount"] = relationship(
        "WhatsAppAccount", back_populates="templates"
    )
    campaigns: Mapped[list["WhatsAppCampaign"]] = relationship(
        "WhatsAppCampaign", back_populates="template"
    )

    __table_args__ = (
        Index("ix_whatsapp_templates_account_status", "account_id", "status"),
        Index("ix_whatsapp_templates_tenant", "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<WhatsAppTemplate {self.name!r} ({self.language})>"


class WhatsAppConversation(TimestampMixin, Base):
    """WhatsApp conversation thread with a contact."""

    __tablename__ = "whatsapp_conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("whatsapp_accounts.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )

    # Recipient info
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Conversation state
    status: Mapped[str] = mapped_column(
        String(20), default="open", nullable=False
    )  # open, closed
    window_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )  # 24h window
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_message_preview: Mapped[str | None] = mapped_column(String(200), nullable=True)
    unread_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    account: Mapped["WhatsAppAccount"] = relationship(
        "WhatsAppAccount", back_populates="conversations"
    )
    contact: Mapped["Contact"] = relationship("Contact")
    messages: Mapped[list["WhatsAppMessage"]] = relationship(
        "WhatsAppMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="WhatsAppMessage.created_at",
    )

    __table_args__ = (
        UniqueConstraint("account_id", "phone", name="uq_whatsapp_conv_account_phone"),
        Index("ix_whatsapp_conversations_tenant_status", "tenant_id", "status"),
        Index("ix_whatsapp_conversations_last_message", "tenant_id", "last_message_at"),
    )

    def __repr__(self) -> str:
        return f"<WhatsAppConversation {self.phone} ({self.status})>"


class WhatsAppMessage(TimestampMixin, Base):
    """Individual WhatsApp message within a conversation."""

    __tablename__ = "whatsapp_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("whatsapp_conversations.id", ondelete="CASCADE"), nullable=False
    )

    # Message direction and type
    direction: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # inbound, outbound
    message_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # text, image, document, template, interactive

    # Message content
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Template info (if template message)
    template_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    template_variables: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Meta message ID
    wamid: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending, sent, delivered, read, failed
    error_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    conversation: Mapped["WhatsAppConversation"] = relationship(
        "WhatsAppConversation", back_populates="messages"
    )

    __table_args__ = (
        Index("ix_whatsapp_messages_conversation", "conversation_id", "created_at"),
        Index("ix_whatsapp_messages_wamid", "wamid"),
        Index("ix_whatsapp_messages_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<WhatsAppMessage {self.direction} {self.message_type} ({self.status})>"


class WhatsAppCampaign(TimestampMixin, Base):
    """WhatsApp broadcast campaign."""

    __tablename__ = "whatsapp_campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("whatsapp_accounts.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("whatsapp_templates.id", ondelete="SET NULL"), nullable=True
    )
    pipeline_id: Mapped[int | None] = mapped_column(
        ForeignKey("engagement_pipelines.id", ondelete="SET NULL"), nullable=True
    )

    # Campaign info
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Recipient selection
    segment_filters: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # {"tags": ["lead"]}
    contact_ids: Mapped[list | None] = mapped_column(
        JSONB, nullable=True
    )  # Explicit IDs

    # Status
    status: Mapped[str] = mapped_column(
        String(30), default="draft", nullable=False
    )  # draft, scheduled, sending, sent, paused, cancelled
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Stats
    total_recipients: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    read_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    account: Mapped["WhatsAppAccount"] = relationship(
        "WhatsAppAccount", back_populates="campaigns"
    )
    template: Mapped["WhatsAppTemplate"] = relationship(
        "WhatsAppTemplate", back_populates="campaigns"
    )
    recipients: Mapped[list["WhatsAppCampaignRecipient"]] = relationship(
        "WhatsAppCampaignRecipient",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_whatsapp_campaigns_tenant_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<WhatsAppCampaign {self.name!r} ({self.status})>"


class WhatsAppCampaignRecipient(TimestampMixin, Base):
    """Individual recipient of a WhatsApp campaign."""

    __tablename__ = "whatsapp_campaign_recipients"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("whatsapp_campaigns.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )

    # Recipient info
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Template variables for this recipient
    template_variables: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False
    )

    # Meta message ID
    wamid: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending, sent, delivered, read, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    campaign: Mapped["WhatsAppCampaign"] = relationship(
        "WhatsAppCampaign", back_populates="recipients"
    )
    contact: Mapped["Contact"] = relationship("Contact")

    __table_args__ = (
        Index(
            "ix_whatsapp_campaign_recipients_campaign_status", "campaign_id", "status"
        ),
        Index("ix_whatsapp_campaign_recipients_wamid", "wamid"),
    )

    def __repr__(self) -> str:
        return f"<WhatsAppCampaignRecipient {self.phone} ({self.status})>"
