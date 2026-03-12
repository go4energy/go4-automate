"""WhatsApp Business schemas - Pydantic models for request/response."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ============== Account Schemas ==============


class WhatsAppAccountBase(BaseModel):
    """Base schema for WhatsApp account."""

    name: str = Field(min_length=1, max_length=200)
    phone_number: str = Field(min_length=10, max_length=20)
    phone_number_id: str = Field(min_length=1, max_length=50)
    waba_id: str = Field(min_length=1, max_length=50)
    daily_limit: int = Field(default=1000, ge=1, le=100000)


class WhatsAppAccountCreate(WhatsAppAccountBase):
    """Schema for creating an account."""

    access_token: str = Field(min_length=1)
    webhook_verify_token: str | None = None


class WhatsAppAccountUpdate(BaseModel):
    """Schema for updating an account."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    daily_limit: int | None = Field(default=None, ge=1, le=100000)
    access_token: str | None = None
    webhook_verify_token: str | None = None
    status: Literal["active", "inactive"] | None = None


class WhatsAppAccountResponse(WhatsAppAccountBase):
    """Schema for account response."""

    id: int
    tenant_id: str
    status: str
    last_error: str | None
    last_verified_at: datetime | None
    messages_sent_today: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WhatsAppAccountListResponse(BaseModel):
    """Schema for account list."""

    id: int
    name: str
    phone_number: str
    status: str
    messages_sent_today: int
    daily_limit: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============== Template Schemas ==============


class WhatsAppTemplateComponent(BaseModel):
    """Template component structure."""

    type: str  # HEADER, BODY, FOOTER, BUTTONS
    format: str | None = None  # TEXT, IMAGE, DOCUMENT, VIDEO
    text: str | None = None
    buttons: list[dict] | None = None


class WhatsAppTemplateResponse(BaseModel):
    """Schema for template response."""

    id: int
    tenant_id: str
    account_id: int
    name: str
    language: str
    category: str
    status: str
    components: list[dict]
    variables: list[str]
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WhatsAppTemplateListResponse(BaseModel):
    """Schema for template list."""

    id: int
    account_id: int
    name: str
    language: str
    category: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WhatsAppTemplatePreviewRequest(BaseModel):
    """Request for template preview."""

    variables: dict = Field(default_factory=dict)


class WhatsAppTemplatePreviewResponse(BaseModel):
    """Response for template preview."""

    name: str
    language: str
    rendered_text: str
    components: list[dict]


# ============== Conversation Schemas ==============


class WhatsAppConversationCreate(BaseModel):
    """Schema for starting a new conversation."""

    account_id: int
    phone: str = Field(min_length=10, max_length=20)
    contact_name: str | None = None
    contact_id: int | None = None


class WhatsAppConversationResponse(BaseModel):
    """Schema for conversation response."""

    id: int
    tenant_id: str
    account_id: int
    contact_id: int | None
    phone: str
    contact_name: str | None
    status: str
    window_expires_at: datetime | None
    last_message_at: datetime | None
    last_message_preview: str | None
    unread_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WhatsAppConversationListResponse(BaseModel):
    """Schema for conversation list."""

    id: int
    account_id: int
    phone: str
    contact_name: str | None
    contact_id: int | None
    status: str
    window_expires_at: datetime | None
    last_message_at: datetime | None
    last_message_preview: str | None
    unread_count: int

    model_config = ConfigDict(from_attributes=True)


class WhatsAppConversationWithMessages(WhatsAppConversationResponse):
    """Conversation with messages."""

    messages: list["WhatsAppMessageResponse"] = []


# ============== Message Schemas ==============


class WhatsAppTextContent(BaseModel):
    """Text message content."""

    body: str = Field(min_length=1, max_length=4096)
    preview_url: bool = False


class WhatsAppMediaContent(BaseModel):
    """Media message content."""

    link: str | None = None
    id: str | None = None  # Media ID from Meta
    caption: str | None = None
    filename: str | None = None


class WhatsAppTemplateContent(BaseModel):
    """Template message content."""

    name: str
    language: str = "de"
    components: list[dict] | None = None


class WhatsAppMessageSend(BaseModel):
    """Schema for sending a message."""

    message_type: Literal["text", "image", "document", "audio", "video", "template"]
    text: WhatsAppTextContent | None = None
    image: WhatsAppMediaContent | None = None
    document: WhatsAppMediaContent | None = None
    audio: WhatsAppMediaContent | None = None
    video: WhatsAppMediaContent | None = None
    template: WhatsAppTemplateContent | None = None


class WhatsAppMessageResponse(BaseModel):
    """Schema for message response."""

    id: int
    conversation_id: int
    direction: str
    message_type: str
    content: dict
    template_name: str | None
    wamid: str | None
    status: str
    error_code: int | None
    error_message: str | None
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============== Campaign Schemas ==============


class WhatsAppCampaignBase(BaseModel):
    """Base schema for campaign."""

    name: str = Field(min_length=1, max_length=200)


class WhatsAppCampaignCreate(WhatsAppCampaignBase):
    """Schema for creating a campaign."""

    account_id: int
    template_id: int
    pipeline_id: int | None = None
    segment_filters: dict | None = None
    contact_ids: list[int] | None = None


class WhatsAppCampaignUpdate(BaseModel):
    """Schema for updating a campaign."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    template_id: int | None = None
    pipeline_id: int | None = None
    segment_filters: dict | None = None
    contact_ids: list[int] | None = None


class WhatsAppCampaignResponse(WhatsAppCampaignBase):
    """Schema for campaign response."""

    id: int
    tenant_id: str
    account_id: int
    template_id: int | None
    pipeline_id: int | None = None
    segment_filters: dict | None
    contact_ids: list[int] | None
    status: str
    scheduled_at: datetime | None
    sent_at: datetime | None
    last_error: str | None
    total_recipients: int
    sent_count: int
    delivered_count: int
    read_count: int
    failed_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WhatsAppCampaignListResponse(BaseModel):
    """Schema for campaign list."""

    id: int
    name: str
    status: str
    total_recipients: int
    sent_count: int
    delivered_count: int
    read_count: int
    failed_count: int
    sent_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WhatsAppCampaignStats(BaseModel):
    """Detailed campaign statistics."""

    total_recipients: int
    sent: int
    delivered: int
    read: int
    failed: int
    delivery_rate: float
    read_rate: float


class CampaignScheduleRequest(BaseModel):
    """Schema for scheduling a campaign."""

    scheduled_at: datetime


class CampaignTemplateVariablesRequest(BaseModel):
    """Schema for setting template variables for recipients."""

    default_variables: dict = Field(default_factory=dict)


# ============== Campaign Recipient Schemas ==============


class WhatsAppCampaignRecipientResponse(BaseModel):
    """Schema for campaign recipient response."""

    id: int
    contact_id: int | None
    phone: str
    contact_name: str | None
    template_variables: dict
    wamid: str | None
    status: str
    error_message: str | None
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class RecipientListParams(BaseModel):
    """Query params for recipient list."""

    status: str | None = None
    search: str | None = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


# ============== Webhook Schemas ==============


class MetaWebhookVerification(BaseModel):
    """Meta webhook verification request."""

    hub_mode: str = Field(alias="hub.mode")
    hub_verify_token: str = Field(alias="hub.verify_token")
    hub_challenge: str = Field(alias="hub.challenge")

    model_config = ConfigDict(populate_by_name=True)


class MetaWebhookMessage(BaseModel):
    """Incoming message from Meta webhook."""

    from_: str = Field(alias="from")
    id: str
    timestamp: str
    type: str
    text: dict | None = None
    image: dict | None = None
    document: dict | None = None
    audio: dict | None = None
    video: dict | None = None
    location: dict | None = None
    contacts: list | None = None
    interactive: dict | None = None
    button: dict | None = None

    model_config = ConfigDict(populate_by_name=True)


class MetaWebhookStatus(BaseModel):
    """Message status update from Meta webhook."""

    id: str
    status: str  # sent, delivered, read, failed
    timestamp: str
    recipient_id: str
    errors: list[dict] | None = None


class MetaWebhookEntry(BaseModel):
    """Webhook entry containing changes."""

    id: str
    changes: list[dict]


class MetaWebhookPayload(BaseModel):
    """Full webhook payload from Meta."""

    object: str
    entry: list[MetaWebhookEntry]


# ============== Dashboard Schemas ==============


class WhatsAppDashboard(BaseModel):
    """Dashboard overview data."""

    total_accounts: int
    active_accounts: int
    total_conversations: int
    open_conversations: int
    total_campaigns: int
    sent_campaigns: int
    messages_sent_24h: int
    messages_received_24h: int
    delivery_rate_7d: float
    read_rate_7d: float


# Rebuild models for forward references
WhatsAppConversationWithMessages.model_rebuild()
