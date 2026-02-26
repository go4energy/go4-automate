"""Funnels models - Funnel, Stage, Company, Prospect, Activity, Handoff."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Funnel(TimestampMixin, Base):
    """Prospecting funnel/campaign container."""

    __tablename__ = "funnel_funnels"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # active, paused, archived
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    target_criteria: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Handoff configuration
    handoff_pipeline_id: Mapped[int | None] = mapped_column(
        ForeignKey("crm_pipelines.id", ondelete="SET NULL"), nullable=True
    )
    handoff_stage_id: Mapped[int | None] = mapped_column(
        ForeignKey("crm_pipeline_stages.id", ondelete="SET NULL"), nullable=True
    )
    external_crm_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="funnels")
    owner = relationship("User", back_populates="owned_funnels")
    stages = relationship(
        "FunnelStage",
        back_populates="funnel",
        order_by="FunnelStage.position",
        cascade="all, delete-orphan",
    )
    companies = relationship(
        "FunnelCompany", back_populates="funnel", cascade="all, delete-orphan"
    )
    prospects = relationship(
        "FunnelProspect", back_populates="funnel", cascade="all, delete-orphan"
    )
    handoffs = relationship(
        "FunnelHandoff", back_populates="funnel", cascade="all, delete-orphan"
    )
    handoff_pipeline = relationship("CrmPipeline", foreign_keys=[handoff_pipeline_id])
    handoff_stage = relationship("CrmPipelineStage", foreign_keys=[handoff_stage_id])

    __table_args__ = (
        Index("ix_funnel_funnels_tenant", "tenant_id"),
        Index("ix_funnel_funnels_tenant_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Funnel {self.name!r} ({self.status})>"


class FunnelStage(TimestampMixin, Base):
    """A stage within a funnel."""

    __tablename__ = "funnel_stages"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    funnel_id: Mapped[int] = mapped_column(
        ForeignKey("funnel_funnels.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#6B7280", nullable=False)
    is_handoff: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_disqualified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_actions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="funnel_stages")
    funnel = relationship("Funnel", back_populates="stages")
    prospects = relationship("FunnelProspect", back_populates="stage")

    __table_args__ = (
        Index("ix_funnel_stages_funnel_position", "funnel_id", "position"),
    )

    def __repr__(self) -> str:
        return f"<FunnelStage {self.name!r} @ position {self.position}>"


class FunnelCompany(TimestampMixin, Base):
    """Company in a funnel (separate from CRM companies)."""

    __tablename__ = "funnel_companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    funnel_id: Mapped[int] = mapped_column(
        ForeignKey("funnel_funnels.id", ondelete="CASCADE"), nullable=False
    )

    # Basic Info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(200), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Address & Contact
    address: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)

    # Source & Verification
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Dedup
    dedup_key: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # CRM Link (after handoff)
    crm_company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )

    # Metadata
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    custom_fields: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    enrichment_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="funnel_companies")
    funnel = relationship("Funnel", back_populates="companies")
    prospects = relationship("FunnelProspect", back_populates="company")
    crm_company = relationship("Company")
    handoffs = relationship("FunnelHandoff", back_populates="company")

    __table_args__ = (
        Index("ix_funnel_companies_tenant_funnel", "tenant_id", "funnel_id"),
        Index("ix_funnel_companies_dedup_key", "tenant_id", "dedup_key"),
    )

    def __repr__(self) -> str:
        return f"<FunnelCompany {self.name!r}>"


class FunnelProspect(TimestampMixin, Base):
    """Prospect in a funnel (separate from CRM contacts)."""

    __tablename__ = "funnel_prospects"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    funnel_id: Mapped[int] = mapped_column(
        ForeignKey("funnel_funnels.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("funnel_companies.id", ondelete="SET NULL"), nullable=True
    )
    stage_id: Mapped[int | None] = mapped_column(
        ForeignKey("funnel_stages.id", ondelete="SET NULL"), nullable=True
    )
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Person
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(50), nullable=True)
    position: Mapped[str | None] = mapped_column(String(150), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    seniority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    twitter_url: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Dedup Keys (normalized)
    dedup_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    dedup_linkedin: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dedup_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Verification
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Score & Status
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score_factors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default="new", nullable=False
    )  # new, contacted, engaged, qualified, handed_off, do_not_contact

    # Duplicate handling
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    master_prospect_id: Mapped[int | None] = mapped_column(
        ForeignKey("funnel_prospects.id", ondelete="SET NULL"), nullable=True
    )
    duplicate_of_crm_contact: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )

    # CRM Links (after handoff)
    crm_contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    crm_deal_id: Mapped[int | None] = mapped_column(
        ForeignKey("crm_deals.id", ondelete="SET NULL"), nullable=True
    )

    # Metadata
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    custom_fields: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    enrichment_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="funnel_prospects")
    funnel = relationship("Funnel", back_populates="prospects")
    company = relationship("FunnelCompany", back_populates="prospects")
    stage = relationship("FunnelStage", back_populates="prospects")
    owner = relationship("User", back_populates="funnel_prospects")
    activities = relationship(
        "FunnelActivity", back_populates="prospect", cascade="all, delete-orphan"
    )
    handoffs = relationship(
        "FunnelHandoff", back_populates="prospect", cascade="all, delete-orphan"
    )
    master_prospect = relationship("FunnelProspect", remote_side=[id])
    crm_contact = relationship("Contact", foreign_keys=[crm_contact_id])
    duplicate_crm_contact = relationship("Contact", foreign_keys=[duplicate_of_crm_contact])
    crm_deal = relationship("CrmDeal")

    __table_args__ = (
        Index("ix_funnel_prospects_tenant_funnel", "tenant_id", "funnel_id"),
        Index("ix_funnel_prospects_funnel_stage", "funnel_id", "stage_id"),
        Index("ix_funnel_prospects_dedup_email", "tenant_id", "dedup_email"),
        Index("ix_funnel_prospects_dedup_linkedin", "tenant_id", "dedup_linkedin"),
        Index("ix_funnel_prospects_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<FunnelProspect {self.name!r} ({self.email})>"


class FunnelActivity(TimestampMixin, Base):
    """Activity log for prospects."""

    __tablename__ = "funnel_activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    prospect_id: Mapped[int] = mapped_column(
        ForeignKey("funnel_prospects.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Activity details
    activity_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # email_sent, email_opened, email_clicked, email_replied, email_bounced,
    # linkedin_connection_sent, linkedin_accepted, linkedin_message_sent, linkedin_replied,
    # letter_sent, letter_delivered, call_made, call_answered, voicemail_left,
    # stage_changed, enrichment_completed, handoff_initiated, handoff_completed
    subject: Mapped[str | None] = mapped_column(String(300), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # External reference
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="completed", nullable=False
    )  # pending, completed, failed
    activity_date: Mapped[datetime] = mapped_column(nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="funnel_activities")
    prospect = relationship("FunnelProspect", back_populates="activities")
    user = relationship("User", back_populates="funnel_activities_created")

    __table_args__ = (
        Index("ix_funnel_activities_prospect", "prospect_id", "activity_date"),
        Index("ix_funnel_activities_tenant_type", "tenant_id", "activity_type"),
    )

    def __repr__(self) -> str:
        return f"<FunnelActivity {self.activity_type!r}>"


class FunnelHandoff(TimestampMixin, Base):
    """Handoff queue for CRM transfer."""

    __tablename__ = "funnel_handoffs"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    funnel_id: Mapped[int] = mapped_column(
        ForeignKey("funnel_funnels.id", ondelete="CASCADE"), nullable=False
    )
    prospect_id: Mapped[int] = mapped_column(
        ForeignKey("funnel_prospects.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("funnel_companies.id", ondelete="SET NULL"), nullable=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending, processing, completed, failed, skipped

    # Internal CRM references
    crm_contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    crm_company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    crm_deal_id: Mapped[int | None] = mapped_column(
        ForeignKey("crm_deals.id", ondelete="SET NULL"), nullable=True
    )

    # External CRM references
    external_crm_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # hubspot, salesforce, pipedrive
    external_crm_contact_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_crm_deal_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Trigger info
    triggered_by: Mapped[str] = mapped_column(
        String(20), default="manual", nullable=False
    )  # auto, manual, n8n
    triggered_at: Mapped[datetime] = mapped_column(nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Snapshot
    prospect_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="funnel_handoffs")
    funnel = relationship("Funnel", back_populates="handoffs")
    prospect = relationship("FunnelProspect", back_populates="handoffs")
    company = relationship("FunnelCompany", back_populates="handoffs")
    crm_contact = relationship("Contact")
    crm_company = relationship("Company")
    crm_deal = relationship("CrmDeal")

    __table_args__ = (
        Index("ix_funnel_handoffs_tenant_status", "tenant_id", "status"),
        Index("ix_funnel_handoffs_prospect", "prospect_id"),
    )

    def __repr__(self) -> str:
        return f"<FunnelHandoff {self.id} ({self.status})>"
