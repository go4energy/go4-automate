"""Customer Journey schemas - Pydantic validation for API endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ============== Identify (external API) ==============


class IdentifyRequest(BaseModel):
    """Lead identify request from go4.energy / Odoo / smartladen.de.

    ``tags`` und ``custom_fields`` sind generisch und steuern das
    Auto-Enrollment in Pipelines mit ``auto_enroll_filter``. Tag-Vokabular
    wählt der Tenant selbst (keine Whitelist).
    """

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    source: str | None = None
    source_detail: str | None = None
    existing_hash: str | None = None
    ref_code: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    metadata: dict = Field(default_factory=dict)
    # Generic tagging + structured properties — used by AutoEnrollmentRouter
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class IdentifyResponse(BaseModel):
    """Response from identify endpoint."""

    ok: bool = True
    tracking_hash: str
    lead_id: int
    is_new: bool
    merged: bool = False


# ============== Event (external API) ==============


class TrackEventRequest(BaseModel):
    """Event tracking request from go4.energy."""

    tracking_hash: str | None = None
    ref_code: str | None = None
    event: str
    page_path: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_term: str | None = None
    utm_content: str | None = None
    metadata: dict = Field(default_factory=dict)
    timestamp: datetime | None = None
    source_site: str = "go4.energy"


class TrackEventResponse(BaseModel):
    """Response from event tracking endpoint."""

    ok: bool = True
    tracking_hash: str | None = None


class BatchEventRequest(BaseModel):
    """Batch event request."""

    events: list[TrackEventRequest]


class BatchEventResponse(BaseModel):
    """Response from batch event endpoint."""

    ok: bool = True
    processed: int = 0
    errors: int = 0


# ============== Prepare Link (external API) ==============


class PrepareLinkRequest(BaseModel):
    """One-call endpoint: identify contact + resolve campaign + create ref-code + return link."""

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    source: str | None = "odoo"
    campaign_name: str | None = None
    campaign_channel: str | None = None
    target_url: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None


class PrepareLinkResponse(BaseModel):
    """Response with ready-to-use tracking link."""

    ok: bool = True
    tracking_hash: str
    ref_code: str
    link: str
    contact_id: int
    is_new_contact: bool
    is_new_ref: bool = True


# ============== Ref-Code Resolve (external API) ==============


class RefResolveResponse(BaseModel):
    """Response from ref-code resolve endpoint."""

    ok: bool = True
    tracking_hash: str
    ref_code: str
    lead_name: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None


# ============== Ref-Code CRUD (internal API) ==============


class RefCodeCreate(BaseModel):
    """Create a ref-code."""

    ref_code: str | None = None  # Auto-generated if not set
    contact_id: int | None = None
    campaign_id: int | None = None
    name: str | None = None
    context: str | None = None
    target_url: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    notify_on_visit: bool = False
    notify_channel: str = "none"
    notify_target: str | None = None


class BulkGenerateRequest(BaseModel):
    """Generate N ref-codes without contacts."""

    count: int = Field(..., ge=1, le=5000)
    campaign_id: int | None = None
    target_url: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    prefix: str | None = None  # Optional prefix for ref codes


class RefCodeUpdate(BaseModel):
    """Update a ref-code."""

    contact_id: int | None = None
    campaign_id: int | None = None
    name: str | None = None
    context: str | None = None
    target_url: str | None = None
    notify_on_visit: bool | None = None
    notify_channel: str | None = None
    notify_target: str | None = None


class RefCodeResponse(BaseModel):
    """Ref-code response with stats."""

    id: int
    tenant_id: str
    ref_code: str
    contact_id: int | None
    campaign_id: int | None
    name: str | None
    context: str | None
    target_url: str | None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    notify_on_visit: bool
    notify_channel: str
    notify_target: str | None
    visit_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BulkRefCodeCreate(BaseModel):
    """Bulk import ref-codes (Name;Context per line)."""

    lines: str  # "Name1;Context1\nName2;Context2"
    campaign_id: int | None = None
    target_url: str | None = None


# ============== Campaign CRUD ==============


class CampaignCreate(BaseModel):
    """Create a campaign."""

    name: str = Field(..., min_length=1, max_length=200)
    channel: str | None = None
    description: str | None = None


class CampaignUpdate(BaseModel):
    """Update a campaign."""

    name: str | None = Field(None, min_length=1, max_length=200)
    channel: str | None = None
    status: str | None = None
    description: str | None = None


class CampaignResponse(BaseModel):
    """Campaign response."""

    id: int
    tenant_id: str
    name: str
    channel: str | None
    status: str
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============== CSV Import ==============


class ImportPreviewRequest(BaseModel):
    """CSV preview with column mapping."""

    csv_raw: str = Field(..., min_length=1)
    mapping: dict[str, str]  # {csv_column: target_field}


class ImportConflictContact(BaseModel):
    """Existing contact found as conflict."""

    id: int
    name: str
    email: str
    linkedin: str | None


class ImportConflict(BaseModel):
    """A single conflict row."""

    row_index: int
    csv_row: dict
    mapped_data: dict
    existing_contact: ImportConflictContact


class ImportPreviewResponse(BaseModel):
    """Response from import preview."""

    headers: list[str]
    row_count: int
    new_count: int
    conflict_count: int
    conflicts: list[ImportConflict]
    preview_rows: list[dict]


class ImportExecuteRequest(BaseModel):
    """Execute the import."""

    csv_raw: str = Field(..., min_length=1)
    mapping: dict[str, str]
    base_url: str = Field(..., min_length=1)
    campaign_id: int | None = None
    conflict_resolutions: dict[str, str] = Field(default_factory=dict)
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None


class MappableField(BaseModel):
    """A field that can be mapped to."""

    key: str
    label: str
    group: str


# ============== Journey Event (internal/dashboard) ==============


class JourneyEventResponse(BaseModel):
    """Journey event for timeline display."""

    id: int
    contact_id: int | None
    contact_name: str | None = None
    contact_email: str | None = None
    event: str
    category: str | None
    page_path: str | None
    source_site: str
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    utm_term: str | None = None
    utm_content: str | None = None
    ref_code: str | None
    metadata_: dict = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    days_since_last_visit: int | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ============== Dashboard ==============


class DashboardStats(BaseModel):
    """Dashboard overview stats."""

    leads_total: int = 0
    leads_new_today: int = 0
    leads_new_week: int = 0
    events_today: int = 0
    events_week: int = 0
    conversions_week: int = 0
    ref_codes_total: int = 0
    campaigns_active: int = 0


class LeadListResponse(BaseModel):
    """Lead in list view (contact + journey data)."""

    id: int
    name: str
    email: str
    phone: str | None
    source: str | None
    tracking_hash: str | None
    journey_status: str | None
    event_count: int = 0
    last_event: str | None = None
    last_event_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeadWithEvents(LeadListResponse):
    """Lead enriched with its most recent events for the by-lead feed."""

    events: list[JourneyEventResponse] = Field(default_factory=list)
