"""Customer Journey models - JourneyEvent, JourneyRefCode, JourneyCampaign."""

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class JourneyEvent(TimestampMixin, Base):
    """Tracking event in a lead's customer journey."""

    __tablename__ = "journey_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), nullable=True
    )

    # Event
    event: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Context
    page_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_site: Mapped[str] = mapped_column(
        String(100), nullable=False, default="go4.energy"
    )

    # Attribution
    utm_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(100), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(100), nullable=True)
    utm_term: Mapped[str | None] = mapped_column(String(100), nullable=True)
    utm_content: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ref_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Extra data
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    # Relationships
    contact = relationship("Contact", back_populates="journey_events")

    __table_args__ = (
        Index("ix_journey_events_contact", "tenant_id", "contact_id"),
        Index("ix_journey_events_time", "created_at"),
        Index("ix_journey_events_event", "event"),
    )

    def __repr__(self) -> str:
        return f"<JourneyEvent {self.event!r} contact={self.contact_id}>"


class JourneyRefCode(TimestampMixin, Base):
    """Referral code for campaign tracking links."""

    __tablename__ = "journey_ref_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("journey_campaigns.id", ondelete="SET NULL"), nullable=True
    )

    # Code
    ref_code: Mapped[str] = mapped_column(String(20), nullable=False)

    # Context
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    context: Mapped[str | None] = mapped_column(String(200), nullable=True)
    target_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # UTM parameters (for link building)
    utm_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(100), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Notifications
    notify_on_visit: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    notify_channel: Mapped[str] = mapped_column(
        String(20), default="none", nullable=False
    )
    notify_target: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Stats (denormalized for performance)
    visit_count: Mapped[int] = mapped_column(default=0, nullable=False)

    # Relationships
    contact = relationship("Contact", back_populates="journey_ref_codes")
    campaign = relationship("JourneyCampaign", back_populates="ref_codes")

    __table_args__ = (
        UniqueConstraint("tenant_id", "ref_code", name="uq_journey_ref_code"),
        Index("ix_journey_refs_tenant", "tenant_id"),
        Index("ix_journey_refs_contact", "tenant_id", "contact_id"),
    )

    def __repr__(self) -> str:
        return f"<JourneyRefCode {self.ref_code!r}>"


class JourneyCampaign(TimestampMixin, Base):
    """Campaign for grouping ref-codes and attribution."""

    __tablename__ = "journey_campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    channel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    ref_codes = relationship("JourneyRefCode", back_populates="campaign")

    __table_args__ = (
        Index("ix_journey_campaigns_tenant", "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<JourneyCampaign {self.name!r}>"
