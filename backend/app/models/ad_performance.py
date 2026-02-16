"""AdPerformance model."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class AdPerformance(TimestampMixin, Base):
    """Advertising campaign performance tracking."""

    __tablename__ = "ad_performances"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(200), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    spend: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    leads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cpl: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)

    # Relationships
    tenant = relationship("Tenant", back_populates="ad_performances")

    __table_args__ = (Index("ix_ad_performance_tenant_date", "tenant_id", "date"),)

    def __repr__(self) -> str:
        return f"<AdPerformance {self.platform} {self.campaign_id} ({self.date})>"
