"""Post-Mail Module Schemas.

Pydantic schemas for API validation.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

# ============== Enums ==============


class LetterFormatEnum(str, Enum):
    """Letter format options."""

    A4 = "a4"
    US_LETTER = "us_letter"
    DIN_LANG = "din_lang"


class LetterStatusEnum(str, Enum):
    """Letter status options."""

    DRAFT = "draft"
    APPROVED = "approved"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    RETURNED = "returned"


class BatchStatusEnum(str, Enum):
    """Batch status options."""

    COLLECTING = "collecting"
    READY = "ready"
    EXPORTED = "exported"
    SENT = "sent"


# ============== Template Schemas ==============


class TemplateCreate(BaseModel):
    """Create a new template."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    format: LetterFormatEnum = LetterFormatEnum.A4
    content_html: str = Field(..., min_length=1)
    header_html: str | None = None
    footer_html: str | None = None


class TemplateUpdate(BaseModel):
    """Update a template."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    format: LetterFormatEnum | None = None
    content_html: str | None = None
    header_html: str | None = None
    footer_html: str | None = None
    is_active: bool | None = None


class TemplateResponse(BaseModel):
    """Template response."""

    id: int
    name: str
    description: str | None
    format: str
    content_html: str
    header_html: str | None
    footer_html: str | None
    preview_image: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None
    letter_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class TemplateList(BaseModel):
    """Paginated template list."""

    items: list[TemplateResponse]
    total: int


# ============== Letter Schemas ==============


class RecipientData(BaseModel):
    """Recipient address data."""

    name: str = Field(..., min_length=1, max_length=200)
    company: str | None = Field(None, max_length=200)
    street: str | None = Field(None, max_length=200)
    zip: str | None = Field(None, max_length=20)
    city: str | None = Field(None, max_length=100)
    country: str = Field("DE", max_length=10)


class LetterCreate(BaseModel):
    """Create a new letter."""

    template_id: int
    contact_id: int | None = None
    pipeline_id: int | None = None
    recipient: RecipientData
    content_html: str | None = None


class LetterCreateFromAction(BaseModel):
    """Create letter from pending action."""

    pending_action_id: int
    template_id: int


class LetterUpdate(BaseModel):
    """Update a letter."""

    recipient: RecipientData | None = None
    content_html: str | None = None
    status: LetterStatusEnum | None = None


class LetterResponse(BaseModel):
    """Letter response."""

    id: int
    template_id: int
    template_name: str | None = None
    contact_id: int | None
    pipeline_id: int | None
    batch_id: int | None
    recipient_name: str
    recipient_company: str | None
    recipient_street: str | None
    recipient_zip: str | None
    recipient_city: str | None
    recipient_country: str
    content_html: str | None
    pdf_path: str | None
    status: str
    queued_at: datetime | None
    sent_at: datetime | None
    delivered_at: datetime | None
    returned_at: datetime | None
    return_reason: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class LetterList(BaseModel):
    """Paginated letter list."""

    items: list[LetterResponse]
    total: int


# ============== Batch Schemas ==============


class BatchCreate(BaseModel):
    """Create a new batch."""

    name: str = Field(..., min_length=1, max_length=200)
    letter_ids: list[int] = Field(..., min_length=1)


class BatchUpdate(BaseModel):
    """Update a batch."""

    name: str | None = Field(None, min_length=1, max_length=200)
    status: BatchStatusEnum | None = None


class BatchResponse(BaseModel):
    """Batch response."""

    id: int
    name: str
    letter_count: int
    export_format: str | None
    export_path: str | None
    status: str
    exported_at: datetime | None
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class BatchList(BaseModel):
    """Paginated batch list."""

    items: list[BatchResponse]
    total: int


class BatchExportResponse(BaseModel):
    """Batch export response."""

    batch_id: int
    export_path: str
    letter_count: int


# ============== Preview/Render Schemas ==============


class RenderPreviewRequest(BaseModel):
    """Request to render a template preview."""

    template_id: int
    contact_id: int | None = None
    custom_data: dict | None = None


class RenderPreviewResponse(BaseModel):
    """Rendered template preview."""

    html: str
    recipient: RecipientData | None


# ============== Stats ==============


class PostmailStats(BaseModel):
    """Post-Mail statistics."""

    total_templates: int
    active_templates: int
    total_letters: int
    letters_by_status: dict[str, int]
    total_batches: int
    pending_batches: int
