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
            "(channels=[letter,email]) an und verknuepft sie."
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
    # Company-level LinkedIn URL discovered by impressum-link extraction or the
    # linkedin worker stage. ``match_method`` says where it came from so the
    # detail view can show provenance ('Impressum' vs 'Serper').
    linkedin_company_url: str | None = None
    linkedin_company_match_method: str | None = None
    impressum: ImpressumSummary | None = None
    llm_insights: LLMInsightsSummary | None = None
    # Materialised person rows from leadgen_contacts. Empty list when the
    # linkedin stage hasn't run yet — the detail view degrades gracefully.
    contacts: list["LeadgenContactRead"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class PlaceNeighborsResponse(BaseModel):
    """Forward/backward neighbours for the prospect detail-view arrows."""

    prev_id: int | None
    next_id: int | None


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
    """Start an enrichment run on already-discovered places.

    Skips Stage 1 (Google Places) entirely and runs the selected ``stages``
    on ``limit`` places that are not yet fully enriched.
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
    stages: list[str] | None = Field(
        default=None,
        description=(
            "Subset of ('impressum','verify','llm','linkedin') to run. "
            "When None the legacy default ('verify','llm') is used so existing "
            "callers keep their behaviour."
        ),
    )
    # Filter eligible places by LLM match-score. The LinkedIn stage typically
    # only makes sense on already-llm-scored leads, so this lets the operator
    # cap Serper-spend to the top-quality prospects (e.g. min_match_score=7
    # for "only Match >= 7/10"). None = no filter, run on the full pool.
    min_match_score: int | None = Field(
        default=None,
        ge=0,
        le=10,
        description=(
            "Optional: only consider places whose LLM target_match_score >= "
            "this value. Requires the llm stage to have run on those places."
        ),
    )
    # LinkedIn-stage knob: companies cost a separate Serper call per place,
    # but for outreach personalisation the operator usually only needs the
    # person-level URLs. Default off so the cheap path is the default; toggle
    # on when the operator also wants linkedin_company_url filled.
    enrich_companies: bool = Field(
        default=False,
        description=(
            "When True the linkedin stage also issues a Serper query per "
            "place for the company LinkedIn URL. Default False keeps the run "
            "cheaper and focused on the per-person URLs that outreach needs."
        ),
    )
    # Apollo-stage knob: by default Apollo runs on every contact under the
    # campaign (whether or not we already found a LinkedIn URL). Toggle on to
    # restrict Apollo lookups to contacts that already carry a LinkedIn URL,
    # which gives Apollo its highest-confidence input and avoids burning
    # credits on weakly-identified contacts.
    apollo_validate_existing_urls: bool = Field(
        default=False,
        description=(
            "When True, Apollo also processes contacts that already have a "
            "LinkedIn URL (from Serper or manual) — confirms or replaces them. "
            "Default False = Apollo only fills gaps Serper missed."
        ),
    )
    # Reveal-Flags consume additional Apollo credits on top of the 1 export
    # credit per match. Email reveals are unlimited on Pro Monthly (fair use)
    # so the toggle is essentially free; phone reveals are capped at 100/mo
    # AND require a configured webhook because Apollo delivers numbers async.
    apollo_reveal_email: bool = Field(
        default=False,
        description=(
            "When True, Apollo also returns the verified personal email "
            "address for matched contacts. Pro Monthly: unlimited (fair use)."
        ),
    )
    apollo_reveal_phone: bool = Field(
        default=False,
        description=(
            "When True, Apollo also returns mobile phone numbers via webhook. "
            "Pro Monthly: 100/month included. Requires "
            "settings.apollo_phone_webhook_url to be configured."
        ),
    )


class EnrichRunPreview(BaseModel):
    """Live count of how many places a given enrich-config would touch."""

    eligible_count: int
    # Number of leadgen_contacts under those places — i.e. the per-person
    # Serper calls the linkedin stage would issue. Same value the Apollo
    # export shows for the same filter.
    contact_count: int = 0
    # Number of leadgen_contacts the apollo stage would attempt to match
    # (= bulk-call requests / 10, rounded up). Equal to contact_count minus
    # already-Apollo-enriched contacts; honours apollo_require_linkedin.
    apollo_count: int = 0


class RunRequest(BaseModel):
    """Unified run request used by the new 'Run starten…' modal.

    Lets the user pick exactly which stages to run plus the enrich-style
    filters (only relevant when ``places`` is not selected).
    """

    stages: list[str] = Field(
        ...,
        min_length=1,
        description="Any non-empty subset of ('places','impressum','verify','llm','linkedin').",
    )
    limit: int | None = Field(
        default=None,
        ge=1,
        le=10_000,
        description="Required when 'places' is NOT in stages.",
    )
    sampling: str = Field(
        default="top_rated",
        pattern=r"^(top_rated|random)$",
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
    include_without_email: bool = Field(
        default=True,
        description=(
            "Also enroll places without an impressum email. They get a"
            " synthetic placeholder email so the Contact NOT NULL constraint"
            " holds, and become reachable via Letter / Phone channels even"
            " though Email is not viable for them."
        ),
    )


class HandoffPreview(BaseModel):
    """Pre-flight stats so the user sees what will happen before clicking."""

    eligible_total: int
    would_enroll: int
    already_have_contact: int
    missing_email: int
    # New: how many of the would-enroll come without an email and rely on
    # the synthetic-placeholder path. Frontend can warn that those leads
    # are letter/phone-only.
    would_enroll_without_email: int = 0


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
    # New: how many enrolled contacts had no real email and got a synthetic
    # placeholder. They are reachable only via Letter / Phone.
    enrolled_without_email: int = 0


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
    apollo_count: int = 0
    # Subset of ``apollo_count`` that already carries a LinkedIn URL — lets
    # the export modal show "10 255 gesamt, davon 1 234 mit LinkedIn-URL" so
    # the operator knows whether running the linkedin stage first is worth it.
    apollo_with_linkedin: int = 0


# ---- LeadgenContact ----


class LeadgenContactBase(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    full_name: str
    role: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    linkedin_match_method: str | None = None
    linkedin_match_confidence: float | None = None
    gender: str | None = None
    gender_confidence: float | None = None
    gender_method: str | None = None
    source: str


class LeadgenContactRead(LeadgenContactBase):
    id: int
    place_id: int
    tenant_id: str
    is_handed_off: bool
    contact_id: int | None
    extra: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Resolve the forward reference in PlaceResponse — declared above
# LeadgenContactRead so the FastAPI response model can serialise eager-loaded
# contact rows.
PlaceResponse.model_rebuild()


class PlaceMapPoint(BaseModel):
    """Lightweight place projection for the map view (cluster-ready)."""

    id: int
    name: str
    lat: float
    lng: float
    status: str | None = None
    city: str | None = None
    match_score: int | None = None  # from leadgen_llm_insights, 0..10

    model_config = ConfigDict(from_attributes=True)
