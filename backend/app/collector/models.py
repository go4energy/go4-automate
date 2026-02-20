"""Collector models - Source, Finding, Topic, PageSnapshot."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Float,
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


class CollectorSource(TimestampMixin, Base):
    """Configurable source for topic discovery and monitoring."""

    __tablename__ = "collector_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    keywords: Mapped[list | None] = mapped_column(JSONB, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fetch_interval_hours: Mapped[int] = mapped_column(
        Integer, default=24, nullable=False
    )
    last_fetched_at: Mapped[datetime | None] = mapped_column()
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    categories: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    change_detection_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="collector_sources")
    findings = relationship(
        "CollectorFinding", back_populates="source", cascade="all, delete-orphan"
    )
    snapshots = relationship(
        "PageSnapshot", back_populates="source", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_research_sources_tenant_active", "tenant_id", "active"),
        Index("ix_research_sources_tenant_type", "tenant_id", "source_type"),
    )

    def __repr__(self) -> str:
        return f"<CollectorSource {self.name!r} ({self.source_type})>"


class CollectorFinding(TimestampMixin, Base):
    """A single finding discovered by source scanning."""

    __tablename__ = "collector_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("collector_sources.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    content_snippet: Mapped[str | None] = mapped_column(Text)
    found_at: Mapped[datetime] = mapped_column(nullable=False)
    topics_extracted: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False)
    categories: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="collector_findings")
    source = relationship("CollectorSource", back_populates="findings")
    topics = relationship(
        "CollectorTopic", back_populates="finding", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "url", name="uq_research_findings_tenant_url"),
        Index("ix_research_findings_tenant_status", "tenant_id", "status"),
        Index("ix_research_findings_tenant_source", "tenant_id", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<CollectorFinding {self.title!r} ({self.status})>"


class CollectorTopic(TimestampMixin, Base):
    """A suggested content topic from research or manual input."""

    __tablename__ = "collector_topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    finding_id: Mapped[int | None] = mapped_column(
        ForeignKey("collector_findings.id"), nullable=True
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
    content_piece_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    categories: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    target_modules: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="collector_topics")
    finding = relationship("CollectorFinding", back_populates="topics")

    __table_args__ = (
        Index("ix_topic_suggestions_tenant_status", "tenant_id", "status"),
        Index("ix_topic_suggestions_tenant_source_type", "tenant_id", "source_type"),
    )

    def __repr__(self) -> str:
        return f"<CollectorTopic {self.title!r} ({self.status})>"


class PageSnapshot(TimestampMixin, Base):
    """Snapshot of a web page for change detection."""

    __tablename__ = "collector_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("collector_sources.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_at: Mapped[datetime] = mapped_column(nullable=False)
    diff_from_previous: Mapped[str | None] = mapped_column(Text)
    change_summary: Mapped[str | None] = mapped_column(Text)
    change_significance: Mapped[str | None] = mapped_column(String(20))

    # Relationships
    source = relationship("CollectorSource", back_populates="snapshots")

    def __repr__(self) -> str:
        return f"<PageSnapshot source={self.source_id} ({self.snapshot_at})>"
