"""CRM models - Contact, EmailLog."""

from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class CrmContact(TimestampMixin, Base):
    """Marketing contact (ex Lead)."""

    __tablename__ = "crm_contacts"

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
    tenant = relationship("Tenant", back_populates="crm_contacts")
    email_logs = relationship("CrmEmailLog", back_populates="contact", lazy="selectin")

    __table_args__ = (Index("ix_leads_tenant_status", "tenant_id", "status"),)

    def __repr__(self) -> str:
        return f"<CrmContact {self.email} ({self.tenant_id})>"


class CrmEmailLog(TimestampMixin, Base):
    """Email send log for tracking."""

    __tablename__ = "crm_email_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    lead_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("crm_contacts.id"), nullable=False
    )
    email_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column()
    opened_at: Mapped[datetime | None] = mapped_column()
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)

    # Relationships
    tenant = relationship("Tenant", back_populates="crm_email_logs")
    contact = relationship("CrmContact", back_populates="email_logs")

    def __repr__(self) -> str:
        return f"<CrmEmailLog {self.email_type} -> Contact#{self.lead_id}>"
