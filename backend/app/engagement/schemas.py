"""Engagement schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ============== Pipeline Schemas ==============


class PipelineCreate(BaseModel):
    """Schema for creating an engagement pipeline."""

    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    product_name: str | None = None
    product_description: str | None = None
    target_audience: str | None = None
    channels: list[str] = Field(default_factory=list)
    goal: str | None = None
    playbook: str | None = None
    tone_of_voice: str = "professionell"
    min_days_between_touches: int = Field(default=3, ge=1, le=30)
    auto_actions: dict = Field(default_factory=dict)
    is_active: bool = True


class PipelineUpdate(BaseModel):
    """Schema for updating an engagement pipeline."""

    name: str | None = Field(None, min_length=1, max_length=200)
    product_name: str | None = None
    product_description: str | None = None
    target_audience: str | None = None
    channels: list[str] | None = None
    goal: str | None = None
    playbook: str | None = None
    tone_of_voice: str | None = None
    min_days_between_touches: int | None = Field(None, ge=1, le=30)
    auto_actions: dict | None = None
    is_active: bool | None = None


class PipelineResponse(BaseModel):
    """Schema for pipeline response."""

    id: int
    tenant_id: str
    name: str
    slug: str
    product_name: str | None
    product_description: str | None
    target_audience: str | None
    channels: list[str]
    goal: str | None
    playbook: str | None
    tone_of_voice: str
    min_days_between_touches: int
    auto_actions: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Computed
    enrollment_count: int = 0
    active_enrollment_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class PipelineListResponse(BaseModel):
    """Schema for pipeline list response (lighter)."""

    id: int
    name: str
    slug: str
    channels: list[str]
    goal: str | None
    is_active: bool
    enrollment_count: int = 0
    active_enrollment_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============== Enrollment Schemas ==============


class EnrollmentCreate(BaseModel):
    """Schema for enrolling a contact in a pipeline."""

    contact_id: int
    pipeline_id: int
    source_module: str | None = None
    source_campaign: str | None = None
    source_context: dict | None = None


class EnrollmentUpdate(BaseModel):
    """Schema for updating an enrollment."""

    stage: str | None = Field(None, pattern=r"^(lead|contacted|engaged|qualified|converted|lost)$")
    status: str | None = Field(None, pattern=r"^(active|paused|completed|stopped)$")
    outcome: str | None = None


class EnrollmentResponse(BaseModel):
    """Schema for enrollment response."""

    id: int
    tenant_id: str
    contact_id: int
    pipeline_id: int
    source_module: str | None
    source_campaign: str | None
    source_context: dict | None
    stage: str
    status: str
    touch_count: int
    last_touch_at: datetime | None
    last_response_at: datetime | None
    outcome: str | None
    enrolled_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # Computed from relationships
    contact_name: str | None = None
    contact_email: str | None = None
    pipeline_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EnrollmentListResponse(BaseModel):
    """Schema for enrollment list response."""

    id: int
    contact_id: int
    pipeline_id: int
    stage: str
    status: str
    touch_count: int
    last_touch_at: datetime | None
    last_response_at: datetime | None
    enrolled_at: datetime
    contact_name: str | None = None
    contact_email: str | None = None
    pipeline_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BulkEnrollRequest(BaseModel):
    """Schema for bulk enrollment."""

    contact_ids: list[int] = Field(..., min_length=1)
    pipeline_id: int
    source_module: str | None = None
    source_campaign: str | None = None


class BulkEnrollResponse(BaseModel):
    """Schema for bulk enrollment response."""

    enrolled: int
    skipped: int
    errors: list[str] = Field(default_factory=list)


# ============== Pending Action Schemas ==============


class PendingActionCreate(BaseModel):
    """Schema for creating a pending action."""

    contact_id: int
    pipeline_id: int
    enrollment_id: int
    module: str = Field(..., min_length=1, max_length=100)
    action_type: str = Field(..., min_length=1, max_length=100)
    context: dict = Field(default_factory=dict)
    suggested_content: str | None = None
    priority: str = Field(default="normal", pattern=r"^(urgent|high|normal|low)$")
    due_at: datetime | None = None
    needs_approval: bool = True


class PendingActionUpdate(BaseModel):
    """Schema for updating a pending action."""

    suggested_content: str | None = None
    priority: str | None = Field(None, pattern=r"^(urgent|high|normal|low)$")
    due_at: datetime | None = None
    status: str | None = Field(
        None, pattern=r"^(pending|ready_for_approval|approved|completed|failed|cancelled)$"
    )


class PendingActionApprove(BaseModel):
    """Schema for approving a pending action."""

    modified_content: str | None = None


class PendingActionComplete(BaseModel):
    """Schema for marking an action as completed."""

    result: dict | None = None
    error_message: str | None = None


class PendingActionResponse(BaseModel):
    """Schema for pending action response."""

    id: int
    tenant_id: str
    contact_id: int
    pipeline_id: int
    enrollment_id: int
    module: str
    action_type: str
    context: dict
    suggested_content: str | None
    priority: str
    due_at: datetime | None
    needs_approval: bool
    status: str
    approved_by: int | None
    approved_at: datetime | None
    result: dict | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
    # Computed
    contact_name: str | None = None
    contact_email: str | None = None
    pipeline_name: str | None = None
    approver_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PendingActionListResponse(BaseModel):
    """Schema for pending action list response."""

    id: int
    contact_id: int
    pipeline_id: int
    module: str
    action_type: str
    priority: str
    due_at: datetime | None
    needs_approval: bool
    status: str
    created_at: datetime
    contact_name: str | None = None
    pipeline_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ============== Contact Activity Schemas ==============


class ActivityCreate(BaseModel):
    """Schema for creating a contact activity."""

    contact_id: int
    pipeline_id: int | None = None
    enrollment_id: int | None = None
    channel: str = Field(
        ..., pattern=r"^(linkedin|email|phone|postmail|whatsapp|meeting|sms|other)$"
    )
    activity_type: str = Field(..., min_length=1, max_length=100)
    direction: str = Field(..., pattern=r"^(outbound|inbound)$")
    subject: str | None = None
    content: str | None = None
    source_module: str | None = None
    source_action_id: int | None = None
    external_id: str | None = None
    sentiment: str | None = Field(None, pattern=r"^(positive|neutral|negative)$")
    detected_intent: str | None = None
    status: str | None = None
    metadata_: dict | None = None
    performed_at: datetime | None = None


class ActivityResponse(BaseModel):
    """Schema for activity response."""

    id: int
    tenant_id: str
    contact_id: int
    pipeline_id: int | None
    enrollment_id: int | None
    channel: str
    activity_type: str
    direction: str
    subject: str | None
    content: str | None
    source_module: str | None
    source_action_id: int | None
    external_id: str | None
    sentiment: str | None
    detected_intent: str | None
    ai_analysis: dict | None
    status: str | None
    metadata_: dict | None
    performed_by: int | None
    performed_at: datetime
    created_at: datetime
    # Computed
    performer_name: str | None = None
    pipeline_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ActivityListResponse(BaseModel):
    """Schema for activity list response (lighter)."""

    id: int
    channel: str
    activity_type: str
    direction: str
    subject: str | None
    status: str | None
    sentiment: str | None
    performed_at: datetime
    performer_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ============== Dashboard / Stats Schemas ==============


class PipelineStats(BaseModel):
    """Statistics for a pipeline."""

    pipeline_id: int
    pipeline_name: str
    total_enrollments: int = 0
    active_enrollments: int = 0
    stage_counts: dict[str, int] = Field(default_factory=dict)
    pending_actions: int = 0
    awaiting_approval: int = 0
    conversion_rate: float = 0.0


class EngagementDashboard(BaseModel):
    """Dashboard data for engagement module."""

    total_pipelines: int = 0
    active_pipelines: int = 0
    total_enrollments: int = 0
    active_enrollments: int = 0
    pending_actions: int = 0
    awaiting_approval: int = 0
    todays_tasks: int = 0
    pipeline_stats: list[PipelineStats] = Field(default_factory=list)
    recent_activities: list[ActivityListResponse] = Field(default_factory=list)


class FunnelStage(BaseModel):
    """Funnel stage for visualization."""

    stage: str
    count: int
    percentage: float


class PipelineFunnel(BaseModel):
    """Funnel data for a pipeline."""

    pipeline_id: int
    pipeline_name: str
    total: int
    stages: list[FunnelStage]


# ============== Brain Schemas ==============


class BrainSetupMessage(BaseModel):
    """Schema for brain setup chat message."""

    message: str
    conversation_history: list[dict] = Field(default_factory=list)


class BrainSetupResponse(BaseModel):
    """Schema for brain setup chat response."""

    message: str
    pipeline_config: dict | None = None


class PrerequisiteItem(BaseModel):
    """Single prerequisite check result."""

    channel: str
    component: str
    status: str  # ready, warning, blocker
    message: str
    action_required: str | None = None


class PrerequisiteReport(BaseModel):
    """Full prerequisite check report."""

    items: list[PrerequisiteItem]
    has_blockers: bool
    has_warnings: bool
    all_ready: bool


class PrerequisiteCheckRequest(BaseModel):
    """Request for checking prerequisites."""

    channels: list[str]


class PlaybookGenerateRequest(BaseModel):
    """Request for generating a playbook."""

    pipeline_config: dict


class PlaybookGenerateResponse(BaseModel):
    """Response with generated playbook."""

    playbook: str


class ModulePromptsGenerateRequest(BaseModel):
    """Request for generating module prompts."""

    pipeline_config: dict


class ModulePromptsGenerateResponse(BaseModel):
    """Response with generated module prompts."""

    prompts: dict[str, str]


class PipelineCreateFromSetup(BaseModel):
    """Schema for creating a pipeline from the setup wizard."""

    pipeline_config: dict
    generate_playbook: bool = True
    generate_module_prompts: bool = True
    check_prerequisites: bool = True


class PipelineCreateFromSetupResponse(BaseModel):
    """Response from creating a pipeline via setup wizard."""

    pipeline: PipelineResponse
    playbook: str | None = None
    module_prompts: dict[str, str] | None = None
    prerequisites: PrerequisiteReport | None = None


class AvailableChannel(BaseModel):
    """Available channel information."""

    id: str
    name: str
    actions: list[str]
    requires_account: bool
    auto_capable: bool


class AvailableChannelsResponse(BaseModel):
    """Response with available channels."""

    channels: list[AvailableChannel]


class ContactAnalyzeRequest(BaseModel):
    """Request to analyze a contact for next action."""

    enrollment_id: int


class ActionRecommendation(BaseModel):
    """Recommendation for next action from the Brain."""

    channel: str
    action: str
    content_suggestion: str | None
    new_stage: str | None
    needs_approval: bool
    reasoning: str


class ResponseAnalyzeRequest(BaseModel):
    """Request to analyze an incoming response."""

    activity_id: int


class ResponseAnalysis(BaseModel):
    """Analysis of an incoming response."""

    sentiment: str
    intent: str
    urgency: str
    new_stage: str | None
    recommended_action: str
    draft_response: str | None
    needs_human: bool
    reasoning: str


# ============== A/B Testing Schemas ==============


class ABTestVariantCreate(BaseModel):
    """Schema for creating an A/B test variant."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    content: str | None = None
    subject: str | None = None
    config: dict = Field(default_factory=dict)
    weight: int = Field(default=50, ge=1, le=100)
    is_control: bool = False


class ABTestVariantResponse(BaseModel):
    """Schema for A/B test variant response."""

    id: int
    ab_test_id: int
    name: str
    description: str | None
    content: str | None
    subject: str | None
    config: dict
    weight: int
    impressions: int
    clicks: int
    conversions: int
    responses: int
    is_control: bool
    created_at: datetime
    updated_at: datetime
    # Computed metrics
    click_rate: float = 0.0
    conversion_rate: float = 0.0
    response_rate: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class ABTestCreate(BaseModel):
    """Schema for creating an A/B test."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    pipeline_id: int
    test_type: str = Field(..., pattern=r"^(message|subject|timing|channel)$")
    channel: str | None = None
    action_type: str | None = None
    sample_size: int | None = None
    variants: list[ABTestVariantCreate] = Field(default_factory=list, min_length=2)


class ABTestUpdate(BaseModel):
    """Schema for updating an A/B test."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    sample_size: int | None = None
    status: str | None = Field(None, pattern=r"^(draft|running|paused|completed)$")
    is_active: bool | None = None


class ABTestResponse(BaseModel):
    """Schema for A/B test response."""

    id: int
    tenant_id: str
    pipeline_id: int
    name: str
    description: str | None
    test_type: str
    channel: str | None
    action_type: str | None
    status: str
    is_active: bool
    sample_size: int | None
    traffic_split: dict
    started_at: datetime | None
    ended_at: datetime | None
    winner_variant_id: int | None
    results_summary: dict | None
    created_at: datetime
    updated_at: datetime
    # Computed
    pipeline_name: str | None = None
    variant_count: int = 0
    total_impressions: int = 0

    model_config = ConfigDict(from_attributes=True)


class ABTestDetailResponse(ABTestResponse):
    """Schema for detailed A/B test response with variants."""

    variants: list[ABTestVariantResponse] = Field(default_factory=list)


class ABTestResultsResponse(BaseModel):
    """Schema for A/B test results."""

    ab_test_id: int
    status: str
    variants: list[ABTestVariantResponse]
    winner: ABTestVariantResponse | None = None
    statistical_significance: float | None = None
    recommendation: str | None = None


# ============== Tracking Link Schemas ==============


class TrackingLinkCreate(BaseModel):
    """Schema for creating a tracking link."""

    contact_id: int
    pipeline_id: int | None = None
    enrollment_id: int | None = None
    target_url: str = Field(..., min_length=1, max_length=2000)
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_content: str | None = None
    utm_term: str | None = None
    expires_at: datetime | None = None


class TrackingLinkBulkCreate(BaseModel):
    """Schema for bulk creating tracking links."""

    contact_ids: list[int] = Field(..., min_length=1)
    pipeline_id: int | None = None
    target_url: str = Field(..., min_length=1, max_length=2000)
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    expires_at: datetime | None = None


class TrackingLinkResponse(BaseModel):
    """Schema for tracking link response."""

    id: int
    tenant_id: str
    contact_id: int
    pipeline_id: int | None
    enrollment_id: int | None
    token: str
    target_url: str
    short_code: str | None
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    utm_content: str | None
    utm_term: str | None
    click_count: int
    first_click_at: datetime | None
    last_click_at: datetime | None
    expires_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Computed
    tracking_url: str | None = None
    contact_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TrackingLinkBulkResponse(BaseModel):
    """Schema for bulk tracking link creation response."""

    created: int
    links: list[TrackingLinkResponse]


class TrackingEventCreate(BaseModel):
    """Schema for creating a tracking event (from pixel)."""

    event: str = Field(..., min_length=1, max_length=100)
    ref: str | None = None  # Token from URL
    url: str | None = None
    referrer: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_content: str | None = None
    timestamp: datetime | None = None
    metadata: dict | None = None


class TrackingEventResponse(BaseModel):
    """Schema for tracking event response."""

    id: int
    tenant_id: str
    tracking_link_id: int | None
    contact_id: int | None
    event_type: str
    url: str | None
    referrer: str | None
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    utm_content: str | None
    device_type: str | None
    event_time: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttributionRecordResponse(BaseModel):
    """Schema for attribution record response."""

    id: int
    tenant_id: str
    contact_id: int
    pipeline_id: int | None
    enrollment_id: int | None
    conversion_type: str
    conversion_value: float | None
    first_touch_channel: str | None
    first_touch_source: str | None
    first_touch_at: datetime | None
    last_touch_channel: str | None
    last_touch_source: str | None
    last_touch_at: datetime | None
    touchpoints: list | None
    touchpoint_count: int
    converted_at: datetime
    created_at: datetime
    # Computed
    contact_name: str | None = None
    pipeline_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AttributionDashboard(BaseModel):
    """Schema for attribution dashboard data."""

    total_conversions: int
    total_value: float
    conversion_by_channel: dict[str, int]
    conversion_by_source: dict[str, int]
    avg_touchpoints: float
    first_touch_attribution: dict[str, int]
    last_touch_attribution: dict[str, int]
    recent_conversions: list[AttributionRecordResponse]


class PixelCodeResponse(BaseModel):
    """Schema for pixel code response."""

    pixel_code: str
    pixel_url: str
    tenant_id: str
