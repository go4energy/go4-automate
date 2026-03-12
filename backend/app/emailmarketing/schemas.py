"""Email Marketing schemas - Pydantic models for request/response."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ============== Provider Schemas ==============


class EmailProviderBase(BaseModel):
    """Base schema for email provider."""

    provider_type: Literal["sendgrid", "mailgun", "o365"]
    sender_email: EmailStr
    sender_name: str = Field(min_length=1, max_length=200)
    reply_to_email: EmailStr | None = None
    tracking_domain: str | None = None
    hourly_limit: int = Field(default=500, ge=1, le=100000)
    daily_limit: int = Field(default=10000, ge=1, le=1000000)


class EmailProviderCreate(EmailProviderBase):
    """Schema for creating a provider."""

    api_key: str = Field(min_length=1)  # Will be encrypted


class EmailProviderUpdate(BaseModel):
    """Schema for updating a provider."""

    sender_email: EmailStr | None = None
    sender_name: str | None = Field(default=None, min_length=1, max_length=200)
    reply_to_email: EmailStr | None = None
    tracking_domain: str | None = None
    hourly_limit: int | None = Field(default=None, ge=1, le=100000)
    daily_limit: int | None = Field(default=None, ge=1, le=1000000)
    api_key: str | None = None  # Only update if provided
    status: Literal["active", "inactive"] | None = None


class EmailProviderResponse(EmailProviderBase):
    """Schema for provider response."""

    id: int
    tenant_id: str
    status: str
    last_error: str | None
    last_verified_at: datetime | None
    emails_sent_today: int
    emails_sent_hour: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmailProviderListResponse(BaseModel):
    """Schema for provider list."""

    id: int
    provider_type: str
    sender_email: str
    sender_name: str
    status: str
    emails_sent_today: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============== Template Schemas ==============


class EmailTemplateBase(BaseModel):
    """Base schema for email template."""

    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    subject: str = Field(min_length=1, max_length=500)
    html_content: str = Field(min_length=1)
    text_content: str | None = None
    variables: list[str] = Field(default_factory=list)
    category: str | None = None
    tags: list[str] = Field(default_factory=list)


class EmailTemplateCreate(EmailTemplateBase):
    """Schema for creating a template."""

    pass


class EmailTemplateUpdate(BaseModel):
    """Schema for updating a template."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    subject: str | None = Field(default=None, min_length=1, max_length=500)
    html_content: str | None = None
    text_content: str | None = None
    variables: list[str] | None = None
    is_active: bool | None = None
    category: str | None = None
    tags: list[str] | None = None


class EmailTemplateResponse(EmailTemplateBase):
    """Schema for template response."""

    id: int
    tenant_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmailTemplateListResponse(BaseModel):
    """Schema for template list."""

    id: int
    name: str
    slug: str
    subject: str
    category: str | None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmailTemplatePreview(BaseModel):
    """Schema for template preview request."""

    html_content: str
    merge_data: dict = Field(default_factory=dict)


# ============== Campaign Schemas ==============


class EmailCampaignBase(BaseModel):
    """Base schema for email campaign."""

    name: str = Field(min_length=1, max_length=200)
    subject: str = Field(min_length=1, max_length=500)
    html_content: str = Field(min_length=1)
    text_content: str | None = None


class EmailCampaignCreate(EmailCampaignBase):
    """Schema for creating a campaign."""

    provider_id: int | None = None
    template_id: int | None = None
    pipeline_id: int | None = None
    segment_filters: dict | None = None  # {"tags": ["lead"], "source": "website"}
    contact_ids: list[int] | None = None
    # A/B Testing
    ab_test_enabled: bool = False
    ab_variant_b_subject: str | None = None
    ab_variant_b_html: str | None = None
    ab_split_percentage: int = Field(default=50, ge=10, le=90)
    ab_winner_metric: Literal["open_rate", "click_rate"] = "open_rate"


class EmailCampaignUpdate(BaseModel):
    """Schema for updating a campaign."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    subject: str | None = Field(default=None, min_length=1, max_length=500)
    html_content: str | None = None
    text_content: str | None = None
    provider_id: int | None = None
    template_id: int | None = None
    pipeline_id: int | None = None
    segment_filters: dict | None = None
    contact_ids: list[int] | None = None
    # A/B Testing
    ab_test_enabled: bool | None = None
    ab_variant_b_subject: str | None = None
    ab_variant_b_html: str | None = None
    ab_split_percentage: int | None = Field(default=None, ge=10, le=90)
    ab_winner_metric: Literal["open_rate", "click_rate"] | None = None


class EmailCampaignResponse(EmailCampaignBase):
    """Schema for campaign response."""

    id: int
    tenant_id: str
    provider_id: int | None
    template_id: int | None
    pipeline_id: int | None = None
    segment_filters: dict | None
    contact_ids: list[int] | None
    status: str
    scheduled_at: datetime | None
    sent_at: datetime | None
    last_error: str | None
    # Stats
    total_recipients: int
    sent_count: int
    delivered_count: int
    opened_count: int
    clicked_count: int
    bounced_count: int
    unsubscribed_count: int
    spam_count: int
    # A/B Testing
    ab_test_enabled: bool
    ab_variant_b_subject: str | None
    ab_variant_b_html: str | None
    ab_split_percentage: int
    ab_winner_metric: str
    ab_winner_variant: str | None
    ab_a_sent: int
    ab_a_opened: int
    ab_a_clicked: int
    ab_b_sent: int
    ab_b_opened: int
    ab_b_clicked: int
    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmailCampaignListResponse(BaseModel):
    """Schema for campaign list."""

    id: int
    name: str
    subject: str
    status: str
    total_recipients: int
    sent_count: int
    opened_count: int
    clicked_count: int
    sent_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignStats(BaseModel):
    """Detailed campaign statistics."""

    total_recipients: int
    sent: int
    delivered: int
    opened: int
    clicked: int
    bounced: int
    unsubscribed: int
    spam: int
    open_rate: float
    click_rate: float
    bounce_rate: float
    # A/B Stats
    ab_test_enabled: bool = False
    ab_a_sent: int = 0
    ab_a_opened: int = 0
    ab_a_clicked: int = 0
    ab_a_open_rate: float = 0.0
    ab_a_click_rate: float = 0.0
    ab_b_sent: int = 0
    ab_b_opened: int = 0
    ab_b_clicked: int = 0
    ab_b_open_rate: float = 0.0
    ab_b_click_rate: float = 0.0
    ab_winner_variant: str | None = None


class CampaignScheduleRequest(BaseModel):
    """Schema for scheduling a campaign."""

    scheduled_at: datetime


class CampaignTestRequest(BaseModel):
    """Schema for sending a test email."""

    to: EmailStr
    merge_data: dict = Field(default_factory=dict)


# ============== Recipient Schemas ==============


class EmailRecipientResponse(BaseModel):
    """Schema for recipient response."""

    id: int
    email: str
    name: str | None
    status: str
    sent_at: datetime | None
    opened_at: datetime | None
    clicked_at: datetime | None
    bounced_at: datetime | None
    contact_id: int | None

    model_config = ConfigDict(from_attributes=True)


class RecipientListParams(BaseModel):
    """Query params for recipient list."""

    status: str | None = None
    search: str | None = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


# ============== Sequence Schemas ==============


class EmailSequenceBase(BaseModel):
    """Base schema for email sequence."""

    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    trigger_type: Literal["manual", "tag_added", "contact_created"] = "manual"
    trigger_filters: dict | None = None
    send_window_start: str | None = Field(
        default=None, pattern=r"^([01]\d|2[0-3]):([0-5]\d)$"
    )
    send_window_end: str | None = Field(
        default=None, pattern=r"^([01]\d|2[0-3]):([0-5]\d)$"
    )
    skip_weekends: bool = True
    timezone: str = "Europe/Berlin"


class EmailSequenceCreate(EmailSequenceBase):
    """Schema for creating a sequence."""

    provider_id: int | None = None
    pipeline_id: int | None = None


class EmailSequenceUpdate(BaseModel):
    """Schema for updating a sequence."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    provider_id: int | None = None
    pipeline_id: int | None = None
    trigger_type: Literal["manual", "tag_added", "contact_created"] | None = None
    trigger_filters: dict | None = None
    send_window_start: str | None = None
    send_window_end: str | None = None
    skip_weekends: bool | None = None
    timezone: str | None = None


class EmailSequenceResponse(EmailSequenceBase):
    """Schema for sequence response."""

    id: int
    tenant_id: str
    provider_id: int | None
    pipeline_id: int | None = None
    status: str
    total_enrolled: int
    total_completed: int
    total_unsubscribed: int
    created_at: datetime
    updated_at: datetime
    steps: list["EmailSequenceStepResponse"] = []

    model_config = ConfigDict(from_attributes=True)


class EmailSequenceListResponse(BaseModel):
    """Schema for sequence list."""

    id: int
    name: str
    trigger_type: str
    status: str
    total_enrolled: int
    total_completed: int
    step_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============== Sequence Step Schemas ==============


class EmailSequenceStepBase(BaseModel):
    """Base schema for sequence step."""

    position: int = Field(ge=0)
    delay_days: int = Field(default=1, ge=0)
    delay_hours: int = Field(default=0, ge=0, le=23)
    subject: str = Field(min_length=1, max_length=500)
    html_content: str = Field(min_length=1)
    text_content: str | None = None
    send_if_opened_previous: bool | None = None
    send_if_clicked_previous: bool | None = None


class EmailSequenceStepCreate(EmailSequenceStepBase):
    """Schema for creating a sequence step."""

    template_id: int | None = None


class EmailSequenceStepUpdate(BaseModel):
    """Schema for updating a sequence step."""

    position: int | None = Field(default=None, ge=0)
    delay_days: int | None = Field(default=None, ge=0)
    delay_hours: int | None = Field(default=None, ge=0, le=23)
    subject: str | None = Field(default=None, min_length=1, max_length=500)
    html_content: str | None = None
    text_content: str | None = None
    template_id: int | None = None
    send_if_opened_previous: bool | None = None
    send_if_clicked_previous: bool | None = None


class EmailSequenceStepResponse(EmailSequenceStepBase):
    """Schema for sequence step response."""

    id: int
    sequence_id: int
    template_id: int | None
    sent_count: int
    opened_count: int
    clicked_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============== Enrollment Schemas ==============


class EnrollContactsRequest(BaseModel):
    """Schema for enrolling contacts in a sequence."""

    contact_ids: list[int] = Field(min_length=1)


class EmailEnrollmentResponse(BaseModel):
    """Schema for enrollment response."""

    id: int
    contact_id: int
    contact_name: str | None
    contact_email: str
    current_step: int
    status: str
    next_send_at: datetime | None
    enrolled_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class EnrollmentListParams(BaseModel):
    """Query params for enrollment list."""

    status: str | None = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


# ============== Unsubscribe Schemas ==============


class EmailUnsubscribeResponse(BaseModel):
    """Schema for unsubscribe response."""

    id: int
    email: str
    reason: str
    source_type: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnsubscribeListParams(BaseModel):
    """Query params for unsubscribe list."""

    search: str | None = None
    reason: str | None = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


# ============== Webhook Schemas ==============


class SendGridWebhookEvent(BaseModel):
    """SendGrid webhook event."""

    event: str  # delivered, bounce, open, click, spamreport, unsubscribe
    email: str
    timestamp: int
    sg_message_id: str | None = None
    url: str | None = None  # For click events
    ip: str | None = None
    useragent: str | None = None


class MailgunWebhookEvent(BaseModel):
    """Mailgun webhook event."""

    event: str  # delivered, bounced, opened, clicked, complained, unsubscribed
    recipient: str
    timestamp: float
    message_id: str | None = Field(default=None, alias="Message-Id")
    url: str | None = None
    ip: str | None = None
    user_agent: str | None = Field(default=None, alias="user-agent")

    model_config = ConfigDict(populate_by_name=True)


# ============== Dashboard Schemas ==============


class EmailMarketingDashboard(BaseModel):
    """Dashboard overview data."""

    total_campaigns: int
    sent_campaigns: int
    draft_campaigns: int
    total_sequences: int
    active_sequences: int
    total_templates: int
    total_providers: int
    active_providers: int
    emails_sent_30d: int
    open_rate_30d: float
    click_rate_30d: float
    unsubscribes_30d: int


# Rebuild models for forward references
EmailSequenceResponse.model_rebuild()
