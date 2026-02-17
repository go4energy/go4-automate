"""ContentPiece model."""

from datetime import datetime

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class ContentPiece(TimestampMixin, Base):
    """Content piece for marketing automation."""

    __tablename__ = "content_pieces"

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
    tenant = relationship("Tenant", back_populates="content_pieces")
    calendar_entries = relationship(
        "ContentCalendar", back_populates="content_piece", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_content_pieces_tenant_status", "tenant_id", "status"),
        Index("ix_content_pieces_tenant_platform", "tenant_id", "platform"),
    )

    def __repr__(self) -> str:
        return f"<ContentPiece {self.title!r} ({self.status})>"
