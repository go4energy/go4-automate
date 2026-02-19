"""TopicSuggestion model."""

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class TopicSuggestion(TimestampMixin, Base):
    """A suggested content topic from research or manual input."""

    __tablename__ = "topic_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    finding_id: Mapped[int | None] = mapped_column(
        ForeignKey("research_findings.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="general", nullable=False)
    platforms: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(20), default="research", nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="suggested", nullable=False)
    content_piece_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_pieces.id"), nullable=True
    )
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="topic_suggestions")
    finding = relationship("ResearchFinding", back_populates="topic_suggestions")
    content_piece = relationship("ContentPiece", lazy="selectin")

    __table_args__ = (
        Index("ix_topic_suggestions_tenant_status", "tenant_id", "status"),
        Index("ix_topic_suggestions_tenant_source_type", "tenant_id", "source_type"),
    )

    def __repr__(self) -> str:
        return f"<TopicSuggestion {self.title!r} ({self.status})>"
