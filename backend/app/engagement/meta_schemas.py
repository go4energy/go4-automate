"""
Meta Integration Schemas

Pydantic schemas for Meta Conversions API endpoints.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

# ============== Enums ==============


class EventStatus(str, Enum):
    """Status of a conversion event."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    TEST = "test"


class EventName(str, Enum):
    """Standard Meta conversion event names."""

    PAGE_VIEW = "PageView"
    LEAD = "Lead"
    CONTACT = "Contact"
    PURCHASE = "Purchase"
    VIEW_CONTENT = "ViewContent"
    COMPLETE_REGISTRATION = "CompleteRegistration"
    ADD_TO_CART = "AddToCart"
    INITIATE_CHECKOUT = "InitiateCheckout"
    SCHEDULE = "Schedule"
    SUBMIT_APPLICATION = "SubmitApplication"


# ============== Meta Integration ==============


class MetaIntegrationBase(BaseModel):
    """Base schema for Meta integration."""

    pixel_id: str = Field(..., description="Meta Pixel ID from Events Manager")
    ad_account_id: str | None = Field(
        None, description="Optional Ad Account ID for Custom Audiences"
    )
    is_active: bool = Field(True, description="Enable/disable the integration")
    test_mode: bool = Field(
        False, description="Send events with test_event_code for debugging"
    )


class MetaIntegrationCreate(MetaIntegrationBase):
    """Schema for creating a Meta integration."""

    access_token: str = Field(
        ...,
        description="System User access token with ads_management permission",
        min_length=10,
    )


class MetaIntegrationUpdate(BaseModel):
    """Schema for updating a Meta integration."""

    pixel_id: str | None = None
    access_token: str | None = Field(None, min_length=10)
    ad_account_id: str | None = None
    is_active: bool | None = None
    test_mode: bool | None = None


class MetaIntegrationResponse(MetaIntegrationBase):
    """Schema for Meta integration response."""

    id: int
    tenant_id: str
    # Token is masked for security
    access_token_masked: str = Field(..., description="Masked access token (last 4 chars)")
    last_event_at: datetime | None
    total_events_sent: int
    total_events_failed: int
    success_rate: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MetaIntegrationStatus(BaseModel):
    """Quick status check response."""

    is_configured: bool
    is_active: bool
    test_mode: bool
    pixel_id: str | None
    last_event_at: datetime | None
    events_today: int
    success_rate: float


# ============== Conversion Events ==============


class ConversionEventBase(BaseModel):
    """Base schema for conversion events."""

    event_name: EventName
    contact_id: int | None = None
    pipeline_id: int | None = None
    enrollment_id: int | None = None
    custom_data: dict | None = Field(None, description="Event-specific custom data")


class TestEventRequest(BaseModel):
    """Schema for sending a test event."""

    event_name: EventName = Field(EventName.PAGE_VIEW, description="Event type to test")
    contact_id: int | None = Field(None, description="Optional contact to use")
    url: str | None = Field(None, description="URL for PageView events")
    custom_data: dict | None = None


class TestEventResponse(BaseModel):
    """Response from test event."""

    success: bool
    event_id: str | None
    message: str
    response_body: dict | None = None


class ConversionEventResponse(BaseModel):
    """Schema for conversion event response."""

    id: int
    event_name: str
    event_time: datetime
    event_id: str
    contact_id: int | None
    contact_name: str | None = None
    pipeline_id: int | None
    pipeline_name: str | None = None
    status: EventStatus
    custom_data: dict | None
    response_code: int | None
    error_message: str | None
    created_at: datetime
    sent_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ConversionEventList(BaseModel):
    """Paginated list of conversion events."""

    items: list[ConversionEventResponse]
    total: int
    page: int
    page_size: int


# ============== Statistics ==============


class EventStats(BaseModel):
    """Statistics for conversion events."""

    period_start: datetime
    period_end: datetime
    total_events: int
    events_sent: int
    events_failed: int
    success_rate: float
    events_by_type: dict[str, int]
    events_by_day: list[dict]


class DailyEventCount(BaseModel):
    """Event count for a single day."""

    date: str
    count: int
    sent: int
    failed: int


# ============== Setup Guide ==============


class SetupGuide(BaseModel):
    """Setup instructions for Meta integration."""

    steps: list[dict] = Field(
        default=[
            {
                "step": 1,
                "title": "Meta Pixel erstellen",
                "description": "Gehen Sie zum Meta Events Manager und erstellen Sie ein Pixel.",
                "link": "https://business.facebook.com/events_manager",
            },
            {
                "step": 2,
                "title": "System User erstellen",
                "description": "Erstellen Sie einen System User in den Business Settings.",
                "link": "https://business.facebook.com/settings/system-users",
            },
            {
                "step": 3,
                "title": "Access Token generieren",
                "description": "Generieren Sie einen Access Token mit 'ads_management' Berechtigung.",
                "permissions": ["ads_management", "ads_read"],
            },
            {
                "step": 4,
                "title": "Pixel ID eingeben",
                "description": "Kopieren Sie die Pixel ID aus dem Events Manager.",
            },
            {
                "step": 5,
                "title": "Token eingeben",
                "description": "Fügen Sie den Access Token hier ein.",
            },
            {
                "step": 6,
                "title": "Test-Event senden",
                "description": "Senden Sie ein Test-Event, um die Verbindung zu prüfen.",
            },
        ]
    )


# ============== Custom Audiences ==============


class SyncModeEnum(str, Enum):
    """Sync mode for Custom Audiences."""

    MANUAL = "manual"
    DAILY = "daily"
    REALTIME = "realtime"


class SyncStatusEnum(str, Enum):
    """Status of audience sync operation."""

    PENDING = "pending"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class SegmentFilter(BaseModel):
    """Filter criteria for audience segment."""

    stages: list[str] | None = Field(
        None, description="Pipeline stages to include (e.g., ['engaged', 'qualified'])"
    )
    statuses: list[str] | None = Field(
        None, description="Enrollment statuses to include (e.g., ['active'])"
    )
    tags: list[str] | None = Field(None, description="Contact tags to require")
    source_modules: list[str] | None = Field(
        None, description="Source modules to filter by"
    )


class CustomAudienceCreate(BaseModel):
    """Schema for creating a Custom Audience."""

    name: str = Field(..., min_length=1, max_length=200, description="Audience name")
    description: str | None = Field(None, max_length=500)
    pipeline_id: int | None = Field(None, description="Filter to specific pipeline")
    segment_filter: SegmentFilter | None = Field(
        None, description="Segment filter criteria"
    )
    sync_mode: SyncModeEnum = Field(
        SyncModeEnum.MANUAL, description="When to sync audience"
    )
    create_in_meta: bool = Field(
        True, description="Create audience in Meta immediately"
    )


class CustomAudienceUpdate(BaseModel):
    """Schema for updating a Custom Audience."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=500)
    segment_filter: SegmentFilter | None = None
    sync_mode: SyncModeEnum | None = None
    is_active: bool | None = None


class CustomAudienceResponse(BaseModel):
    """Schema for Custom Audience response."""

    id: int
    tenant_id: str
    name: str
    description: str | None
    meta_audience_id: str | None
    meta_audience_name: str | None
    pipeline_id: int | None
    pipeline_name: str | None = None
    segment_filter: dict
    sync_mode: str
    is_active: bool
    audience_size: int
    last_sync_at: datetime | None
    last_sync_count: int
    last_sync_status: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomAudienceList(BaseModel):
    """Paginated list of Custom Audiences."""

    items: list[CustomAudienceResponse]
    total: int


class AudienceSyncRequest(BaseModel):
    """Request to sync an audience."""

    # No fields needed, just triggers sync


class AudienceSyncLogResponse(BaseModel):
    """Schema for sync log response."""

    id: int
    audience_id: int
    audience_name: str | None = None
    operation: str
    started_at: datetime
    completed_at: datetime | None
    contacts_processed: int
    contacts_added: int
    contacts_removed: int
    contacts_failed: int
    status: str
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)


class AudienceSyncLogList(BaseModel):
    """Paginated list of sync logs."""

    items: list[AudienceSyncLogResponse]
    total: int


class AudienceStats(BaseModel):
    """Statistics for Custom Audiences."""

    total_audiences: int
    active_audiences: int
    total_contacts_synced: int
    last_sync_at: datetime | None
    audiences_by_pipeline: dict[str, int]
    sync_success_rate: float
