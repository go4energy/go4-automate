"""LinkedIn models - Account, ScraperJob, Contact, Connection, Message, Campaign."""

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


class LinkedInAccount(TimestampMixin, Base):
    """LinkedIn account for Sales Navigator access."""

    __tablename__ = "linkedin_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )

    # Account info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Session management
    session_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    session_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="inactive", nullable=False
    )  # inactive, active, suspended, rate_limited, warmup
    is_sales_navigator: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Rate limiting & Safety
    daily_profile_limit: Mapped[int] = mapped_column(
        Integer, default=100, nullable=False
    )
    daily_connection_limit: Mapped[int] = mapped_column(
        Integer, default=25, nullable=False
    )
    daily_message_limit: Mapped[int] = mapped_column(
        Integer, default=50, nullable=False
    )
    profiles_scraped_today: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    connections_sent_today: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    messages_sent_today: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    total_profiles_scraped: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    last_scrape_date: Mapped[datetime | None] = mapped_column(nullable=True)

    # Warmup settings
    warmup_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    warmup_day: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # Days since account added (0-14)
    warmup_started_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="linkedin_accounts")
    scraper_jobs = relationship(
        "LinkedInScraperJob",
        back_populates="account",
        cascade="all, delete-orphan",
    )
    connections = relationship(
        "LinkedInConnection",
        back_populates="account",
        cascade="all, delete-orphan",
    )
    messages = relationship(
        "LinkedInMessage",
        back_populates="account",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_linkedin_accounts_tenant", "tenant_id"),
        Index("ix_linkedin_accounts_tenant_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<LinkedInAccount {self.name!r} ({self.status})>"

    def get_effective_limits(self) -> dict:
        """Get effective daily limits considering warmup phase."""
        if not self.warmup_enabled or self.warmup_day >= 14:
            return {
                "connections": self.daily_connection_limit,
                "messages": self.daily_message_limit,
                "profiles": self.daily_profile_limit,
            }
        # Warmup: gradually increase limits over 14 days
        warmup_factor = min(1.0, (self.warmup_day + 1) / 14)
        return {
            "connections": max(3, int(self.daily_connection_limit * warmup_factor)),
            "messages": max(5, int(self.daily_message_limit * warmup_factor)),
            "profiles": max(10, int(self.daily_profile_limit * warmup_factor)),
        }


class LinkedInScraperJob(TimestampMixin, Base):
    """LinkedIn scraper job configuration and status."""

    __tablename__ = "linkedin_scraper_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("linkedin_accounts.id", ondelete="CASCADE"), nullable=False
    )
    funnel_id: Mapped[int | None] = mapped_column(
        ForeignKey("funnel_funnels.id", ondelete="SET NULL"), nullable=True
    )
    pipeline_id: Mapped[int | None] = mapped_column(
        ForeignKey("engagement_pipelines.id", ondelete="SET NULL"), nullable=True
    )

    # Job configuration
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    job_type: Mapped[str] = mapped_column(
        String(30), default="search", nullable=False
    )  # search, profile_list, connections
    search_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_urls: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Limits
    max_profiles: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    daily_limit: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    min_delay_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    max_delay_seconds: Mapped[int] = mapped_column(Integer, default=120, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False
    )  # draft, queued, running, paused, completed, failed, cancelled
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Progress
    profiles_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    profiles_scraped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    profiles_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_page: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_profile_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Scraping options
    scrape_full_profiles: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # If True, also scrape full profile pages for detailed data

    # Auto-import settings
    auto_import: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    import_stage_id: Mapped[int | None] = mapped_column(
        ForeignKey("funnel_stages.id", ondelete="SET NULL"), nullable=True
    )
    # Auto-enroll in pipeline (scrape → central contact → pipeline enrollment)
    auto_enroll_pipeline: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Schedule settings
    schedule_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    schedule_days: Mapped[list | None] = mapped_column(
        JSONB, nullable=True
    )  # [0,1,2,3,4] = Mo-Fr (0=Monday)
    schedule_start_time: Mapped[str | None] = mapped_column(
        String(5), nullable=True
    )  # "08:00"
    schedule_end_time: Mapped[str | None] = mapped_column(
        String(5), nullable=True
    )  # "18:00"
    max_pages_per_run: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False
    )  # Pages per execution

    # Connections job settings
    connections_since_date: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="linkedin_scraper_jobs")
    account = relationship("LinkedInAccount", back_populates="scraper_jobs")
    funnel = relationship("Funnel")
    pipeline = relationship("EngagementPipeline")
    import_stage = relationship("FunnelStage")
    contacts = relationship(
        "LinkedInContact",
        back_populates="scraper_job",
        cascade="all, delete-orphan",
    )
    logs = relationship(
        "LinkedInJobLog",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="desc(LinkedInJobLog.created_at)",
    )

    __table_args__ = (
        Index("ix_linkedin_jobs_tenant", "tenant_id"),
        Index("ix_linkedin_jobs_tenant_status", "tenant_id", "status"),
        Index("ix_linkedin_jobs_account", "account_id"),
    )

    def __repr__(self) -> str:
        return f"<LinkedInScraperJob {self.name!r} ({self.status})>"


class LinkedInContact(TimestampMixin, Base):
    """Scraped LinkedIn contact."""

    __tablename__ = "linkedin_contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    scraper_job_id: Mapped[int] = mapped_column(
        ForeignKey("linkedin_scraper_jobs.id", ondelete="CASCADE"), nullable=False
    )

    # LinkedIn identifiers
    linkedin_url: Mapped[str] = mapped_column(String(500), nullable=False)
    linkedin_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    profile_urn: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sales_navigator_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Basic info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    profile_picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Connection info
    contact_degree: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1, 2, 3
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)  # male, female, unknown
    is_followed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    follower_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    connection_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Company info
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    company_linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    company_size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    company_industry: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Contact info (if available)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    twitter_url: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # About/Summary
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Connection timing
    connected_at: Mapped[datetime | None] = mapped_column(nullable=True)
    connected_at_text: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Experience & Education (JSONB for flexibility)
    experience: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    education: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    skills: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    languages: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    interests: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="scraped", nullable=False
    )  # scraped, imported, failed, skipped
    excluded: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # If True, contact is excluded from messaging/pipelines

    # Central contact integration
    central_contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )

    # Funnel integration
    funnel_prospect_id: Mapped[int | None] = mapped_column(
        ForeignKey("funnel_prospects.id", ondelete="SET NULL"), nullable=True
    )
    funnel_company_id: Mapped[int | None] = mapped_column(
        ForeignKey("funnel_companies.id", ondelete="SET NULL"), nullable=True
    )
    imported_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Raw data backup
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    scrape_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="linkedin_contacts")
    scraper_job = relationship("LinkedInScraperJob", back_populates="contacts")
    central_contact = relationship("Contact", foreign_keys=[central_contact_id])
    funnel_prospect = relationship("FunnelProspect")
    funnel_company = relationship("FunnelCompany")

    __table_args__ = (
        Index("ix_linkedin_contacts_tenant", "tenant_id"),
        Index("ix_linkedin_contacts_job", "scraper_job_id"),
        Index("ix_linkedin_contacts_status", "tenant_id", "status"),
        Index("ix_linkedin_contacts_linkedin_url", "tenant_id", "linkedin_url"),
    )

    def __repr__(self) -> str:
        return f"<LinkedInContact {self.name!r} ({self.linkedin_url})>"


class LinkedInJobLog(TimestampMixin, Base):
    """Log entry for a scraper job execution."""

    __tablename__ = "linkedin_job_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    job_id: Mapped[int] = mapped_column(
        ForeignKey("linkedin_scraper_jobs.id", ondelete="CASCADE"), nullable=False
    )

    # Execution timing
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Progress tracking
    start_page: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    end_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profiles_scraped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    profiles_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    profiles_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="running", nullable=False
    )  # running, completed, failed, cancelled
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    tenant = relationship("Tenant")
    job = relationship("LinkedInScraperJob", back_populates="logs")

    __table_args__ = (
        Index("ix_linkedin_job_logs_job", "job_id"),
        Index("ix_linkedin_job_logs_job_created", "job_id", "created_at"),
        Index("ix_linkedin_job_logs_tenant", "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<LinkedInJobLog job={self.job_id} status={self.status}>"


# ============== NEW MODELS FOR PHASE 1 ==============


class LinkedInMessageTemplate(TimestampMixin, Base):
    """Message template with variable support."""

    __tablename__ = "linkedin_message_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), default="general", nullable=False
    )  # connection_request, first_message, follow_up, inmail
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)  # For InMail
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Variables: {first_name}, {company}, {position}, {mutual_connections}, etc.
    # Stored as list of available variables for this template
    variables: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # A/B Testing
    variant_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("linkedin_message_templates.id", ondelete="SET NULL"), nullable=True
    )
    variant_name: Mapped[str | None] = mapped_column(String(50), nullable=True)  # A, B, C

    # Stats
    times_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    responses_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    tenant = relationship("Tenant")
    variants = relationship(
        "LinkedInMessageTemplate",
        backref="parent_template",
        remote_side=[id],
    )

    __table_args__ = (
        Index("ix_linkedin_templates_tenant", "tenant_id"),
        Index("ix_linkedin_templates_category", "tenant_id", "category"),
    )

    def __repr__(self) -> str:
        return f"<LinkedInMessageTemplate {self.name!r}>"

    def render(self, context: dict) -> str:
        """Render template with context variables."""
        result = self.content
        for key, value in context.items():
            result = result.replace(f"{{{key}}}", str(value) if value else "")
        return result


class LinkedInConnection(TimestampMixin, Base):
    """Connection request tracking."""

    __tablename__ = "linkedin_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("linkedin_accounts.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("linkedin_contacts.id", ondelete="SET NULL"), nullable=True
    )

    # Target profile
    linkedin_url: Mapped[str] = mapped_column(String(500), nullable=False)
    linkedin_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    profile_name: Mapped[str] = mapped_column(String(200), nullable=False)
    profile_headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Connection request
    message: Mapped[str | None] = mapped_column(Text, nullable=True)  # Connection note (300 chars max)
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("linkedin_message_templates.id", ondelete="SET NULL"), nullable=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(30), default="pending", nullable=False
    )  # pending, sent, accepted, declined, withdrawn, error

    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Campaign tracking
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("linkedin_campaigns.id", ondelete="SET NULL"), nullable=True
    )
    campaign_lead_id: Mapped[int | None] = mapped_column(
        ForeignKey("linkedin_campaign_leads.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    tenant = relationship("Tenant")
    account = relationship("LinkedInAccount", back_populates="connections")
    contact = relationship("LinkedInContact")
    template = relationship("LinkedInMessageTemplate")
    campaign = relationship("LinkedInCampaign", back_populates="connections")

    __table_args__ = (
        Index("ix_linkedin_connections_tenant", "tenant_id"),
        Index("ix_linkedin_connections_account", "account_id"),
        Index("ix_linkedin_connections_status", "tenant_id", "status"),
        Index("ix_linkedin_connections_linkedin_url", "tenant_id", "linkedin_url"),
        Index("ix_linkedin_connections_campaign", "campaign_id"),
    )

    def __repr__(self) -> str:
        return f"<LinkedInConnection {self.profile_name!r} ({self.status})>"


class LinkedInMessage(TimestampMixin, Base):
    """Direct message tracking."""

    __tablename__ = "linkedin_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("linkedin_accounts.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("linkedin_contacts.id", ondelete="SET NULL"), nullable=True
    )
    connection_id: Mapped[int | None] = mapped_column(
        ForeignKey("linkedin_connections.id", ondelete="SET NULL"), nullable=True
    )

    # Conversation
    conversation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # LinkedIn's ID
    thread_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Target profile
    linkedin_url: Mapped[str] = mapped_column(String(500), nullable=False)
    profile_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Message content
    message_type: Mapped[str] = mapped_column(
        String(30), default="direct", nullable=False
    )  # direct, inmail, follow_up
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)  # For InMail
    content: Mapped[str] = mapped_column(Text, nullable=False)
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("linkedin_message_templates.id", ondelete="SET NULL"), nullable=True
    )

    # Direction
    direction: Mapped[str] = mapped_column(
        String(10), default="outbound", nullable=False
    )  # outbound, inbound

    # Status
    status: Mapped[str] = mapped_column(
        String(30), default="pending", nullable=False
    )  # pending, sent, delivered, read, replied, failed

    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Campaign tracking
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("linkedin_campaigns.id", ondelete="SET NULL"), nullable=True
    )
    campaign_lead_id: Mapped[int | None] = mapped_column(
        ForeignKey("linkedin_campaign_leads.id", ondelete="SET NULL"), nullable=True
    )
    campaign_step_id: Mapped[int | None] = mapped_column(
        ForeignKey("linkedin_campaign_steps.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    tenant = relationship("Tenant")
    account = relationship("LinkedInAccount", back_populates="messages")
    contact = relationship("LinkedInContact")
    connection = relationship("LinkedInConnection")
    template = relationship("LinkedInMessageTemplate")
    campaign = relationship("LinkedInCampaign", back_populates="messages")

    __table_args__ = (
        Index("ix_linkedin_messages_tenant", "tenant_id"),
        Index("ix_linkedin_messages_account", "account_id"),
        Index("ix_linkedin_messages_status", "tenant_id", "status"),
        Index("ix_linkedin_messages_conversation", "conversation_id"),
        Index("ix_linkedin_messages_campaign", "campaign_id"),
        Index("ix_linkedin_messages_direction", "tenant_id", "direction"),
    )

    def __repr__(self) -> str:
        return f"<LinkedInMessage to={self.profile_name!r} ({self.status})>"


# ============== CAMPAIGN MODELS (PHASE 2) ==============


class LinkedInCampaign(TimestampMixin, Base):
    """Multi-step outreach campaign."""

    __tablename__ = "linkedin_campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("linkedin_accounts.id", ondelete="CASCADE"), nullable=False
    )
    pipeline_id: Mapped[int | None] = mapped_column(
        ForeignKey("engagement_pipelines.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False
    )  # draft, active, paused, completed, archived

    # Settings
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Berlin", nullable=False)

    # Daily limits (override account limits for this campaign)
    daily_connection_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_message_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Schedule (when to run)
    schedule_days: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # [0,1,2,3,4] = Mo-Fr
    schedule_start_time: Mapped[str | None] = mapped_column(String(5), nullable=True)  # "09:00"
    schedule_end_time: Mapped[str | None] = mapped_column(String(5), nullable=True)  # "18:00"

    # Stop conditions
    stop_on_reply: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    stop_on_connect: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Stats (cached for performance)
    total_leads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    leads_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    leads_active: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    connections_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    connections_accepted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    messages_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    replies_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    tenant = relationship("Tenant")
    account = relationship("LinkedInAccount")
    steps = relationship(
        "LinkedInCampaignStep",
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="LinkedInCampaignStep.order",
    )
    leads = relationship(
        "LinkedInCampaignLead",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )
    connections = relationship("LinkedInConnection", back_populates="campaign")
    messages = relationship("LinkedInMessage", back_populates="campaign")

    __table_args__ = (
        Index("ix_linkedin_campaigns_tenant", "tenant_id"),
        Index("ix_linkedin_campaigns_status", "tenant_id", "status"),
        Index("ix_linkedin_campaigns_account", "account_id"),
    )

    def __repr__(self) -> str:
        return f"<LinkedInCampaign {self.name!r} ({self.status})>"


class LinkedInCampaignStep(TimestampMixin, Base):
    """Step in a campaign workflow."""

    __tablename__ = "linkedin_campaign_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("linkedin_campaigns.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)

    # Step type
    step_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # connect, message, inmail, view_profile, follow, wait, condition

    # Wait step
    wait_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wait_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Message/Connect step
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("linkedin_message_templates.id", ondelete="SET NULL"), nullable=True
    )

    # A/B Testing - multiple templates
    template_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # For A/B test
    ab_test_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Condition step (for branching)
    condition_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # replied, connected, opened
    condition_true_step_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    condition_false_step_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Stats
    leads_entered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    leads_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    leads_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    tenant = relationship("Tenant")
    campaign = relationship("LinkedInCampaign", back_populates="steps")
    template = relationship("LinkedInMessageTemplate")

    __table_args__ = (
        Index("ix_linkedin_campaign_steps_campaign", "campaign_id"),
        Index("ix_linkedin_campaign_steps_order", "campaign_id", "order"),
    )

    def __repr__(self) -> str:
        return f"<LinkedInCampaignStep {self.name!r} ({self.step_type})>"


class LinkedInCampaignLead(TimestampMixin, Base):
    """Lead in a campaign with progress tracking."""

    __tablename__ = "linkedin_campaign_leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("linkedin_campaigns.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("linkedin_contacts.id", ondelete="SET NULL"), nullable=True
    )

    # Profile info (denormalized for performance)
    linkedin_url: Mapped[str] = mapped_column(String(500), nullable=False)
    linkedin_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    profile_name: Mapped[str] = mapped_column(String(200), nullable=False)
    profile_headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    profile_picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Custom variables for templates
    custom_variables: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Progress
    current_step_id: Mapped[int | None] = mapped_column(
        ForeignKey("linkedin_campaign_steps.id", ondelete="SET NULL"), nullable=True
    )
    current_step_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(30), default="pending", nullable=False
    )  # pending, active, waiting, completed, replied, connected, failed, stopped

    # Engagement tracking
    connection_status: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # not_sent, pending, accepted, declined
    has_replied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reply_received_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Timing
    entered_campaign_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, nullable=False
    )
    next_action_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # A/B Test tracking
    ab_variant: Mapped[str | None] = mapped_column(String(10), nullable=True)  # A, B, C

    # Relationships
    tenant = relationship("Tenant")
    campaign = relationship("LinkedInCampaign", back_populates="leads")
    contact = relationship("LinkedInContact")
    current_step = relationship("LinkedInCampaignStep")

    __table_args__ = (
        Index("ix_linkedin_campaign_leads_campaign", "campaign_id"),
        Index("ix_linkedin_campaign_leads_status", "campaign_id", "status"),
        Index("ix_linkedin_campaign_leads_next_action", "next_action_at"),
        Index("ix_linkedin_campaign_leads_linkedin_url", "tenant_id", "linkedin_url"),
    )

    def __repr__(self) -> str:
        return f"<LinkedInCampaignLead {self.profile_name!r} ({self.status})>"
