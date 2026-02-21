"""Distributor module models."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


def _utcnow() -> datetime:
    return datetime.utcnow()


class DistributorCampaign(TimestampMixin, Base):
    """Advertising campaign entity."""

    __tablename__ = "distributor_campaigns"

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
    tenant = relationship("Tenant", back_populates="distributor_campaigns")
    performances = relationship("DistributorPerformance", back_populates="campaign")

    __table_args__ = (
        Index("ix_distributor_campaigns_tenant_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<DistributorCampaign {self.name!r} ({self.status})>"


class DistributorPerformance(TimestampMixin, Base):
    """Advertising campaign performance tracking."""

    __tablename__ = "distributor_performances"

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
    distributor_campaign_id: Mapped[int | None] = mapped_column(
        "ad_campaign_id",
        Integer,
        ForeignKey("distributor_campaigns.id", ondelete="SET NULL"),
    )
    # Extended fields for ad pipeline
    campaign_name: Mapped[str | None] = mapped_column(String(200))
    adset_id: Mapped[str | None] = mapped_column(String(100))
    adset_name: Mapped[str | None] = mapped_column(String(200))
    ad_id: Mapped[str | None] = mapped_column(String(100))
    ad_name: Mapped[str | None] = mapped_column(String(200))
    conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conversion_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=0, nullable=False
    )
    cpc: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    ctr: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    frequency: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    reach: Mapped[int | None] = mapped_column(Integer)
    budget_applied: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    weather_boosted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    optimization_action: Mapped[str | None] = mapped_column(String(50))

    # Relationships
    tenant = relationship("Tenant", back_populates="distributor_performances")
    campaign = relationship("DistributorCampaign", back_populates="performances")

    __table_args__ = (
        Index("ix_distributor_performance_tenant_date", "tenant_id", "date"),
    )

    def __repr__(self) -> str:
        return (
            f"<DistributorPerformance {self.platform} "
            f"{self.campaign_id} ({self.date})>"
        )


class DistributorCampaignConfig(TimestampMixin, Base):
    """Configuration for automated campaign optimization."""

    __tablename__ = "distributor_campaign_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    campaign_id: Mapped[str] = mapped_column(String(100), nullable=False)
    campaign_name: Mapped[str | None] = mapped_column(String(200))
    platform: Mapped[str] = mapped_column(String(30), default="meta", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    target_cpl: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    max_cpl: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    daily_budget_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    daily_budget_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    weather_boost_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    weather_boost_factor: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=Decimal("1.5"), nullable=False
    )
    auto_optimize: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    optimization_rules: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # Relationships
    tenant = relationship("Tenant")

    __table_args__ = (
        Index(
            "ix_distributor_campaign_configs_tenant",
            "tenant_id",
            "campaign_id",
        ),
    )

    def __repr__(self) -> str:
        return f"<DistributorCampaignConfig {self.campaign_id} ({self.status})>"


class DistributorConversion(Base):
    """Server-side conversion events for Meta Conversion API."""

    __tablename__ = "distributor_conversions"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    event_name: Mapped[str] = mapped_column(String(50), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    user_agent: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    fbc: Mapped[str | None] = mapped_column(String(200))
    fbp: Mapped[str | None] = mapped_column(String(200))
    email_hash: Mapped[str | None] = mapped_column(String(64))
    phone_hash: Mapped[str | None] = mapped_column(String(64))
    custom_data: Mapped[dict | None] = mapped_column(JSONB)
    sent_to_meta: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    meta_response: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
        nullable=False,
    )

    # Relationships
    tenant = relationship("Tenant")

    __table_args__ = (
        Index("ix_dist_conv_tenant_event", "tenant_id", "event_name"),
        Index("ix_dist_conv_time", "event_time"),
    )

    def __repr__(self) -> str:
        return f"<DistributorConversion {self.event_name} ({self.event_time})>"
