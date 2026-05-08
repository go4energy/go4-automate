"""Conversation model for chat system."""

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Conversation(TimestampMixin, Base):
    """Chat conversation."""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    context_type: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="general"
    )
    context_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    topic: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="active"
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="conversations", lazy="selectin")
    messages = relationship(
        "ChatMessage",
        back_populates="conversation",
        lazy="selectin",
        order_by="ChatMessage.created_at",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_conversations_tenant_status", "tenant_id", "status"),
        Index("ix_conversations_tenant_topic", "tenant_id", "topic"),
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.id} ({self.context_type})>"
