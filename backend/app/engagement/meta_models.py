"""
Meta Integration Models

SQLAlchemy models for Meta (Facebook) Conversions API integration.
Supports server-side event tracking and (future) Custom Audience sync.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.contacts.models import Contact
    from app.engagement.models import EngagementPipeline, PipelineEnrollment


class MetaIntegration(Base):
    """
    Meta Business Account integration per tenant.

    Stores credentials and configuration for Meta Conversions API.
    Each tenant can have ONE active Meta integration.

    Attributes:
        pixel_id: Meta Pixel ID (from Events Manager)
        access_token: System User access token (encrypted in DB)
        ad_account_id: Optional Ad Account ID for Custom Audiences
        is_active: Whether the integration is enabled
        test_mode: If True, events are sent with test_event_code
    """

    __tablename__ = "meta_integrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Meta Account Details
    pixel_id: Mapped[str] = mapped_column(String(50), nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    ad_account_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Configuration
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    test_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Statistics
    last_event_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_events_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_events_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    events: Mapped[list["ConversionEvent"]] = relationship(
        "ConversionEvent", back_populates="integration", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<MetaIntegration tenant={self.tenant_id} pixel={self.pixel_id}>"

    @property
    def success_rate(self) -> float:
        """Calculate event success rate as percentage."""
        total = self.total_events_sent + self.total_events_failed
        if total == 0:
            return 100.0
        return (self.total_events_sent / total) * 100


class ConversionEvent(Base):
    """
    Log of conversion events sent to Meta Conversions API.

    Each event tracks a specific user action (PageView, Lead, Purchase, etc.)
    and stores the API response for debugging and auditing.

    Event Names (Meta Standard Events):
        - PageView: User visited a tracked page
        - Lead: User enrolled in a pipeline
        - Contact: User responded to outreach
        - Purchase: User converted (deal won)
        - ViewContent: User viewed specific content
        - CompleteRegistration: User completed signup

    Attributes:
        event_name: Standard Meta event name
        event_id: Unique ID for deduplication (contact_id + event + timestamp)
        status: pending, sent, failed, test
    """

    __tablename__ = "conversion_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    meta_integration_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meta_integrations.id", ondelete="CASCADE"), nullable=False
    )

    # Event Details
    event_name: Mapped[str] = mapped_column(String(50), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    # Contact Reference
    contact_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )

    # Pipeline/Enrollment Reference
    pipeline_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("engagement_pipelines.id", ondelete="SET NULL"), nullable=True
    )
    enrollment_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("pipeline_enrollments.id", ondelete="SET NULL"), nullable=True
    )

    # Payload Info (PII is hashed before sending, we only log which fields)
    user_data_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    custom_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Response
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    integration: Mapped["MetaIntegration"] = relationship(
        "MetaIntegration", back_populates="events"
    )
    contact: Mapped["Contact | None"] = relationship("Contact", lazy="selectin")
    pipeline: Mapped["EngagementPipeline | None"] = relationship("EngagementPipeline", lazy="selectin")
    enrollment: Mapped["PipelineEnrollment | None"] = relationship(
        "PipelineEnrollment", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<ConversionEvent {self.event_name} contact={self.contact_id} status={self.status}>"


# Event name constants for type safety
class MetaEventName:
    """Standard Meta Conversion Events."""

    PAGE_VIEW = "PageView"
    LEAD = "Lead"
    CONTACT = "Contact"
    PURCHASE = "Purchase"
    VIEW_CONTENT = "ViewContent"
    COMPLETE_REGISTRATION = "CompleteRegistration"
    ADD_TO_CART = "AddToCart"
    INITIATE_CHECKOUT = "InitiateCheckout"
    SCHEDULE = "Schedule"
    SUBMIT_APPLICATION = "SubmitApplication"

    @classmethod
    def all(cls) -> list[str]:
        """Return all standard event names."""
        return [
            cls.PAGE_VIEW,
            cls.LEAD,
            cls.CONTACT,
            cls.PURCHASE,
            cls.VIEW_CONTENT,
            cls.COMPLETE_REGISTRATION,
            cls.ADD_TO_CART,
            cls.INITIATE_CHECKOUT,
            cls.SCHEDULE,
            cls.SUBMIT_APPLICATION,
        ]
