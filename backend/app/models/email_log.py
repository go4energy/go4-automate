"""EmailLog model."""

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class EmailLog(TimestampMixin, Base):
    """Email send log for tracking."""

    __tablename__ = "email_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    lead_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("leads.id"), nullable=False
    )
    email_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column()
    opened_at: Mapped[datetime | None] = mapped_column()
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)

    # Relationships
    tenant = relationship("Tenant", back_populates="email_logs")
    lead = relationship("Lead", back_populates="email_logs")

    def __repr__(self) -> str:
        return f"<EmailLog {self.email_type} → Lead#{self.lead_id}>"
