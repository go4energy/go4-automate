"""Leadgen Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ---- Campaign ----


class CampaignBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    queries: list[str] = Field(default_factory=list)
    language: str = "de"
    region: str = "DE"
    target_match_threshold: int = Field(default=5, ge=0, le=10)
    target_engagement_pipeline_id: int | None = None
    source: str = Field(default="google_places", max_length=30)
    source_config: dict = Field(default_factory=dict)


class CampaignCreate(CampaignBase):
    create_new_pipeline: bool = Field(
        default=False,
        description=(
            "Wenn True und target_engagement_pipeline_id leer ist: "
            "Service legt eine neue Engagement-Pipeline mit Defaults "
            "(channels=[postmail,email]) an und verknuepft sie."
        ),
    )


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    queries: list[str] | None = None
    language: str | None = None
    region: str | None = None
    target_match_threshold: int | None = Field(default=None, ge=0, le=10)
    target_engagement_pipeline_id: int | None = None
    status: str | None = Field(
        default=None, pattern=r"^(draft|active|paused|completed)$"
    )
    source: str | None = Field(default=None, max_length=30)
    source_config: dict | None = None


class ActiveRunSummary(BaseModel):
    """Lightweight summary of the currently active or last run for a campaign."""

    id: int
    status: str
    current_stage: str
    processed: int = 0
    total: int = 0
    cost_cents: int = 0


class CampaignResponse(CampaignBase):
    id: int
    tenant_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    # Lightweight stats — populated by the service layer for list/detail views
    # so the frontend does not need an extra round-trip.
    total_places: int = 0
    enriched_places: int = 0
    active_run: ActiveRunSummary | None = None

    model_config = ConfigDict(from_attributes=True)


class CampaignStats(BaseModel):
    campaign_id: int
    total_places: int
    by_status: dict[str, int]
    total_cost_cents: int
    runs_total: int
    runs_running: int


# ---- Run ----


class RunResponse(BaseModel):
    id: int
    campaign_id: int
    current_stage: str
    status: str
    processed_count: int
    success_count: int
    error_count: int
    cost_cents: int
    stage_state: dict = Field(default_factory=dict)
    started_at: datetime | None
    completed_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---- Place ----


class ImpressumSummary(BaseModel):
    """Inline-Response for enrichment data on a Place."""

    email: str | None = None
    phone: str | None = None
    managing_directors: list[str] = Field(default_factory=list)
    postal_address: str | None = None
    handelsregister: str | None = None
    ust_id: str | None = None
    source_url: str | None = None
    extraction_error: str | None = None
    extracted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PrimaryContact(BaseModel):
    """Best-guess contact person for the downstream outreach module."""

    salutation: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    gender: str | None = None
    role: str | None = None
    source: str | None = None

    model_config = ConfigDict(from_attributes=True)


class LLMInsightsSummary(BaseModel):
    """Inline-Response for Stage-3 LLM analysis on a Place."""

    target_match_score: int | None = None
    services: list[str] = Field(default_factory=list)
    brands: list[str] = Field(default_factory=list)
    customer_segments: list[str] = Field(default_factory=list)
    company_size_indicator: str | None = None
    personalization_hook: str | None = None
    red_flags: list[str] = Field(default_factory=list)
    primary_contact: PrimaryContact | None = None
    pages_analyzed: list[str] = Field(default_factory=list)
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_cents: int = 0
    model_used: str | None = None
    extraction_error: str | None = None
    extracted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PlaceResponse(BaseModel):
    id: int
    campaign_id: int
    run_id: int | None
    google_place_id: str
    name: str
    address_street: str | None
    address_zip: str | None
    address_city: str | None
    formatted_address: str | None
    website: str | None
    phone: str | None
    rating: float | None
    user_ratings_total: int | None
    business_status: str | None
    status: str
    rejected_reason: str | None
    contact_id: int | None
    created_at: datetime
    impressum: ImpressumSummary | None = None
    llm_insights: LLMInsightsSummary | None = None

    model_config = ConfigDict(from_attributes=True)


class PlaceListResponse(BaseModel):
    items: list[PlaceResponse]
    total: int
    page: int
    size: int


class PlaceRejectRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=200)


class RunResumeRequest(BaseModel):
    additional_budget: int | None = Field(
        default=None,
        ge=1,
        le=100_000,
        description=(
            "Optional extra API calls to add to the campaign's max_api_calls "
            "before resuming. Useful when the previous run paused at the budget."
        ),
    )


class EnrichRunRequest(BaseModel):
    """Start an LLM-only enrichment run on already-discovered places.

    Skips Stage 1 (Google Places) and Stage 2 (Impressum-scraping) entirely
    and runs the LLM analysis on `limit` places that are not yet enriched.
    """

    limit: int = Field(..., ge=1, le=10_000)
    sampling: str = Field(
        default="top_rated",
        pattern=r"^(top_rated|random)$",
        description=(
            "top_rated: best Google rating first (default); "
            "random: shuffle uniformly across the eligible pool"
        ),
    )


class HandoffRequest(BaseModel):
    """Convert top-scoring places into contacts and bulk-enroll them in the
    campaign's linked engagement pipeline."""

    min_score: int = Field(default=7, ge=0, le=10)
    limit: int = Field(default=100, ge=1, le=10_000)
    pipeline_id: int | None = Field(
        default=None,
        description=(
            "Override the campaign's target_engagement_pipeline_id."
            " Defaults to the campaign-linked pipeline."
        ),
    )


class HandoffPreview(BaseModel):
    """Pre-flight stats so the user sees what will happen before clicking."""

    eligible_total: int
    would_enroll: int
    already_have_contact: int
    missing_email: int


class HandoffResponse(BaseModel):
    """Outcome of the actual handoff."""

    enrolled: int
    skipped: int
    errors: list[str] = Field(default_factory=list)
    contacts_created: int
    contacts_reused: int
    skipped_no_email: int
    skipped_existing: int
    pipeline_id: int


class ExportFilter(BaseModel):
    """Filter parameters shared by the LinkedIn CSV exports."""

    min_score: int = Field(default=7, ge=0, le=10)
    limit: int = Field(default=10_000, ge=1, le=50_000)
    only_enrolled: bool = Field(
        default=False,
        description=(
            "True: only places already handed off (contact_id NOT NULL). "
            "False: all qualifying places."
        ),
    )


class ExportPreview(BaseModel):
    """How many rows each export format would produce for the current filter."""

    accounts_count: int
    leads_count: int
