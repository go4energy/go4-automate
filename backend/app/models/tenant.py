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

    # Relationships - Domain Modules
    crm_contacts = relationship("CrmContact", back_populates="tenant", lazy="selectin")
    crm_email_logs = relationship(
        "CrmEmailLog", back_populates="tenant", lazy="selectin"
    )
    creator_pieces = relationship(
        "CreatorPiece", back_populates="tenant", lazy="selectin"
    )
    creator_calendar = relationship(
        "CreatorCalendar", back_populates="tenant", lazy="selectin"
    )
    campaigns = relationship(
        "Campaign", back_populates="tenant", lazy="selectin"
    )
    campaign_performances = relationship(
        "CampaignPerformance", back_populates="tenant", lazy="selectin"
    )
    collector_groups = relationship(
        "CollectorGroup", back_populates="tenant", lazy="selectin"
    )
    collector_sources = relationship(
        "CollectorSource", back_populates="tenant", lazy="selectin"
    )
    collector_findings = relationship(
        "CollectorFinding", back_populates="tenant", lazy="selectin"
    )
    collector_topics = relationship(
        "CollectorTopic", back_populates="tenant", lazy="selectin"
    )

    # Contacts
    contacts = relationship("Contact", back_populates="tenant", lazy="selectin")
    companies = relationship("Company", back_populates="tenant", lazy="selectin")

    # CRM
    crm_pipelines = relationship("CrmPipeline", back_populates="tenant", lazy="selectin")
    crm_pipeline_stages = relationship(
        "CrmPipelineStage", back_populates="tenant", lazy="selectin"
    )
    crm_deals = relationship("CrmDeal", back_populates="tenant", lazy="selectin")
    crm_activities = relationship("CrmActivity", back_populates="tenant", lazy="selectin")
    crm_tasks = relationship("CrmTask", back_populates="tenant", lazy="selectin")

    # Funnels
    funnels = relationship("Funnel", back_populates="tenant", lazy="selectin")
    funnel_stages = relationship("FunnelStage", back_populates="tenant", lazy="selectin")
    funnel_companies = relationship(
        "FunnelCompany", back_populates="tenant", lazy="selectin"
    )
    funnel_prospects = relationship(
        "FunnelProspect", back_populates="tenant", lazy="selectin"
    )
    funnel_activities = relationship(
        "FunnelActivity", back_populates="tenant", lazy="selectin"
    )
    funnel_handoffs = relationship(
        "FunnelHandoff", back_populates="tenant", lazy="selectin"
    )

    # Shared
    prompts = relationship("Prompt", back_populates="tenant", lazy="selectin")
    conversations = relationship(
        "Conversation", back_populates="tenant", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Tenant {self.tenant_id}>"
