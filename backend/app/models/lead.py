"""Lead model."""

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Lead(TimestampMixin, Base):
    """Marketing lead."""

    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    source: Mapped[str | None] = mapped_column(String(100))
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="new", nullable=False, index=True
    )
    konfigurator_data: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    followup_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    followup_paused: Mapped[bool] = mapped_column(default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    tenant = relationship("Tenant", back_populates="leads")
    email_logs = relationship("EmailLog", back_populates="lead", lazy="selectin")

    __table_args__ = (Index("ix_leads_tenant_status", "tenant_id", "status"),)

    def __repr__(self) -> str:
        return f"<Lead {self.email} ({self.tenant_id})>"
