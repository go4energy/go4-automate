"""LinkedIn schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ============== Account Schemas ==============


class LinkedInAccountCreate(BaseModel):
    """Schema for creating a LinkedIn account."""

    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    password: str | None = Field(None, min_length=1)
    is_sales_navigator: bool = False
    daily_profile_limit: int = Field(100, ge=1, le=500)
    daily_connection_limit: int = Field(25, ge=1, le=100)
    daily_message_limit: int = Field(50, ge=1, le=150)
    warmup_enabled: bool = True


class LinkedInAccountUpdate(BaseModel):
    """Schema for updating a LinkedIn account."""

    name: str | None = Field(None, min_length=1, max_length=200)
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=1)
    is_sales_navigator: bool | None = None
    daily_profile_limit: int | None = Field(None, ge=1, le=500)
    daily_connection_limit: int | None = Field(None, ge=1, le=100)
    daily_message_limit: int | None = Field(None, ge=1, le=150)
    warmup_enabled: bool | None = None
    status: str | None = None


class LinkedInAccountResponse(BaseModel):
    """Schema for LinkedIn account response."""

    id: int
    tenant_id: str
    name: str
    email: str
    status: str
    is_sales_navigator: bool
    daily_profile_limit: int
    daily_connection_limit: int
    daily_message_limit: int
    profiles_scraped_today: int
    connections_sent_today: int
    messages_sent_today: int
    total_profiles_scraped: int
    warmup_enabled: bool
    warmup_day: int
    last_login_at: datetime | None
    last_scrape_date: datetime | None
    last_error: str | None
    session_expires_at: datetime | None
    has_valid_session: bool = False
    effective_limits: dict | None = None
    job_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LinkedInAccountListResponse(BaseModel):
    """Schema for LinkedIn account list response (lighter)."""

    id: int
    name: str
    email: str
    status: str
    is_sales_navigator: bool
    profiles_scraped_today: int
    connections_sent_today: int
    messages_sent_today: int
    daily_profile_limit: int
    daily_connection_limit: int
    daily_message_limit: int
    warmup_enabled: bool
    warmup_day: int
    last_login_at: datetime | None
    has_valid_session: bool = False
    job_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============== Scraper Job Schemas ==============


class LinkedInJobCreate(BaseModel):
    """Schema for creating a LinkedIn scraper job."""

    name: str = Field(..., min_length=1, max_length=200)
    account_id: int
    funnel_id: int | None = None
    pipeline_id: int | None = None
    job_type: str = "search"  # search, profile_list, connections
    search_url: str | None = None
    profile_urls: list[str] | None = None
    connections_since_date: datetime | None = None
    max_profiles: int = Field(100, ge=1, le=2500)
    daily_limit: int = Field(50, ge=1, le=10000)
    min_delay_seconds: int = Field(5, ge=1, le=300)
    scrape_full_profiles: bool = False
    auto_import: bool = False
    import_stage_id: int | None = None
    auto_enroll_pipeline: bool = False
    schedule_enabled: bool = False
    schedule_days: list[int] | None = None
    schedule_start_time: str | None = None
    schedule_end_time: str | None = None
    max_pages_per_run: int = Field(10, ge=1, le=50)


class LinkedInJobUpdate(BaseModel):
    """Schema for updating a LinkedIn scraper job."""

    name: str | None = Field(None, min_length=1, max_length=200)
    funnel_id: int | None = None
    pipeline_id: int | None = None
    search_url: str | None = None
    profile_urls: list[str] | None = None
    max_profiles: int | None = Field(None, ge=1, le=2500)
    profiles_scraped: int | None = Field(None, ge=0)
    daily_limit: int | None = Field(None, ge=1, le=10000)
    min_delay_seconds: int | None = Field(None, ge=1, le=300)
    scrape_full_profiles: bool | None = None
    auto_import: bool | None = None
    import_stage_id: int | None = None
    auto_enroll_pipeline: bool | None = None
    schedule_enabled: bool | None = None
    schedule_days: list[int] | None = None
    schedule_start_time: str | None = None
    schedule_end_time: str | None = None
    max_pages_per_run: int | None = Field(None, ge=1, le=50)
    connections_since_date: datetime | None = None


class LinkedInJobResponse(BaseModel):
    """Schema for LinkedIn scraper job response."""

    id: int
    tenant_id: str
    account_id: int
    funnel_id: int | None
    pipeline_id: int | None = None
    name: str
    job_type: str
    search_url: str | None
    profile_urls: list[str] | None
    max_profiles: int
    daily_limit: int
    min_delay_seconds: int
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    profiles_found: int
    profiles_scraped: int
    profiles_failed: int
    current_page: int
    error_message: str | None
    retry_count: int
    scrape_full_profiles: bool
    auto_import: bool
    import_stage_id: int | None
    auto_enroll_pipeline: bool = False
    schedule_enabled: bool
    schedule_days: list[int] | None
    schedule_start_time: str | None
    schedule_end_time: str | None
    max_pages_per_run: int
    connections_since_date: datetime | None = None
    account_name: str | None = None
    funnel_name: str | None = None
    pipeline_name: str | None = None
    import_stage_name: str | None = None
    progress_percent: float = 0.0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LinkedInJobListResponse(BaseModel):
    """Schema for LinkedIn scraper job list response (lighter)."""

    id: int
    account_id: int
    funnel_id: int | None
    pipeline_id: int | None = None
    name: str
    job_type: str
    status: str
    profiles_found: int
    profiles_scraped: int
    profiles_failed: int
    max_profiles: int
    current_page: int
    schedule_enabled: bool
    max_pages_per_run: int
    connections_since_date: datetime | None = None
    auto_enroll_pipeline: bool = False
    progress_percent: float = 0.0
    account_name: str | None = None
    funnel_name: str | None = None
    pipeline_name: str | None = None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============== Contact Schemas ==============


class LinkedInContactResponse(BaseModel):
    """Schema for LinkedIn contact response."""

    id: int
    tenant_id: str
    scraper_job_id: int
    linkedin_url: str
    linkedin_id: str | None
    sales_navigator_url: str | None
    name: str
    first_name: str | None
    last_name: str | None
    headline: str | None
    position: str | None
    location: str | None
    profile_picture_url: str | None
    contact_degree: int | None
    is_premium: bool
    gender: str | None
    is_followed: bool
    follower_count: int | None
    connection_count: int | None
    website: str | None
    company_name: str | None
    company_linkedin_url: str | None
    company_size: str | None
    company_industry: str | None
    email: str | None
    phone: str | None
    twitter_url: str | None
    summary: str | None
    connected_at: datetime | None = None
    connected_at_text: str | None = None
    experience: list | None
    education: list | None
    skills: list | None
    languages: list | None
    interests: dict | None = None
    profile_urn: str | None = None
    status: str
    excluded: bool = False
    funnel_prospect_id: int | None
    funnel_company_id: int | None
    imported_at: datetime | None
    scrape_error: str | None
    central_contact_id: int | None = None
    raw_data: dict | None = None
    pipeline_count: int = 0
    pipelines: list[dict] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LinkedInContactListResponse(BaseModel):
    """Schema for LinkedIn contact list response (lighter)."""

    id: int
    scraper_job_id: int
    linkedin_url: str
    name: str
    headline: str | None
    position: str | None
    company_name: str | None
    location: str | None
    contact_degree: int | None
    is_premium: bool
    gender: str | None
    status: str
    excluded: bool = False
    central_contact_id: int | None = None
    pipeline_count: int = 0
    imported_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============== Import Schemas ==============


class LinkedInImportRequest(BaseModel):
    """Schema for importing LinkedIn contacts to funnel."""

    contact_ids: list[int] | None = None
    funnel_id: int
    stage_id: int | None = None
    skip_duplicates: bool = True
    create_companies: bool = True


class LinkedInImportResult(BaseModel):
    """Schema for import result."""

    total: int
    imported: int
    skipped: int
    duplicates: int
    companies_created: int
    errors: list[str] = []
    prospect_ids: list[int] = []


# ============== Manual URL Import Schemas ==============


class LinkedInManualUrlImport(BaseModel):
    """Schema for manually importing profile URLs."""

    urls: list[str] = Field(..., min_length=1, max_length=100)


class LinkedInManualUrlImportResult(BaseModel):
    """Schema for manual URL import result."""

    total: int
    added: int
    duplicates: int
    invalid: int
    errors: list[str] = []


# ============== Login/Session Schemas ==============


class LinkedInLoginRequest(BaseModel):
    """Schema for initiating browser login."""

    headless: bool = False


class LinkedInLoginResponse(BaseModel):
    """Schema for login response."""

    status: str
    message: str | None = None
    session_valid_until: datetime | None = None


class LinkedInSessionVerifyResponse(BaseModel):
    """Schema for session verification response."""

    valid: bool
    expires_at: datetime | None
    is_sales_navigator: bool = False
    profile_name: str | None = None


class LinkedInSessionImport(BaseModel):
    """Schema for importing browser session/cookies."""

    cookies: list[dict] | None = None
    storage_state: dict | None = None


class LinkedInSessionImportResponse(BaseModel):
    """Schema for session import response."""

    success: bool
    message: str
    session_expires_at: datetime | None = None


class LinkedInJobStartResponse(BaseModel):
    """Schema for job start response."""

    status: str
    message: str
    job_id: int


class LinkedInAutoLoginRequest(BaseModel):
    """Schema for auto-login request."""

    password: str | None = None
    wait_for_2fa_timeout: int = 300


class LinkedInAutoLoginResponse(BaseModel):
    """Schema for auto-login response."""

    success: bool
    message: str
    session_expires_at: datetime | None = None
    needs_manual_intervention: bool = False


class LinkedInSetPasswordRequest(BaseModel):
    """Schema for setting account password."""

    password: str


# ============== Stats Schemas ==============


class LinkedInStats(BaseModel):
    """Schema for LinkedIn module statistics."""

    accounts_total: int = 0
    accounts_active: int = 0
    jobs_total: int = 0
    jobs_running: int = 0
    jobs_completed: int = 0
    contacts_scraped: int = 0
    contacts_imported: int = 0
    profiles_today: int = 0
    daily_limit_remaining: int = 0
    # New stats
    connections_sent_today: int = 0
    connections_pending: int = 0
    connections_accepted: int = 0
    messages_sent_today: int = 0
    campaigns_active: int = 0
    templates_total: int = 0


# ============== Job Log Schemas ==============


class LinkedInJobLogResponse(BaseModel):
    """Schema for LinkedIn job log response."""

    id: int
    job_id: int
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: int | None
    start_page: int
    end_page: int | None
    profiles_scraped: int
    profiles_failed: int
    profiles_skipped: int
    status: str
    error_message: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LinkedInJobLogListResponse(BaseModel):
    """Schema for LinkedIn job log list response (lighter)."""

    id: int
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: int | None
    start_page: int
    end_page: int | None
    profiles_scraped: int
    profiles_failed: int
    profiles_skipped: int
    status: str
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)


# ============== MESSAGE TEMPLATE SCHEMAS ==============


class LinkedInTemplateCreate(BaseModel):
    """Schema for creating a message template."""

    name: str = Field(..., min_length=1, max_length=200)
    category: str = "general"  # connection_request, first_message, follow_up, inmail
    subject: str | None = Field(None, max_length=200)
    content: str = Field(..., min_length=1)
    variables: list[str] | None = None
    variant_of_id: int | None = None
    variant_name: str | None = None


class LinkedInTemplateUpdate(BaseModel):
    """Schema for updating a message template."""

    name: str | None = Field(None, min_length=1, max_length=200)
    category: str | None = None
    subject: str | None = Field(None, max_length=200)
    content: str | None = None
    variables: list[str] | None = None
    is_active: bool | None = None


class LinkedInTemplateResponse(BaseModel):
    """Schema for message template response."""

    id: int
    tenant_id: str
    name: str
    category: str
    subject: str | None
    content: str
    variables: list[str] | None
    variant_of_id: int | None
    variant_name: str | None
    times_used: int
    responses_received: int
    response_rate: float = 0.0
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LinkedInTemplateListResponse(BaseModel):
    """Schema for template list response (lighter)."""

    id: int
    name: str
    category: str
    times_used: int
    responses_received: int
    response_rate: float = 0.0
    is_active: bool
    variant_of_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LinkedInTemplatePreview(BaseModel):
    """Schema for previewing a rendered template."""

    template_id: int
    context: dict = {}


class LinkedInTemplatePreviewResponse(BaseModel):
    """Schema for template preview response."""

    rendered_content: str
    rendered_subject: str | None = None


# ============== CONNECTION SCHEMAS ==============


class LinkedInConnectionCreate(BaseModel):
    """Schema for creating a connection request."""

    account_id: int
    linkedin_url: str
    profile_name: str
    profile_headline: str | None = None
    profile_picture_url: str | None = None
    message: str | None = Field(None, max_length=300)
    template_id: int | None = None
    contact_id: int | None = None
    campaign_id: int | None = None


class LinkedInConnectionResponse(BaseModel):
    """Schema for connection response."""

    id: int
    tenant_id: str
    account_id: int
    contact_id: int | None
    linkedin_url: str
    linkedin_id: str | None
    profile_name: str
    profile_headline: str | None
    profile_picture_url: str | None
    message: str | None
    template_id: int | None
    status: str
    sent_at: datetime | None
    accepted_at: datetime | None
    withdrawn_at: datetime | None
    error_message: str | None
    campaign_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LinkedInConnectionListResponse(BaseModel):
    """Schema for connection list response."""

    id: int
    account_id: int
    linkedin_url: str
    profile_name: str
    profile_headline: str | None
    status: str
    sent_at: datetime | None
    accepted_at: datetime | None
    campaign_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LinkedInConnectionBulkCreate(BaseModel):
    """Schema for bulk creating connection requests."""

    account_id: int
    contact_ids: list[int] = Field(..., min_length=1, max_length=100)
    message: str | None = Field(None, max_length=300)
    template_id: int | None = None
    campaign_id: int | None = None


class LinkedInConnectionBulkResult(BaseModel):
    """Schema for bulk connection result."""

    total: int
    created: int
    skipped: int
    errors: list[str] = []


# ============== MESSAGE SCHEMAS ==============


class LinkedInMessageCreate(BaseModel):
    """Schema for creating a direct message."""

    account_id: int
    linkedin_url: str
    profile_name: str
    content: str = Field(..., min_length=1)
    subject: str | None = Field(None, max_length=200)
    message_type: str = "direct"  # direct, inmail, follow_up
    template_id: int | None = None
    contact_id: int | None = None
    connection_id: int | None = None
    campaign_id: int | None = None


class LinkedInMessageResponse(BaseModel):
    """Schema for message response."""

    id: int
    tenant_id: str
    account_id: int
    contact_id: int | None
    connection_id: int | None
    conversation_id: str | None
    linkedin_url: str
    profile_name: str
    message_type: str
    subject: str | None
    content: str
    template_id: int | None
    direction: str
    status: str
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None
    replied_at: datetime | None
    error_message: str | None
    campaign_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LinkedInMessageListResponse(BaseModel):
    """Schema for message list response."""

    id: int
    account_id: int
    linkedin_url: str
    profile_name: str
    message_type: str
    direction: str
    content_preview: str  # First 100 chars
    status: str
    sent_at: datetime | None
    replied_at: datetime | None
    campaign_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LinkedInInboxResponse(BaseModel):
    """Schema for inbox conversation."""

    conversation_id: str | None
    linkedin_url: str
    profile_name: str
    profile_picture_url: str | None
    last_message_content: str
    last_message_direction: str
    last_message_at: datetime
    unread_count: int = 0
    messages: list[LinkedInMessageResponse] = []


# ============== CAMPAIGN SCHEMAS ==============


class LinkedInCampaignStepCreate(BaseModel):
    """Schema for creating a campaign step."""

    name: str = Field(..., min_length=1, max_length=200)
    order: int
    step_type: str  # connect, message, inmail, view_profile, follow, wait, condition
    wait_days: int | None = None
    wait_hours: int | None = None
    template_id: int | None = None
    template_ids: list[int] | None = None
    ab_test_enabled: bool = False
    condition_type: str | None = None
    condition_true_step_id: int | None = None
    condition_false_step_id: int | None = None


class LinkedInCampaignStepResponse(BaseModel):
    """Schema for campaign step response."""

    id: int
    campaign_id: int
    name: str
    order: int
    step_type: str
    wait_days: int | None
    wait_hours: int | None
    template_id: int | None
    template_ids: list[int] | None
    ab_test_enabled: bool
    condition_type: str | None
    condition_true_step_id: int | None
    condition_false_step_id: int | None
    leads_entered: int
    leads_completed: int
    leads_failed: int
    is_active: bool
    template_name: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LinkedInCampaignCreate(BaseModel):
    """Schema for creating a campaign."""

    name: str = Field(..., min_length=1, max_length=200)
    account_id: int
    pipeline_id: int | None = None
    description: str | None = None
    timezone: str = "Europe/Berlin"
    daily_connection_limit: int | None = None
    daily_message_limit: int | None = None
    schedule_days: list[int] | None = None
    schedule_start_time: str | None = None
    schedule_end_time: str | None = None
    stop_on_reply: bool = True
    stop_on_connect: bool = False
    steps: list[LinkedInCampaignStepCreate] | None = None


class LinkedInCampaignUpdate(BaseModel):
    """Schema for updating a campaign."""

    name: str | None = Field(None, min_length=1, max_length=200)
    pipeline_id: int | None = None
    description: str | None = None
    status: str | None = None
    timezone: str | None = None
    daily_connection_limit: int | None = None
    daily_message_limit: int | None = None
    schedule_days: list[int] | None = None
    schedule_start_time: str | None = None
    schedule_end_time: str | None = None
    stop_on_reply: bool | None = None
    stop_on_connect: bool | None = None


class LinkedInCampaignResponse(BaseModel):
    """Schema for campaign response."""

    id: int
    tenant_id: str
    account_id: int
    pipeline_id: int | None = None
    name: str
    description: str | None
    status: str
    timezone: str
    daily_connection_limit: int | None
    daily_message_limit: int | None
    schedule_days: list[int] | None
    schedule_start_time: str | None
    schedule_end_time: str | None
    stop_on_reply: bool
    stop_on_connect: bool
    total_leads: int
    leads_completed: int
    leads_active: int
    connections_sent: int
    connections_accepted: int
    messages_sent: int
    replies_received: int
    connection_rate: float = 0.0
    reply_rate: float = 0.0
    started_at: datetime | None
    completed_at: datetime | None
    account_name: str | None = None
    steps: list[LinkedInCampaignStepResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LinkedInCampaignListResponse(BaseModel):
    """Schema for campaign list response."""

    id: int
    account_id: int
    name: str
    status: str
    total_leads: int
    leads_active: int
    leads_completed: int
    connections_sent: int
    connections_accepted: int
    messages_sent: int
    replies_received: int
    connection_rate: float = 0.0
    reply_rate: float = 0.0
    account_name: str | None = None
    started_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LinkedInCampaignLeadCreate(BaseModel):
    """Schema for adding a lead to campaign."""

    linkedin_url: str
    profile_name: str
    profile_headline: str | None = None
    company_name: str | None = None
    profile_picture_url: str | None = None
    contact_id: int | None = None
    custom_variables: dict | None = None


class LinkedInCampaignLeadBulkCreate(BaseModel):
    """Schema for bulk adding leads from contacts."""

    contact_ids: list[int] = Field(..., min_length=1, max_length=500)
    custom_variables: dict | None = None


class LinkedInCampaignLeadResponse(BaseModel):
    """Schema for campaign lead response."""

    id: int
    campaign_id: int
    contact_id: int | None
    linkedin_url: str
    linkedin_id: str | None
    profile_name: str
    profile_headline: str | None
    company_name: str | None
    profile_picture_url: str | None
    custom_variables: dict | None
    current_step_id: int | None
    current_step_order: int
    status: str
    connection_status: str | None
    has_replied: bool
    reply_received_at: datetime | None
    entered_campaign_at: datetime
    next_action_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    ab_variant: str | None
    current_step_name: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LinkedInCampaignLeadListResponse(BaseModel):
    """Schema for campaign lead list response."""

    id: int
    linkedin_url: str
    profile_name: str
    company_name: str | None
    status: str
    connection_status: str | None
    has_replied: bool
    current_step_order: int
    current_step_name: str | None = None
    next_action_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LinkedInCampaignLeadBulkResult(BaseModel):
    """Schema for bulk lead add result."""

    total: int
    added: int
    skipped: int
    duplicates: int
    errors: list[str] = []


# ============== ACTION SCHEMAS ==============


class LinkedInSendConnectionRequest(BaseModel):
    """Schema for sending a connection request immediately."""

    account_id: int
    linkedin_url: str
    message: str | None = Field(None, max_length=300)
    template_id: int | None = None


class LinkedInSendMessageRequest(BaseModel):
    """Schema for sending a message immediately."""

    account_id: int
    linkedin_url: str
    content: str = Field(..., min_length=1)
    subject: str | None = None
    template_id: int | None = None


class LinkedInActionResponse(BaseModel):
    """Schema for action response."""

    success: bool
    message: str
    connection_id: int | None = None
    message_id: int | None = None


# ============== ANALYTICS SCHEMAS ==============


class LinkedInCampaignAnalytics(BaseModel):
    """Schema for campaign analytics."""

    campaign_id: int
    campaign_name: str
    total_leads: int
    leads_by_status: dict[str, int] = {}
    connections_sent: int
    connections_accepted: int
    connections_declined: int
    connection_rate: float
    messages_sent: int
    messages_opened: int
    replies_received: int
    reply_rate: float
    step_analytics: list[dict] = []
    daily_activity: list[dict] = []


class LinkedInAccountAnalytics(BaseModel):
    """Schema for account analytics."""

    account_id: int
    account_name: str
    period_days: int = 30
    profiles_scraped: int
    connections_sent: int
    connections_accepted: int
    connection_rate: float
    messages_sent: int
    replies_received: int
    reply_rate: float
    daily_activity: list[dict] = []
    warmup_progress: float = 0.0
