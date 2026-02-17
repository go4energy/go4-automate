"""Ad management models."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


class AdCampaignConfig(TimestampMixin, Base):
    """Configuration for automated campaign optimization."""

    __tablename__ = "ad_campaign_configs"

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
        Index("ix_ad_campaign_configs_tenant", "tenant_id", "campaign_id"),
    )

    def __repr__(self) -> str:
        return f"<AdCampaignConfig {self.campaign_id} ({self.status})>"


class ConversionEvent(Base):
    """Server-side conversion events for Meta Conversion API."""

    __tablename__ = "conversion_events"

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
        Index("ix_conv_tenant_event", "tenant_id", "event_name"),
        Index("ix_conv_time", "event_time"),
    )

    def __repr__(self) -> str:
        return f"<ConversionEvent {self.event_name} ({self.event_time})>"
