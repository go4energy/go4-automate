"""Tag model — tenant-scoped tags for universal content routing."""

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Tag(TimestampMixin, Base):
    """A tenant-scoped tag used for routing content between modules."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#6B7280", nullable=False)
    icon: Mapped[str | None] = mapped_column(String(50))

    # Relationships
    tenant = relationship("Tenant")

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_tags_tenant_slug"),
        Index("ix_tags_tenant", "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<Tag {self.slug!r} ({self.label})>"
