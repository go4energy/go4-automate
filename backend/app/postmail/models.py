"""Post-Mail Module Models.

SQLAlchemy models for letter templates, letters, and batches.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# ============== Constants ==============


class LetterFormat:
    """Letter format options."""

    A4 = "a4"
    US_LETTER = "us_letter"
    DIN_LANG = "din_lang"


class LetterStatus:
    """Letter status options."""

    DRAFT = "draft"
    APPROVED = "approved"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    RETURNED = "returned"


class BatchStatus:
    """Batch status options."""

    COLLECTING = "collecting"
    READY = "ready"
    EXPORTED = "exported"
    SENT = "sent"


# ============== Models ==============


class PostmailTemplate(Base):
    """Brief-Templates mit Platzhaltern."""

    __tablename__ = "postmail_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Template
    format: Mapped[str] = mapped_column(
        String(20), nullable=False, default=LetterFormat.A4
    )
    content_html: Mapped[str] = mapped_column(Text, nullable=False)
    header_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    footer_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Preview
    preview_image: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Lifecycle
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    letters: Mapped[list["PostmailLetter"]] = relationship(
        "PostmailLetter", back_populates="template"
    )

    def __repr__(self) -> str:
        return f"<PostmailTemplate {self.id}: {self.name}>"


class PostmailBatch(Base):
    """Batch für Sammelversand."""

    __tablename__ = "postmail_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    letter_count: Mapped[int] = mapped_column(Integer, default=0)

    # Export
    export_format: Mapped[str | None] = mapped_column(String(20), nullable=True)
    export_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=BatchStatus.COLLECTING, index=True
    )
    exported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    letters: Mapped[list["PostmailLetter"]] = relationship(
        "PostmailLetter", back_populates="batch"
    )

    def __repr__(self) -> str:
        return f"<PostmailBatch {self.id}: {self.name}>"


class PostmailLetter(Base):
    """Einzelner Brief zum Versand."""

    __tablename__ = "postmail_letters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # References
    template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("postmail_templates.id"), nullable=False
    )
    contact_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("contacts.id"), nullable=True, index=True
    )
    pipeline_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("engagement_pipelines.id", ondelete="SET NULL"), nullable=True
    )
    pending_action_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    batch_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("postmail_batches.id"), nullable=True, index=True
    )

    # Recipient
    recipient_name: Mapped[str] = mapped_column(String(200), nullable=False)
    recipient_company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    recipient_street: Mapped[str | None] = mapped_column(String(200), nullable=True)
    recipient_zip: Mapped[str | None] = mapped_column(String(20), nullable=True)
    recipient_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recipient_country: Mapped[str] = mapped_column(
        String(10), nullable=False, default="DE"
    )

    # Content
    content_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=LetterStatus.DRAFT, index=True
    )
    queued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    returned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    return_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    template: Mapped["PostmailTemplate"] = relationship(
        "PostmailTemplate", back_populates="letters"
    )
    batch: Mapped["PostmailBatch | None"] = relationship(
        "PostmailBatch", back_populates="letters"
    )

    def __repr__(self) -> str:
        return f"<PostmailLetter {self.id}: {self.recipient_name}>"
