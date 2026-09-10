"""Intel module models — Watch-Targets, Sources, Snapshots, Change-Events, Briefings.

All tables are multi-tenant via ``tenant_id`` (FK to ``tenants.tenant_id``).
Embeddings use pgvector ``Vector(1024)`` matching ``BAAI/bge-m3`` from
the local TEI service. NEVER reuse qdrant or external vector stores —
see ``__manifest__.py`` for the isolation rationale.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class IntelWatchTarget(TimestampMixin, Base):
    """A competitor, regulator or market segment under observation."""

    __tablename__ = "intel_watch_target"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # competitor | regulator | segment
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    # Free-form context: industry, region, tags, notes for the LLM
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    sources: Mapped[list[IntelSource]] = relationship(
        "IntelSource", back_populates="target", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_intel_watch_target_tenant", "tenant_id"),
        Index("ix_intel_watch_target_active", "tenant_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<IntelWatchTarget {self.name!r} ({self.kind})>"


class IntelSource(TimestampMixin, Base):
    """A concrete URL/endpoint feeding into a WatchTarget."""

    __tablename__ = "intel_source"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    target_id: Mapped[int] = mapped_column(
        ForeignKey("intel_watch_target.id", ondelete="CASCADE"), nullable=False
    )
    # web | web_js | rss | jobs_board | structured_api
    adapter: Mapped[str] = mapped_column(String(40), nullable=False)
    # Adapter-specific config (e.g. {"url": "...", "render_js": false})
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    fetch_interval_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # pending | ok | failed
    last_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    target: Mapped[IntelWatchTarget] = relationship(
        "IntelWatchTarget", back_populates="sources"
    )
    snapshots: Mapped[list[IntelSnapshot]] = relationship(
        "IntelSnapshot", back_populates="source", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_intel_source_tenant", "tenant_id"),
        Index("ix_intel_source_target", "target_id"),
        Index("ix_intel_source_due", "is_active", "last_fetched_at"),
    )

    def __repr__(self) -> str:
        return f"<IntelSource id={self.id} adapter={self.adapter}>"


class IntelSnapshot(Base):
    """A single fetch result for an IntelSource.

    Holds normalized text, parsed structure, and an embedding vector for
    semantic-distance diffing. ``embedding`` is NULL when TEI was
    unreachable — the diff pipeline falls back to content_hash + text
    diff in that case.
    """

    __tablename__ = "intel_snapshot"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("intel_source.id", ondelete="CASCADE"), nullable=False
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # 1024d matches BAAI/bge-m3 from local TEI; NULL if TEI unreachable
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    byte_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    source: Mapped[IntelSource] = relationship(
        "IntelSource", back_populates="snapshots"
    )

    __table_args__ = (
        Index("ix_intel_snapshot_tenant", "tenant_id"),
        Index("ix_intel_snapshot_source_fetched", "source_id", "fetched_at"),
        Index("ix_intel_snapshot_content_hash", "source_id", "content_hash"),
        # HNSW vector-index created in migration 089 via raw SQL.
    )

    def __repr__(self) -> str:
        return f"<IntelSnapshot id={self.id} source={self.source_id}>"


class IntelChangeEvent(Base):
    """A detected change between two snapshots for the same source."""

    __tablename__ = "intel_change_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("intel_source.id", ondelete="CASCADE"), nullable=False
    )
    prev_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("intel_snapshot.id", ondelete="SET NULL"), nullable=True
    )
    new_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("intel_snapshot.id", ondelete="CASCADE"), nullable=False
    )
    # Free-form classifier output:
    # price_change | product_launch | hiring_signal | regulation_update | …
    change_type: Mapped[str] = mapped_column(String(50), nullable=False, default="unclassified")
    significance: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, default=Decimal("0.50")
    )
    raw_diff: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    headline: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    # [{ "url": "...", "fetched_at": "..." }, ...]
    evidence: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    # Optional handoff to engagement; populated in v2
    engagement_action_id: Mapped[int | None] = mapped_column(
        ForeignKey("pending_actions.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        Index("ix_intel_change_event_tenant", "tenant_id"),
        Index("ix_intel_change_event_source", "source_id"),
        Index("ix_intel_change_event_significance", "tenant_id", "significance"),
    )

    def __repr__(self) -> str:
        return (
            f"<IntelChangeEvent id={self.id} type={self.change_type} "
            f"sig={self.significance}>"
        )


class IntelBriefing(Base):
    """A composed briefing aggregating ChangeEvents over a period.

    Payload follows ``IntelBriefingPayload`` (see ``schemas.py``).
    The briefing module consumes these read-only.
    """

    __tablename__ = "intel_briefing"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    briefing_uuid: Mapped[_uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True, default=_uuid.uuid4
    )
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    tts_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_intel_briefing_tenant", "tenant_id"),
        Index("ix_intel_briefing_period", "tenant_id", "period_end"),
    )

    def __repr__(self) -> str:
        return f"<IntelBriefing id={self.id} period={self.period_start}..{self.period_end}>"
