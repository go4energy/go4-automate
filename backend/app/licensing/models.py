"""TenantModuleLicense ORM model."""

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class TenantModuleLicense(TimestampMixin, Base):
    """One row per (tenant, module) that is licensed/active.

    The presence of a row means: this tenant has access to this module.
    The middleware (``app.licensing.middleware``) treats absence as
    "permissive" only when the tenant has *zero* license rows at all
    (= legacy / un-licensed tenant). As soon as the tenant has at least
    one row, the licensing model is the source of truth and missing
    modules are denied.
    """

    __tablename__ = "tenant_module_licenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    module_key: Mapped[str] = mapped_column(String(50), nullable=False)

    enabled_at: Mapped[datetime] = mapped_column(nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # "trial" | "starter" | "growth" | "scale" | None (Managed Service)
    plan_tier: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Free-form per-license extras (limits, custom config)
    license_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    tenant = relationship("Tenant")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "module_key", name="uq_tenant_module_license"
        ),
        Index("ix_tenant_module_licenses_tenant", "tenant_id"),
    )

    def is_active(self, now: datetime | None = None) -> bool:
        """A license is active when expires_at is null or in the future."""
        if self.expires_at is None:
            return True
        check = now or datetime.utcnow()
        return self.expires_at > check
