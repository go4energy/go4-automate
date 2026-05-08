"""Email Marketing models - 9 tables for campaigns, sequences, and tracking."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
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


class EmailProvider(TimestampMixin, Base):
    """Email provider configuration (SendGrid, Mailgun, O365)."""

    __tablename__ = "email_providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )

    # Provider type
    provider_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # sendgrid, mailgun, o365, aws_ses

    # Credentials (encrypted)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Sender settings
    sender_email: Mapped[str] = mapped_column(String(320), nullable=False)
    sender_name: Mapped[str] = mapped_column(String(200), nullable=False)
    reply_to_email: Mapped[str | None] = mapped_column(String(320), nullable=True)

    # Domain settings
    tracking_domain: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )  # e.g., mail.kunde.de

    # Rate limits
    hourly_limit: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    daily_limit: Mapped[int] = mapped_column(Integer, default=10000, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # active, inactive, error
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Usage tracking
    emails_sent_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    emails_sent_hour: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_reset_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    campaigns: Mapped[list["EmailCampaign"]] = relationship(
        "EmailCampaign", back_populates="provider"
    )

    __table_args__ = (
        Index("ix_email_providers_tenant_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<EmailProvider {self.provider_type} ({self.sender_email})>"


class EmailTemplate(TimestampMixin, Base):
    """Reusable email template with merge tags."""

    __tablename__ = "email_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )

    # Basics
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Content
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Visual editor design state (react-email-editor JSON). Null for
    # templates authored as raw HTML. html_content stays canonical for send.
    design_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Which editor flavour to load for this template.
    # 'unlayer' (default) — Drag-&-Drop visual; design_json source of truth
    # 'plain' — plain text only; text_content source of truth
    # 'html' — raw HTML editor + optional KI-chat; html_content source of truth
    editor_mode: Mapped[str] = mapped_column(
        String(20), default="unlayer", nullable=False, server_default="unlayer"
    )

    # Merge tags available in this template
    variables: Mapped[list] = mapped_column(
        JSONB, default=list, nullable=False
    )  # ["name", "company", "unsubscribe_url"]

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Categories/Tags
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    campaigns: Mapped[list["EmailCampaign"]] = relationship(
        "EmailCampaign", back_populates="template"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_email_templates_tenant_slug"),
        Index("ix_email_templates_tenant", "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<EmailTemplate {self.name!r}>"


class EmailCampaign(TimestampMixin, Base):
    """Email campaign - broadcast to contacts."""

    __tablename__ = "email_campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    provider_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_providers.id", ondelete="SET NULL"), nullable=True
    )
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True
    )
    pipeline_id: Mapped[int | None] = mapped_column(
        ForeignKey("engagement_pipelines.id", ondelete="SET NULL"), nullable=True
    )

    # Basics
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)

    # Content
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Recipient selection
    segment_filters: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # {"tags": ["lead"], "source": "website"}
    contact_ids: Mapped[list | None] = mapped_column(
        JSONB, nullable=True
    )  # Explicit contact IDs

    # Scheduling
    status: Mapped[str] = mapped_column(
        String(30), default="draft", nullable=False
    )  # draft, scheduled, sending, sent, paused, cancelled
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Error tracking
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # A/B Testing
    ab_test_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ab_variant_b_subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ab_variant_b_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    ab_split_percentage: Mapped[int] = mapped_column(
        Integer, default=50, nullable=False
    )  # % for variant A
    ab_winner_metric: Mapped[str] = mapped_column(
        String(20), default="open_rate", nullable=False
    )  # open_rate, click_rate
    ab_winner_variant: Mapped[str | None] = mapped_column(
        String(1), nullable=True
    )  # "A" or "B"

    # Stats (overall)
    total_recipients: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    opened_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicked_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bounced_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unsubscribed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    spam_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # A/B Stats - Variant A
    ab_a_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ab_a_opened: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ab_a_clicked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # A/B Stats - Variant B
    ab_b_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ab_b_opened: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ab_b_clicked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    provider: Mapped["EmailProvider"] = relationship(
        "EmailProvider", back_populates="campaigns"
    )
    template: Mapped["EmailTemplate"] = relationship(
        "EmailTemplate", back_populates="campaigns"
    )
    recipients: Mapped[list["EmailRecipient"]] = relationship(
        "EmailRecipient", back_populates="campaign", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_email_campaigns_tenant_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<EmailCampaign {self.name!r} ({self.status})>"


class EmailRecipient(TimestampMixin, Base):
    """Individual recipient of a campaign email."""

    __tablename__ = "email_recipients"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_campaigns.id", ondelete="CASCADE"), nullable=True
    )
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    # For engagement-driven 1-to-1 outreach (no campaign): link back to the
    # Brain-generated action so we can re-render the mail and trace the
    # touch in the contact's activity timeline.
    pending_action_id: Mapped[int | None] = mapped_column(
        ForeignKey("pending_actions.id", ondelete="SET NULL"), nullable=True
    )

    # Recipient info (copied at send time)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Personalization data
    merge_data: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False
    )  # {"name": "Max", "company": "Acme"}

    # Tracking token (UUID)
    tracking_token: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True
    )  # UUID for open/click tracking

    # Status
    status: Mapped[str] = mapped_column(
        String(30), default="pending", nullable=False
    )  # pending, sent, delivered, opened, clicked, bounced, unsubscribed, spam

    # A/B Testing variant
    ab_variant: Mapped[str | None] = mapped_column(
        String(1), nullable=True
    )  # "A" or "B"

    # Timestamps
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    bounced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Provider reference (returned by provider API after submission)
    provider_message_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # RFC822 Message-ID header we set on outbound — used to match replies
    # via In-Reply-To / References headers on the inbound side.
    message_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Audit trail of what we actually sent (the canonical record).
    subject_rendered: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Brain-generated pieces (e.g. {"llm_subject": "...", "llm_body": "..."})
    # so we can re-render the body later without re-calling the LLM.
    personalized_inputs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    campaign: Mapped["EmailCampaign"] = relationship(
        "EmailCampaign", back_populates="recipients"
    )
    contact: Mapped["Contact"] = relationship("Contact")
    clicks: Mapped[list["EmailClick"]] = relationship(
        "EmailClick", back_populates="recipient", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_email_recipients_campaign_status", "campaign_id", "status"),
        Index("ix_email_recipients_token", "tracking_token"),
        Index("ix_email_recipients_message_id", "message_id"),
    )

    def __repr__(self) -> str:
        return f"<EmailRecipient {self.email} ({self.status})>"


class EmailClick(TimestampMixin, Base):
    """Click tracking for email links."""

    __tablename__ = "email_clicks"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    recipient_id: Mapped[int] = mapped_column(
        ForeignKey("email_recipients.id", ondelete="CASCADE"), nullable=False
    )

    # Click info
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    clicked_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Meta
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    recipient: Mapped["EmailRecipient"] = relationship(
        "EmailRecipient", back_populates="clicks"
    )

    __table_args__ = (Index("ix_email_clicks_recipient", "recipient_id"),)

    def __repr__(self) -> str:
        return f"<EmailClick {self.original_url[:50]}>"


class EmailSequence(TimestampMixin, Base):
    """Multi-step email automation sequence."""

    __tablename__ = "email_sequences"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    provider_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_providers.id", ondelete="SET NULL"), nullable=True
    )
    pipeline_id: Mapped[int | None] = mapped_column(
        ForeignKey("engagement_pipelines.id", ondelete="SET NULL"), nullable=True
    )

    # Basics
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Trigger
    trigger_type: Mapped[str] = mapped_column(
        String(30), default="manual", nullable=False
    )  # manual, tag_added, contact_created

    # Filter for auto-enrollment
    trigger_filters: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # {"tags": ["new_lead"]}

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False
    )  # draft, active, paused

    # Send window settings
    send_window_start: Mapped[str | None] = mapped_column(
        String(5), nullable=True
    )  # "09:00"
    send_window_end: Mapped[str | None] = mapped_column(
        String(5), nullable=True
    )  # "18:00"
    skip_weekends: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(50), default="Europe/Berlin", nullable=False
    )

    # Stats
    total_enrolled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_unsubscribed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    provider: Mapped["EmailProvider"] = relationship("EmailProvider")
    steps: Mapped[list["EmailSequenceStep"]] = relationship(
        "EmailSequenceStep",
        back_populates="sequence",
        cascade="all, delete-orphan",
        order_by="EmailSequenceStep.position",
    )
    enrollments: Mapped[list["EmailSequenceEnrollment"]] = relationship(
        "EmailSequenceEnrollment",
        back_populates="sequence",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("ix_email_sequences_tenant_status", "tenant_id", "status"),)

    def __repr__(self) -> str:
        return f"<EmailSequence {self.name!r} ({self.status})>"


class EmailSequenceStep(TimestampMixin, Base):
    """Individual step in an email sequence."""

    __tablename__ = "email_sequence_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    sequence_id: Mapped[int] = mapped_column(
        ForeignKey("email_sequences.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True
    )

    # Position
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    # Delay
    delay_days: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )  # Days after previous step
    delay_hours: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # Additional hours

    # Content (can override template)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Conditional sending
    send_if_opened_previous: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )  # None = always, True = only if opened, False = only if not opened
    send_if_clicked_previous: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Stats
    sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    opened_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicked_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    sequence: Mapped["EmailSequence"] = relationship(
        "EmailSequence", back_populates="steps"
    )
    template: Mapped["EmailTemplate"] = relationship("EmailTemplate")

    __table_args__ = (
        Index("ix_email_sequence_steps_sequence_position", "sequence_id", "position"),
    )

    def __repr__(self) -> str:
        return f"<EmailSequenceStep {self.sequence_id}:{self.position}>"


class EmailSequenceEnrollment(TimestampMixin, Base):
    """Contact enrollment in a sequence."""

    __tablename__ = "email_sequence_enrollments"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    sequence_id: Mapped[int] = mapped_column(
        ForeignKey("email_sequences.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[int] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )

    # Progress
    current_step: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # 0 = not started
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # active, paused, completed, unsubscribed

    # Scheduling
    next_send_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Tracking
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Stop-on-reply (and other auto-stops): worker skips further steps
    # when stopped_on_reply_at is set. Reason: reply, unsubscribe, bounce, manual.
    stopped_on_reply_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    stopped_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Source of enrollment
    source: Mapped[str] = mapped_column(
        String(50), default="manual", nullable=False
    )  # manual, trigger, import

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    sequence: Mapped["EmailSequence"] = relationship(
        "EmailSequence", back_populates="enrollments"
    )
    contact: Mapped["Contact"] = relationship("Contact")

    __table_args__ = (
        UniqueConstraint(
            "sequence_id", "contact_id", name="uq_email_enrollments_sequence_contact"
        ),
        Index("ix_email_enrollments_status_next", "status", "next_send_at"),
    )

    def __repr__(self) -> str:
        return f"<EmailSequenceEnrollment seq={self.sequence_id} contact={self.contact_id}>"


class EmailUnsubscribe(TimestampMixin, Base):
    """Email unsubscribe list (per tenant)."""

    __tablename__ = "email_unsubscribes"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )

    # Unsubscribed email
    email: Mapped[str] = mapped_column(String(320), nullable=False)

    # Reason
    reason: Mapped[str] = mapped_column(
        String(30), default="user_request", nullable=False
    )  # user_request, bounce, complaint, manual

    # Source (which campaign/sequence caused this)
    source_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # campaign, sequence
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Additional info
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_email_unsubscribes_tenant_email"),
        Index("ix_email_unsubscribes_tenant_email", "tenant_id", "email"),
    )

    def __repr__(self) -> str:
        return f"<EmailUnsubscribe {self.email}>"


class EmailAsset(TimestampMixin, Base):
    """User-uploaded image / file referenced by email templates."""

    __tablename__ = "email_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )

    # Server-generated filename (UUID-prefixed) inside the tenant folder
    filename: Mapped[str] = mapped_column(String(200), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    # Public URL path (served by FastAPI StaticFiles)
    url_path: Mapped[str] = mapped_column(String(500), nullable=False)

    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")

    __table_args__ = (Index("ix_email_assets_tenant", "tenant_id"),)

    def __repr__(self) -> str:
        return f"<EmailAsset {self.original_filename!r}>"


class EmailTemplateChat(TimestampMixin, Base):
    """Persisted Claude chat per email template — KI-Designer-Assistant."""

    __tablename__ = "email_template_chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    template_id: Mapped[int] = mapped_column(
        ForeignKey("email_templates.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user|assistant|tool
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Claude tool_use blocks (when role=assistant); or tool_result block (when role=tool)
    tool_calls: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tool_use_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    template: Mapped["EmailTemplate"] = relationship("EmailTemplate")

    __table_args__ = (
        Index("ix_email_template_chats_template", "template_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<EmailTemplateChat tpl={self.template_id} role={self.role}>"

