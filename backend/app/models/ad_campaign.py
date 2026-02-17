"""AdCampaign model."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class AdCampaign(TimestampMixin, Base):
    """Advertising campaign entity."""

    __tablename__ = "ad_campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    platform_campaign_id: Mapped[str | None] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    objective: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    daily_budget: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    total_budget: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    spend: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ctr: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0, nullable=False)
    cpc: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_per_lead: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=0, nullable=False
    )
    roas: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="ad_campaigns")
    performances = relationship("AdPerformance", back_populates="ad_campaign")

    __table_args__ = (Index("ix_ad_campaigns_tenant_status", "tenant_id", "status"),)

    def __repr__(self) -> str:
        return f"<AdCampaign {self.name!r} ({self.status})>"
