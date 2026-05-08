"""Leadgen models - Campaign, Run, Place, Impressum, LLM Insights, Contact."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class LeadgenCampaign(TimestampMixin, Base):
    """Leadgen campaign - a set of search queries plus target pipeline + thresholds."""

    __tablename__ = "leadgen_campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Identity
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Search config (legacy Stage-1 freetext queries).
    queries: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="de", nullable=False)
    region: Mapped[str] = mapped_column(String(10), default="DE", nullable=False)

    # Data source: google_places | northdata | handelsregister | ...
    source: Mapped[str] = mapped_column(
        String(30), default="google_places", nullable=False
    )
    # Source-specific parameters. For google_places, see places_source.py.
    source_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Qualification: minimum target_match_score (0-10) for handoff to engagement.
    target_match_threshold: Mapped[int] = mapped_column(default=5, nullable=False)

    # Handoff target (nullable: can be set later or left manual)
    target_engagement_pipeline_id: Mapped[int | None] = mapped_column(
        ForeignKey("engagement_pipelines.id", ondelete="SET NULL"), nullable=True
    )

    # Status: draft | active | paused | completed
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)

    # Relationships
    tenant = relationship("Tenant")
    runs = relationship(
        "LeadgenRun", back_populates="campaign", cascade="all, delete-orphan"
    )
    places = relationship(
        "LeadgenPlace", back_populates="campaign", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_leadgen_campaign_slug"),
        Index("ix_leadgen_campaigns_tenant", "tenant_id"),
    )


class LeadgenRun(TimestampMixin, Base):
    """Single execution of the leadgen pipeline for a campaign."""

    __tablename__ = "leadgen_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("leadgen_campaigns.id", ondelete="CASCADE"), nullable=False
    )

    # Stage: places | impressum | llm | fallback | completed
    current_stage: Mapped[str] = mapped_column(
        String(20), default="places", nullable=False
    )
    # Status: queued | running | paused | completed | failed
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)

    # Progress counters (updated per batch)
    processed_count: Mapped[int] = mapped_column(default=0, nullable=False)
    success_count: Mapped[int] = mapped_column(default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(default=0, nullable=False)

    # Cost tracking (stored in cents to avoid float)
    cost_cents: Mapped[int] = mapped_column(default=0, nullable=False)

    # Per-stage progress state for resume (e.g. last query index, last place id)
    stage_state: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    campaign = relationship("LeadgenCampaign", back_populates="runs")
    places = relationship("LeadgenPlace", back_populates="run")

    __table_args__ = (
        Index("ix_leadgen_runs_tenant_status", "tenant_id", "status"),
        Index("ix_leadgen_runs_campaign", "campaign_id"),
    )


class LeadgenPlace(TimestampMixin, Base):
    """A single place (business) discovered via Google Places API."""

    __tablename__ = "leadgen_places"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("leadgen_campaigns.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[int | None] = mapped_column(
        ForeignKey("leadgen_runs.id", ondelete="SET NULL"), nullable=True
    )

    # Source attribution
    source: Mapped[str] = mapped_column(
        String(30), default="google_places", nullable=False
    )
    source_record_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Google Places identity (kept for backwards compat; new code writes
    # source_record_id in parallel).
    google_place_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_query: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Core fields (parsed from Places payload)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    address_street: Mapped[str | None] = mapped_column(String(300), nullable=True)
    address_zip: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address_city: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address_country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    formatted_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    lat: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    lng: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    google_categories: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    rating: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    user_ratings_total: Mapped[int | None] = mapped_column(nullable=True)
    business_status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Full Places API payload for debugging / schema changes
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Pipeline status: discovered | impressum_done | impressum_failed |
    # llm_done | llm_failed | rejected | enrolled
    status: Mapped[str] = mapped_column(
        String(30), default="discovered", nullable=False
    )
    rejected_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Generic sales-signal bag populated during enrichment (Serper-verify,
    # Places-payload heuristics). Schema is intentionally loose so new signals
    # can be added without migrations.
    enrichment_flags: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Company-level LinkedIn URL (one per place). Populated by impressum-link
    # extraction first, then Serper fallback in the linkedin stage.
    linkedin_company_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    linkedin_company_match_method: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )

    # Handoff
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    campaign = relationship("LeadgenCampaign", back_populates="places")
    run = relationship("LeadgenRun", back_populates="places")
    impressum = relationship(
        "LeadgenImpressum",
        back_populates="place",
        uselist=False,
        cascade="all, delete-orphan",
    )
    llm_insights = relationship(
        "LeadgenLLMInsights",
        back_populates="place",
        uselist=False,
        cascade="all, delete-orphan",
    )
    contacts = relationship(
        "LeadgenContact",
        back_populates="place",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "google_place_id", name="uq_leadgen_place_google_id"
        ),
        Index("ix_leadgen_places_campaign_status", "campaign_id", "status"),
        Index("ix_leadgen_places_tenant", "tenant_id"),
    )


class LeadgenImpressum(TimestampMixin, Base):
    """Structured data extracted from a business's Impressum (§5 TMG)."""

    __tablename__ = "leadgen_impressum"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    place_id: Mapped[int] = mapped_column(
        ForeignKey("leadgen_places.id", ondelete="CASCADE"), nullable=False
    )

    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # §5 TMG fields
    managing_directors: Mapped[list] = mapped_column(
        JSONB, default=list, nullable=False
    )
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    postal_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    handelsregister: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ust_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Extraction status
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    place = relationship("LeadgenPlace", back_populates="impressum")

    __table_args__ = (
        UniqueConstraint("place_id", name="uq_leadgen_impressum_place"),
    )


class LeadgenLLMInsights(TimestampMixin, Base):
    """LLM-extracted business intelligence per place."""

    __tablename__ = "leadgen_llm_insights"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    place_id: Mapped[int] = mapped_column(
        ForeignKey("leadgen_places.id", ondelete="CASCADE"), nullable=False
    )

    # Scores & structured fields (0..10, match against campaign target profile)
    target_match_score: Mapped[int | None] = mapped_column(nullable=True)
    services: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    brands: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    customer_segments: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    company_size_indicator: Mapped[str | None] = mapped_column(String(200), nullable=True)
    personalization_hook: Mapped[str | None] = mapped_column(Text, nullable=True)
    red_flags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    # Structured contact person picked from team/contact/impressum pages so the
    # downstream mail/letter module can address the right person directly.
    # Schema: {"salutation": "Herr|Frau|null", "first_name": "...",
    #          "last_name": "...", "gender": "m|f|null",
    #          "role": "Geschaeftsfuehrer|Vertrieb|...",
    #          "source": "impressum|team-seite|kontakt-seite|unklar"}
    primary_contact: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Provenance / cost
    pages_analyzed: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(nullable=True)
    cost_cents: Mapped[int] = mapped_column(default=0, nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    place = relationship("LeadgenPlace", back_populates="llm_insights")

    __table_args__ = (
        UniqueConstraint("place_id", name="uq_leadgen_llm_insights_place"),
    )


class LeadgenContact(TimestampMixin, Base):
    """One row per person discovered for a place (managing director, primary
    contact, etc.). Source of truth for the Apollo CSV export and the
    ``linkedin`` worker stage. Migrated to ``contacts`` on engagement handoff.
    """

    __tablename__ = "leadgen_contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    place_id: Mapped[int] = mapped_column(
        ForeignKey("leadgen_places.id", ondelete="CASCADE"), nullable=False
    )

    # Identity
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # LinkedIn
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # impressum_link | serper | manual | None
    linkedin_match_method: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )
    linkedin_match_confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    # Gender for salutation
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    gender_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # library | llm | manual | jsonb_legacy
    gender_method: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Provenance
    # managing_director | primary_contact | impressum_link | manual
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    is_handed_off: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )

    # Apollo enrichment — populated by the apollo worker stage
    apollo_enriched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # high | medium | low | no_match
    apollo_match_quality: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    apollo_credits_used: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    # Free-form bag for future fields (LLM gender notes, raw_serper_hit, ...)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    place = relationship("LeadgenPlace", back_populates="contacts")

    __table_args__ = (
        UniqueConstraint(
            "place_id", "full_name", name="uq_leadgen_contacts_place_name"
        ),
        Index(
            "ix_leadgen_contacts_tenant_place",
            "tenant_id",
            "place_id",
        ),
        Index(
            "ix_leadgen_contacts_tenant_handoff",
            "tenant_id",
            "is_handed_off",
        ),
    )
