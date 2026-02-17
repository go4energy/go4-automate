"""ContentCalendar model."""

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class ContentCalendar(TimestampMixin, Base):
    """Editorial calendar for scheduled content publication."""

    __tablename__ = "content_calendar"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    content_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("content_pieces.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(nullable=False)
    time_slot: Mapped[str | None] = mapped_column(String(50))
    is_posted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    posted_platform_id: Mapped[str | None] = mapped_column(String(200))

    # Relationships
    tenant = relationship("Tenant", back_populates="content_calendar")
    content_piece = relationship("ContentPiece", back_populates="calendar_entries")

    __table_args__ = (
        Index("ix_content_calendar_tenant_scheduled", "tenant_id", "scheduled_at"),
    )

    def __repr__(self) -> str:
        return f"<ContentCalendar {self.platform} ({self.scheduled_at})>"
