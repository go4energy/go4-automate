"""Contacts models - Contact, Company."""

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Company(TimestampMixin, Base):
    """Company entity for grouping contacts."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Basic Info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(200), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Details
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    annual_revenue: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Address (JSONB for flexibility)
    address: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Contact Info
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)

    # Metadata
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    custom_fields: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="companies")
    owner = relationship("User", back_populates="owned_companies")
    contacts = relationship("Contact", back_populates="company")
    deals = relationship("CrmDeal", back_populates="company")
    activities = relationship("CrmActivity", back_populates="company")
    tasks = relationship("CrmTask", back_populates="company")

    __table_args__ = (
        Index("ix_companies_tenant_name", "tenant_id", "name"),
        Index("ix_companies_tenant_domain", "tenant_id", "domain"),
    )

    def __repr__(self) -> str:
        return f"<Company {self.name!r}>"


class Contact(TimestampMixin, Base):
    """Contact entity - individual person."""

    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Basic Info
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(50), nullable=True)
    position: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Avatar
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Metadata
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    custom_fields: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Social
    linkedin: Mapped[str | None] = mapped_column(String(200), nullable=True)
    twitter: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Customer Journey
    tracking_hash: Mapped[str | None] = mapped_column(String(12), nullable=True)
    journey_status: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default=None
    )
    odoo_id: Mapped[int | None] = mapped_column(nullable=True)

    # Module-extension FK: when this contact came from a leadgen handoff,
    # this points back to the originating leadgen_place. The brain reads
    # the place's LLM insights / impressum / scoring through this link
    # instead of duplicating that data on the contact itself.
    leadgen_place_id: Mapped[int | None] = mapped_column(
        ForeignKey("leadgen_places.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="contacts")
    company = relationship("Company", back_populates="contacts")
    owner = relationship("User", back_populates="owned_contacts")
    deals = relationship("CrmDeal", back_populates="contact")
    activities = relationship("CrmActivity", back_populates="contact")
    tasks = relationship("CrmTask", back_populates="contact")
    # Engagement relationships
    pipeline_enrollments = relationship("PipelineEnrollment", back_populates="contact")
    pending_actions = relationship("PendingAction", back_populates="contact")
    engagement_activities = relationship("ContactActivity", back_populates="contact")
    # Customer Journey relationships
    journey_events = relationship("JourneyEvent", back_populates="contact")
    journey_ref_codes = relationship("JourneyRefCode", back_populates="contact")

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_contacts_tenant_email"),
        Index("ix_contacts_tenant_email", "tenant_id", "email"),
        Index("ix_contacts_tenant_name", "tenant_id", "name"),
        Index("ix_contacts_tenant_company", "tenant_id", "company_id"),
        Index(
            "ix_contacts_tracking_hash",
            "tracking_hash",
            unique=True,
            postgresql_where="tracking_hash IS NOT NULL",
        ),
    )

    def __repr__(self) -> str:
        return f"<Contact {self.name!r} ({self.email})>"
