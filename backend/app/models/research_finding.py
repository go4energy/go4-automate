"""ResearchFinding model."""

from datetime import datetime

from sqlalchemy import Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class ResearchFinding(TimestampMixin, Base):
    """A single finding discovered by research source scanning."""

    __tablename__ = "research_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("research_sources.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    content_snippet: Mapped[str | None] = mapped_column(Text)
    found_at: Mapped[datetime] = mapped_column(nullable=False)
    topics_extracted: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="research_findings")
    source = relationship("ResearchSource", back_populates="findings")
    topic_suggestions = relationship(
        "TopicSuggestion", back_populates="finding", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "url", name="uq_research_findings_tenant_url"),
        Index("ix_research_findings_tenant_status", "tenant_id", "status"),
        Index("ix_research_findings_tenant_source", "tenant_id", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<ResearchFinding {self.title!r} ({self.status})>"
