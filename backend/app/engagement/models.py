"""Engagement models - Pipeline, Enrollment, PendingAction, ContactActivity, ABTest, TrackingLink."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class EngagementPipeline(TimestampMixin, Base):
    """Engagement pipeline for orchestrating multi-channel outreach."""

    __tablename__ = "engagement_pipelines"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False
    )

    # Basic Info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)

    # Product Info
    product_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    product_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Configuration
    channels: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    goal: Mapped[str | None] = mapped_column(String(100), nullable=True)
    playbook: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone_of_voice: Mapped[str] = mapped_column(String(50), default="professionell")
    min_days_between_touches: Mapped[int] = mapped_column(default=3)
    auto_actions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="engagement_pipelines")
    enrollments = relationship(
        "PipelineEnrollment", back_populates="pipeline", cascade="all, delete-orphan"
    )
    pending_actions = relationship(
        "PendingAction", back_populates="pipeline", cascade="all, delete-orphan"
    )
    activities = relationship("ContactActivity", back_populates="pipeline")

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_engagement_pipelines_tenant_slug"),
        Index("ix_engagement_pipelines_tenant", "tenant_id"),
        Index("ix_engagement_pipelines_active", "tenant_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<EngagementPipeline {self.name!r}>"


class PipelineEnrollment(TimestampMixin, Base):
    """Enrollment of a contact in an engagement pipeline."""

    __tablename__ = "pipeline_enrollments"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False
    )

    # Foreign Keys
    contact_id: Mapped[int] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    pipeline_id: Mapped[int] = mapped_column(
        ForeignKey("engagement_pipelines.id", ondelete="CASCADE"), nullable=False
    )

    # Source Information
    source_module: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_campaign: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Stage & Status
    # Stages: lead, contacted, engaged, qualified, converted, lost
    stage: Mapped[str] = mapped_column(String(50), default="lead")
    # Status: active, paused, completed, stopped
    status: Mapped[str] = mapped_column(String(50), default="active")

    # Engagement Tracking
    touch_count: Mapped[int] = mapped_column(default=0)
    last_touch_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_response_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Outcome
    outcome: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Timestamps
    enrolled_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    tenant = relationship("Tenant")
    contact = relationship("Contact", back_populates="pipeline_enrollments")
    pipeline = relationship("EngagementPipeline", back_populates="enrollments")
    pending_actions = relationship(
        "PendingAction", back_populates="enrollment", cascade="all, delete-orphan"
    )
    activities = relationship("ContactActivity", back_populates="enrollment")

    __table_args__ = (
        UniqueConstraint("contact_id", "pipeline_id", name="uq_enrollments_contact_pipeline"),
        Index("ix_enrollments_tenant", "tenant_id"),
        Index("ix_enrollments_contact", "contact_id"),
        Index("ix_enrollments_pipeline", "pipeline_id"),
        Index("ix_enrollments_status", "tenant_id", "status"),
        Index("ix_enrollments_stage", "tenant_id", "pipeline_id", "stage"),
    )

    def __repr__(self) -> str:
        return f"<PipelineEnrollment contact={self.contact_id} pipeline={self.pipeline_id}>"


class PendingAction(Base):
    """Action delegated by the brain to a module for execution."""

    __tablename__ = "pending_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False
    )

    # Foreign Keys
    contact_id: Mapped[int] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    pipeline_id: Mapped[int] = mapped_column(
        ForeignKey("engagement_pipelines.id", ondelete="CASCADE"), nullable=False
    )
    enrollment_id: Mapped[int] = mapped_column(
        ForeignKey("pipeline_enrollments.id", ondelete="CASCADE"), nullable=False
    )

    # Action Definition
    module: Mapped[str] = mapped_column(String(100), nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    context: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    suggested_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Priority & Scheduling
    # Priority: urgent, high, normal, low
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    due_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Approval
    needs_approval: Mapped[bool] = mapped_column(default=True)
    # Status: pending, ready_for_approval, approved, completed, failed, cancelled
    status: Mapped[str] = mapped_column(String(50), default="pending")
    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Result
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # A/B Testing
    ab_test_variant_id: Mapped[int | None] = mapped_column(
        ForeignKey("ab_test_variants.id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    tenant = relationship("Tenant")
    contact = relationship("Contact", back_populates="pending_actions")
    pipeline = relationship("EngagementPipeline", back_populates="pending_actions")
    enrollment = relationship("PipelineEnrollment", back_populates="pending_actions")
    approver = relationship("User")
    activities = relationship("ContactActivity", back_populates="source_action")
    ab_test_variant = relationship("ABTestVariant")

    __table_args__ = (
        Index("ix_pending_actions_tenant", "tenant_id"),
        Index("ix_pending_actions_contact", "contact_id"),
        Index("ix_pending_actions_enrollment", "enrollment_id"),
        Index("ix_pending_actions_module", "tenant_id", "module"),
        Index("ix_pending_actions_status", "tenant_id", "status"),
        Index("ix_pending_actions_due", "tenant_id", "status", "due_at"),
        Index("ix_pending_actions_ab_variant", "ab_test_variant_id"),
    )

    def __repr__(self) -> str:
        return f"<PendingAction {self.module}:{self.action_type} status={self.status}>"


class ContactActivity(Base):
    """Activity record for contact engagement timeline."""

    __tablename__ = "contact_activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False
    )

    # Foreign Keys
    contact_id: Mapped[int] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    pipeline_id: Mapped[int | None] = mapped_column(
        ForeignKey("engagement_pipelines.id", ondelete="SET NULL"), nullable=True
    )
    enrollment_id: Mapped[int | None] = mapped_column(
        ForeignKey("pipeline_enrollments.id", ondelete="SET NULL"), nullable=True
    )

    # Activity Info
    # Channel: linkedin, email, phone, postmail, whatsapp, meeting, sms, other
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    # Activity Type: message_sent, message_received, call_made, call_received,
    #                email_sent, email_received, email_opened, email_clicked,
    #                meeting_scheduled, meeting_completed, letter_sent, etc.
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # Direction: outbound, inbound
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Source
    source_module: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_action_id: Mapped[int | None] = mapped_column(
        ForeignKey("pending_actions.id", ondelete="SET NULL"), nullable=True
    )
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # AI Analysis
    # Sentiment: positive, neutral, negative
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Intent: interested, question, objection, not_interested, referral, etc.
    detected_intent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Status: sent, delivered, opened, clicked, replied, bounced, failed, etc.
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Metadata
    metadata_: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Actor
    performed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    performed_at: Mapped[datetime] = mapped_column(nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant")
    contact = relationship("Contact", back_populates="engagement_activities")
    pipeline = relationship("EngagementPipeline", back_populates="activities")
    enrollment = relationship("PipelineEnrollment", back_populates="activities")
    source_action = relationship("PendingAction", back_populates="activities")
    performer = relationship("User")

    __table_args__ = (
        Index("ix_contact_activities_tenant", "tenant_id"),
        Index("ix_contact_activities_contact", "contact_id"),
        Index("ix_contact_activities_enrollment", "enrollment_id"),
        Index("ix_contact_activities_channel", "tenant_id", "channel"),
        Index("ix_contact_activities_performed", "contact_id", "performed_at"),
        Index("ix_contact_activities_external", "tenant_id", "external_id"),
    )

    def __repr__(self) -> str:
        return f"<ContactActivity {self.channel}:{self.activity_type}>"


class ABTest(TimestampMixin, Base):
    """A/B Test for engagement pipelines."""

    __tablename__ = "ab_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False
    )
    pipeline_id: Mapped[int] = mapped_column(
        ForeignKey("engagement_pipelines.id", ondelete="CASCADE"), nullable=False
    )

    # Test configuration
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_type: Mapped[str] = mapped_column(String(50), nullable=False)  # message, subject, timing, channel
    channel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    action_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status: draft, running, paused, completed
    status: Mapped[str] = mapped_column(String(50), default="draft")
    is_active: Mapped[bool] = mapped_column(default=False)

    # Targeting
    sample_size: Mapped[int | None] = mapped_column(nullable=True)
    traffic_split: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Results
    winner_variant_id: Mapped[int | None] = mapped_column(nullable=True)
    results_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    tenant = relationship("Tenant")
    pipeline = relationship("EngagementPipeline")
    variants = relationship("ABTestVariant", back_populates="ab_test", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_ab_tests_tenant", "tenant_id"),
        Index("ix_ab_tests_pipeline", "pipeline_id"),
        Index("ix_ab_tests_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<ABTest {self.name!r} status={self.status}>"


class ABTestVariant(TimestampMixin, Base):
    """Variant in an A/B Test."""

    __tablename__ = "ab_test_variants"

    id: Mapped[int] = mapped_column(primary_key=True)
    ab_test_id: Mapped[int] = mapped_column(
        ForeignKey("ab_tests.id", ondelete="CASCADE"), nullable=False
    )

    # Variant configuration
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # A, B, Control, etc.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    weight: Mapped[int] = mapped_column(default=50)  # Traffic weight percentage

    # Statistics
    impressions: Mapped[int] = mapped_column(default=0)
    clicks: Mapped[int] = mapped_column(default=0)
    conversions: Mapped[int] = mapped_column(default=0)
    responses: Mapped[int] = mapped_column(default=0)

    # Is this the control variant?
    is_control: Mapped[bool] = mapped_column(default=False)

    # Relationships
    ab_test = relationship("ABTest", back_populates="variants")

    __table_args__ = (
        Index("ix_ab_test_variants_test", "ab_test_id"),
    )

    def __repr__(self) -> str:
        return f"<ABTestVariant {self.name!r}>"


class TrackingLink(TimestampMixin, Base):
    """Tracking link for cross-channel attribution."""

    __tablename__ = "tracking_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[int] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    pipeline_id: Mapped[int | None] = mapped_column(
        ForeignKey("engagement_pipelines.id", ondelete="SET NULL"), nullable=True
    )
    enrollment_id: Mapped[int | None] = mapped_column(
        ForeignKey("pipeline_enrollments.id", ondelete="SET NULL"), nullable=True
    )

    # Link configuration
    token: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    target_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    short_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # UTM parameters
    utm_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(100), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(200), nullable=True)
    utm_content: Mapped[str | None] = mapped_column(String(200), nullable=True)
    utm_term: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Statistics
    click_count: Mapped[int] = mapped_column(default=0)
    first_click_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_click_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Lifecycle
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    tenant = relationship("Tenant")
    contact = relationship("Contact")
    pipeline = relationship("EngagementPipeline")
    enrollment = relationship("PipelineEnrollment")
    events = relationship("TrackingEvent", back_populates="tracking_link", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_tracking_links_tenant", "tenant_id"),
        Index("ix_tracking_links_contact", "contact_id"),
        Index("ix_tracking_links_token", "token", unique=True),
        Index("ix_tracking_links_short_code", "short_code"),
        Index("ix_tracking_links_pipeline", "pipeline_id"),
    )

    def __repr__(self) -> str:
        return f"<TrackingLink {self.token}>"


class TrackingEvent(Base):
    """Website tracking event from pixel."""

    __tablename__ = "tracking_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False
    )
    tracking_link_id: Mapped[int | None] = mapped_column(
        ForeignKey("tracking_links.id", ondelete="SET NULL"), nullable=True
    )
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )

    # Event data
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # UTM data
    utm_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(100), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(200), nullable=True)
    utm_content: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Client info
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Additional data
    metadata_: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Timestamps
    event_time: Mapped[datetime] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant")
    tracking_link = relationship("TrackingLink", back_populates="events")
    contact = relationship("Contact")

    __table_args__ = (
        Index("ix_tracking_events_tenant", "tenant_id"),
        Index("ix_tracking_events_link", "tracking_link_id"),
        Index("ix_tracking_events_contact", "contact_id"),
        Index("ix_tracking_events_time", "tenant_id", "event_time"),
    )

    def __repr__(self) -> str:
        return f"<TrackingEvent {self.event_type}>"


class AttributionRecord(Base):
    """Attribution record for conversion tracking."""

    __tablename__ = "attribution_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[int] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    pipeline_id: Mapped[int | None] = mapped_column(
        ForeignKey("engagement_pipelines.id", ondelete="SET NULL"), nullable=True
    )
    enrollment_id: Mapped[int | None] = mapped_column(
        ForeignKey("pipeline_enrollments.id", ondelete="SET NULL"), nullable=True
    )

    # Attribution data
    conversion_type: Mapped[str] = mapped_column(String(100), nullable=False)
    conversion_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    # First touch attribution
    first_touch_channel: Mapped[str | None] = mapped_column(String(100), nullable=True)
    first_touch_source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    first_touch_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Last touch attribution
    last_touch_channel: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_touch_source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_touch_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Full journey
    touchpoints: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    touchpoint_count: Mapped[int] = mapped_column(default=0)

    # Timestamps
    converted_at: Mapped[datetime] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant")
    contact = relationship("Contact")
    pipeline = relationship("EngagementPipeline")
    enrollment = relationship("PipelineEnrollment")

    __table_args__ = (
        Index("ix_attribution_records_tenant", "tenant_id"),
        Index("ix_attribution_records_contact", "contact_id"),
        Index("ix_attribution_records_pipeline", "pipeline_id"),
        Index("ix_attribution_records_converted", "tenant_id", "converted_at"),
    )

    def __repr__(self) -> str:
        return f"<AttributionRecord {self.conversion_type}>"
