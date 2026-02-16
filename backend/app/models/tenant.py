"""Tenant model."""

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Tenant(TimestampMixin, Base):
    """Multi-tenant configuration."""

    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    tenant_name: Mapped[str] = mapped_column(String(200), nullable=False)
    config: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    leads = relationship("Lead", back_populates="tenant", lazy="selectin")
    content_queue = relationship(
        "ContentQueue", back_populates="tenant", lazy="selectin"
    )
    email_logs = relationship("EmailLog", back_populates="tenant", lazy="selectin")
    ad_performances = relationship(
        "AdPerformance", back_populates="tenant", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Tenant {self.tenant_id}>"
