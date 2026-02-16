"""ContentQueue model."""

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class ContentQueue(TimestampMixin, Base):
    """Social media / content publication queue."""

    __tablename__ = "content_queue"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    image_prompt: Mapped[str | None] = mapped_column(Text)
    scheduled_at: Mapped[datetime | None] = mapped_column()
    published_at: Mapped[datetime | None] = mapped_column()
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    engagement_data: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # Relationships
    tenant = relationship("Tenant", back_populates="content_queue")

    __table_args__ = (
        Index("ix_content_queue_tenant_scheduled", "tenant_id", "scheduled_at"),
    )

    def __repr__(self) -> str:
        return f"<ContentQueue {self.platform} ({self.status})>"
