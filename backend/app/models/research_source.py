"""ResearchSource model."""

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class ResearchSource(TimestampMixin, Base):
    """Configurable research source for topic discovery."""

    __tablename__ = "research_sources"

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

    # Relationships
    tenant = relationship("Tenant", back_populates="research_sources")
    findings = relationship(
        "ResearchFinding", back_populates="source", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_research_sources_tenant_active", "tenant_id", "active"),
        Index("ix_research_sources_tenant_type", "tenant_id", "source_type"),
    )

    def __repr__(self) -> str:
        return f"<ResearchSource {self.name!r} ({self.source_type})>"
