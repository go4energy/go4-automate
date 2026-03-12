"""CRM models - Contact, EmailLog, Pipeline, Deal, Activity, Task."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
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


class CrmPipeline(TimestampMixin, Base):
    """Sales pipeline with configurable stages."""

    __tablename__ = "crm_pipelines"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="crm_pipelines")
    stages = relationship(
        "CrmPipelineStage",
        back_populates="pipeline",
        order_by="CrmPipelineStage.position",
        cascade="all, delete-orphan",
    )
    deals = relationship("CrmDeal", back_populates="pipeline")

    __table_args__ = (Index("ix_crm_pipelines_tenant", "tenant_id"),)

    def __repr__(self) -> str:
        return f"<CrmPipeline {self.name!r}>"


class CrmPipelineStage(TimestampMixin, Base):
    """A stage within a pipeline."""

    __tablename__ = "crm_pipeline_stages"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    pipeline_id: Mapped[int] = mapped_column(
        ForeignKey("crm_pipelines.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    probability: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#6B7280", nullable=False)

    is_won: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_lost: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="crm_pipeline_stages")
    pipeline = relationship("CrmPipeline", back_populates="stages")
    deals = relationship("CrmDeal", back_populates="stage")

    __table_args__ = (
        Index("ix_crm_pipeline_stages_pipeline", "pipeline_id", "position"),
    )

    def __repr__(self) -> str:
        return f"<CrmPipelineStage {self.name!r} @ position {self.position}>"


class CrmDeal(TimestampMixin, Base):
    """A sales opportunity/deal."""

    __tablename__ = "crm_deals"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )

    # Relations
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    pipeline_id: Mapped[int] = mapped_column(
        ForeignKey("crm_pipelines.id"), nullable=False
    )
    stage_id: Mapped[int] = mapped_column(
        ForeignKey("crm_pipeline_stages.id"), nullable=False
    )
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Deal Info
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    probability: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expected_close: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    lost_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    won_at: Mapped[datetime | None] = mapped_column(nullable=True)
    lost_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Priority & Tags
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Notes & Custom
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_fields: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="crm_deals")
    contact = relationship("Contact", back_populates="deals")
    company = relationship("Company", back_populates="deals")
    pipeline = relationship("CrmPipeline", back_populates="deals")
    stage = relationship("CrmPipelineStage", back_populates="deals")
    owner = relationship("User", back_populates="owned_deals")
    activities = relationship(
        "CrmActivity", back_populates="deal", cascade="all, delete-orphan"
    )
    tasks = relationship("CrmTask", back_populates="deal", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_crm_deals_tenant_pipeline_stage", "tenant_id", "pipeline_id", "stage_id"),
        Index("ix_crm_deals_tenant_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<CrmDeal {self.title!r} ({self.status})>"


class CrmActivity(TimestampMixin, Base):
    """Activity log for contacts, companies, and deals."""

    __tablename__ = "crm_activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )

    # Relations (at least one should be set)
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), nullable=True
    )
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=True
    )
    deal_id: Mapped[int | None] = mapped_column(
        ForeignKey("crm_deals.id", ondelete="CASCADE"), nullable=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Activity details
    activity_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # call, meeting, email, note, task_completed
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    activity_date: Mapped[datetime] = mapped_column(nullable=False)

    # Metadata
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)

    # Relationships
    tenant = relationship("Tenant", back_populates="crm_activities")
    contact = relationship("Contact", back_populates="activities")
    company = relationship("Company", back_populates="activities")
    deal = relationship("CrmDeal", back_populates="activities")
    user = relationship("User", back_populates="crm_activities")

    __table_args__ = (
        Index("ix_crm_activities_tenant_contact", "tenant_id", "contact_id"),
        Index("ix_crm_activities_tenant_deal", "tenant_id", "deal_id"),
    )

    def __repr__(self) -> str:
        return f"<CrmActivity {self.activity_type!r}: {self.subject!r}>"


class CrmTask(TimestampMixin, Base):
    """Task associated with contacts, companies, or deals."""

    __tablename__ = "crm_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )

    # Relations
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), nullable=True
    )
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=True
    )
    deal_id: Mapped[int | None] = mapped_column(
        ForeignKey("crm_deals.id", ondelete="CASCADE"), nullable=True
    )
    assigned_to: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Task details
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="crm_tasks")
    contact = relationship("Contact", back_populates="tasks")
    company = relationship("Company", back_populates="tasks")
    deal = relationship("CrmDeal", back_populates="tasks")
    assignee = relationship(
        "User", foreign_keys=[assigned_to], back_populates="assigned_tasks"
    )
    creator = relationship(
        "User", foreign_keys=[created_by], back_populates="created_tasks"
    )

    __table_args__ = (
        Index("ix_crm_tasks_tenant_status", "tenant_id", "status"),
        Index("ix_crm_tasks_tenant_assigned", "tenant_id", "assigned_to"),
    )

    def __repr__(self) -> str:
        return f"<CrmTask {self.title!r} ({self.status})>"
