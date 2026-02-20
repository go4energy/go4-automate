"""Creator models - Piece, Calendar."""

from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class CreatorPiece(TimestampMixin, Base):
    """Content piece for marketing automation."""

    __tablename__ = "creator_pieces"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    topic: Mapped[str | None] = mapped_column(String(200))
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    caption: Mapped[str | None] = mapped_column(Text)
    short: Mapped[str | None] = mapped_column(Text)
    hashtags: Mapped[str | None] = mapped_column(Text)
    hook: Mapped[str | None] = mapped_column(Text)
    cta: Mapped[str | None] = mapped_column(String(300))
    media_urls: Mapped[list | None] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column()
    posted_at: Mapped[datetime | None] = mapped_column()
    funnel_stage: Mapped[str | None] = mapped_column(String(50))
    buyer_persona: Mapped[str | None] = mapped_column(String(100))
    reach: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    engagement: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    link_clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    leads_generated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(100))
    ai_model: Mapped[str | None] = mapped_column(String(100))
    meta_post_id: Mapped[str | None] = mapped_column(String(100))
    approved_by: Mapped[str | None] = mapped_column(String(100))
    approved_at: Mapped[datetime | None] = mapped_column()
    error_message: Mapped[str | None] = mapped_column(Text)

    # Relationships
    tenant = relationship("Tenant", back_populates="creator_pieces")
    calendar_entries = relationship(
        "CreatorCalendar", back_populates="content_piece", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_content_pieces_tenant_status", "tenant_id", "status"),
        Index("ix_content_pieces_tenant_platform", "tenant_id", "platform"),
    )

    def __repr__(self) -> str:
        return f"<CreatorPiece {self.title!r} ({self.status})>"


class CreatorCalendar(TimestampMixin, Base):
    """Editorial calendar for scheduled content publication."""

    __tablename__ = "creator_calendar"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    content_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("creator_pieces.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(nullable=False)
    time_slot: Mapped[str | None] = mapped_column(String(50))
    is_posted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    posted_platform_id: Mapped[str | None] = mapped_column(String(200))

    # Relationships
    tenant = relationship("Tenant", back_populates="creator_calendar")
    content_piece = relationship("CreatorPiece", back_populates="calendar_entries")

    __table_args__ = (
        Index("ix_content_calendar_tenant_scheduled", "tenant_id", "scheduled_at"),
    )

    def __repr__(self) -> str:
        return f"<CreatorCalendar {self.platform} ({self.scheduled_at})>"
