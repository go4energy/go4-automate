"""Funnels schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ============== Funnel Schemas ==============


class FunnelStageCreate(BaseModel):
    """Schema for creating a funnel stage."""

    name: str = Field(..., min_length=1, max_length=100)
    position: int = 0
    color: str = "#6B7280"
    is_handoff: bool = False
    is_disqualified: bool = False
    auto_actions: dict | None = None


class FunnelStageUpdate(BaseModel):
    """Schema for updating a funnel stage."""

    name: str | None = Field(None, min_length=1, max_length=100)
    position: int | None = None
    color: str | None = None
    is_handoff: bool | None = None
    is_disqualified: bool | None = None
    auto_actions: dict | None = None


class FunnelStageResponse(BaseModel):
    """Schema for funnel stage response."""

    id: int
    funnel_id: int
    name: str
    position: int
    color: str
    is_handoff: bool
    is_disqualified: bool
    auto_actions: dict | None = None
    prospect_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class FunnelCreate(BaseModel):
    """Schema for creating a funnel."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    status: str = "active"
    color: str | None = None
    tags: list[str] = Field(default_factory=list)
    target_criteria: dict | None = None
    handoff_pipeline_id: int | None = None
    handoff_stage_id: int | None = None
    external_crm_config: dict | None = None
    stages: list[FunnelStageCreate] = Field(default_factory=list)


class FunnelUpdate(BaseModel):
    """Schema for updating a funnel."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    status: str | None = None
    color: str | None = None
    tags: list[str] | None = None
    target_criteria: dict | None = None
    handoff_pipeline_id: int | None = None
    handoff_stage_id: int | None = None
    external_crm_config: dict | None = None


class FunnelResponse(BaseModel):
    """Schema for funnel response."""

    id: int
    tenant_id: str
    owner_id: int | None
    name: str
    description: str | None
    status: str
    color: str | None
    tags: list[str]
    target_criteria: dict | None
    handoff_pipeline_id: int | None
    handoff_stage_id: int | None
    external_crm_config: dict | None
    stages: list[FunnelStageResponse] = []
    prospect_count: int = 0
    company_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FunnelListResponse(BaseModel):
    """Schema for funnel list response (lighter)."""

    id: int
    name: str
    description: str | None
    status: str
    color: str | None
    tags: list[str]
    stage_count: int = 0
    prospect_count: int = 0
    company_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============== Company Schemas ==============


class FunnelCompanyCreate(BaseModel):
    """Schema for creating a funnel company."""

    name: str = Field(..., min_length=1, max_length=200)
    domain: str | None = None
    website: str | None = None
    industry: str | None = None
    size: str | None = None
    address: dict | None = None
    phone: str | None = None
    email: EmailStr | None = None
    source: str | None = None
    source_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict = Field(default_factory=dict)


class FunnelCompanyUpdate(BaseModel):
    """Schema for updating a funnel company."""

    name: str | None = Field(None, min_length=1, max_length=200)
    domain: str | None = None
    website: str | None = None
    industry: str | None = None
    size: str | None = None
    address: dict | None = None
    phone: str | None = None
    email: EmailStr | None = None
    verified: bool | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None
    enrichment_data: dict | None = None


class FunnelCompanyResponse(BaseModel):
    """Schema for funnel company response."""

    id: int
    tenant_id: str
    funnel_id: int
    name: str
    domain: str | None
    website: str | None
    industry: str | None
    size: str | None
    address: dict | None
    phone: str | None
    email: str | None
    source: str | None
    source_id: str | None
    verified: bool
    verified_at: datetime | None
    dedup_key: str | None
    crm_company_id: int | None
    tags: list[str]
    custom_fields: dict
    enrichment_data: dict | None
    prospect_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FunnelCompanyListResponse(BaseModel):
    """Schema for funnel company list response (lighter)."""

    id: int
    funnel_id: int
    name: str
    domain: str | None
    industry: str | None
    size: str | None
    verified: bool
    tags: list[str]
    prospect_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============== Prospect Schemas ==============


class FunnelProspectCreate(BaseModel):
    """Schema for creating a funnel prospect."""

    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    mobile: str | None = None
    position: str | None = None
    department: str | None = None
    seniority: str | None = None
    linkedin_url: str | None = None
    twitter_url: str | None = None
    company_id: int | None = None
    stage_id: int | None = None
    owner_id: int | None = None
    source: str | None = None
    source_id: str | None = None
    score: int = 0
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict = Field(default_factory=dict)


class FunnelProspectUpdate(BaseModel):
    """Schema for updating a funnel prospect."""

    name: str | None = Field(None, min_length=1, max_length=200)
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    mobile: str | None = None
    position: str | None = None
    department: str | None = None
    seniority: str | None = None
    linkedin_url: str | None = None
    twitter_url: str | None = None
    company_id: int | None = None
    stage_id: int | None = None
    owner_id: int | None = None
    email_verified: bool | None = None
    score: int | None = None
    score_factors: dict | None = None
    status: str | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None
    enrichment_data: dict | None = None


class ProspectMoveRequest(BaseModel):
    """Schema for moving a prospect to a different stage."""

    stage_id: int


class FunnelProspectResponse(BaseModel):
    """Schema for funnel prospect response."""

    id: int
    tenant_id: str
    funnel_id: int
    company_id: int | None
    stage_id: int | None
    owner_id: int | None
    email: str | None
    name: str
    first_name: str | None
    last_name: str | None
    phone: str | None
    mobile: str | None
    position: str | None
    department: str | None
    seniority: str | None
    linkedin_url: str | None
    twitter_url: str | None
    source: str | None
    source_id: str | None
    email_verified: bool
    email_verified_at: datetime | None
    score: int
    score_factors: dict | None
    status: str
    is_duplicate: bool
    master_prospect_id: int | None
    duplicate_of_crm_contact: int | None
    crm_contact_id: int | None
    crm_deal_id: int | None
    tags: list[str]
    custom_fields: dict
    enrichment_data: dict | None
    created_at: datetime
    updated_at: datetime
    # Computed fields
    company_name: str | None = None
    stage_name: str | None = None
    owner_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class FunnelProspectListResponse(BaseModel):
    """Schema for funnel prospect list response (lighter)."""

    id: int
    funnel_id: int
    company_id: int | None
    stage_id: int | None
    email: str | None
    name: str
    position: str | None
    linkedin_url: str | None
    score: int
    status: str
    is_duplicate: bool
    tags: list[str]
    company_name: str | None = None
    stage_name: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KanbanStageResponse(BaseModel):
    """Schema for Kanban stage with prospects."""

    id: int
    name: str
    position: int
    color: str
    is_handoff: bool
    is_disqualified: bool
    prospects: list[FunnelProspectListResponse] = []
    prospect_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class KanbanBoardResponse(BaseModel):
    """Schema for full Kanban board response."""

    funnel: FunnelListResponse
    stages: list[KanbanStageResponse]

    model_config = ConfigDict(from_attributes=True)


# ============== Activity Schemas ==============


class FunnelActivityCreate(BaseModel):
    """Schema for creating a funnel activity."""

    activity_type: str = Field(..., min_length=1, max_length=50)
    subject: str | None = None
    content: str | None = None
    channel: str | None = None
    external_id: str | None = None
    external_url: str | None = None
    status: str = "completed"
    activity_date: datetime | None = None
    metadata: dict | None = None


class FunnelActivityResponse(BaseModel):
    """Schema for funnel activity response."""

    id: int
    tenant_id: str
    prospect_id: int
    user_id: int | None
    activity_type: str
    subject: str | None
    content: str | None
    channel: str | None
    external_id: str | None
    external_url: str | None
    status: str
    activity_date: datetime
    metadata: dict | None = None
    user_name: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============== Handoff Schemas ==============


class HandoffInitiateRequest(BaseModel):
    """Schema for initiating a handoff."""

    create_deal: bool = True
    deal_title: str | None = None
    deal_value: float | None = None
    notes: str | None = None


class HandoffRetryRequest(BaseModel):
    """Schema for retrying a failed handoff."""

    pass


class FunnelHandoffResponse(BaseModel):
    """Schema for funnel handoff response."""

    id: int
    tenant_id: str
    funnel_id: int
    prospect_id: int
    company_id: int | None
    status: str
    crm_contact_id: int | None
    crm_company_id: int | None
    crm_deal_id: int | None
    external_crm_type: str | None
    external_crm_contact_id: str | None
    external_crm_deal_id: str | None
    triggered_by: str
    triggered_at: datetime
    completed_at: datetime | None
    error_message: str | None
    retry_count: int
    created_at: datetime
    updated_at: datetime
    # Computed
    prospect_name: str | None = None
    company_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ============== Duplicate Check Schemas ==============


class DuplicateCheckRequest(BaseModel):
    """Schema for checking duplicates."""

    email: EmailStr | None = None
    linkedin_url: str | None = None
    phone: str | None = None


class DuplicateMatch(BaseModel):
    """Schema for a duplicate match."""

    match_type: str  # funnel_prospect, crm_contact
    match_field: str  # email, linkedin, phone
    confidence: float  # 0.0 - 1.0
    # Funnel prospect match
    prospect_id: int | None = None
    prospect_name: str | None = None
    prospect_funnel_id: int | None = None
    prospect_funnel_name: str | None = None
    # CRM contact match
    contact_id: int | None = None
    contact_name: str | None = None
    contact_email: str | None = None


class DuplicateCheckResponse(BaseModel):
    """Schema for duplicate check response."""

    has_duplicates: bool
    matches: list[DuplicateMatch] = []


# ============== Import Schemas ==============


class BulkImportItem(BaseModel):
    """Schema for a single item in bulk import."""

    name: str
    email: EmailStr | None = None
    phone: str | None = None
    position: str | None = None
    company_name: str | None = None
    company_domain: str | None = None
    linkedin_url: str | None = None
    source: str | None = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict = Field(default_factory=dict)


class BulkImportRequest(BaseModel):
    """Schema for bulk import request."""

    items: list[BulkImportItem]
    skip_duplicates: bool = True
    stage_id: int | None = None
    owner_id: int | None = None


class BulkImportResult(BaseModel):
    """Schema for bulk import result."""

    total: int
    imported: int
    skipped: int
    duplicates: int
    errors: list[str] = []
    prospect_ids: list[int] = []


# ============== n8n Schemas ==============


class N8nImportCompany(BaseModel):
    """Schema for n8n company import."""

    name: str
    domain: str | None = None
    website: str | None = None
    industry: str | None = None
    size: str | None = None
    phone: str | None = None
    email: str | None = None
    address: dict | None = None
    source: str | None = None
    source_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict = Field(default_factory=dict)


class N8nImportProspect(BaseModel):
    """Schema for n8n prospect import."""

    name: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    mobile: str | None = None
    position: str | None = None
    department: str | None = None
    seniority: str | None = None
    linkedin_url: str | None = None
    twitter_url: str | None = None
    company_name: str | None = None
    company_domain: str | None = None
    company_id: int | None = None
    stage_id: int | None = None
    source: str | None = None
    source_id: str | None = None
    score: int = 0
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict = Field(default_factory=dict)


class N8nBulkImportRequest(BaseModel):
    """Schema for n8n bulk import."""

    funnel_id: int
    items: list[N8nImportProspect | N8nImportCompany]
    type: str = "prospect"  # prospect or company
    skip_duplicates: bool = True


class N8nEnrichRequest(BaseModel):
    """Schema for n8n enrichment."""

    prospect_id: int
    enrichment_data: dict
    update_fields: bool = True


class N8nActivityRequest(BaseModel):
    """Schema for n8n activity logging."""

    prospect_id: int
    activity_type: str
    subject: str | None = None
    content: str | None = None
    channel: str | None = None
    external_id: str | None = None
    external_url: str | None = None
    activity_date: datetime | None = None
    metadata: dict | None = None


class N8nHandoffTriggerRequest(BaseModel):
    """Schema for n8n handoff trigger."""

    prospect_id: int
    create_deal: bool = True
    deal_title: str | None = None
    deal_value: float | None = None
