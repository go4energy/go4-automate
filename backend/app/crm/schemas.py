"""CRM schemas."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CrmContactCreate(BaseModel):
    """Schema for creating a new contact."""

    email: EmailStr
    name: str
    phone: str | None = None
    source: str | None = None
    konfigurator_data: dict | None = None
    notes: str | None = None


class CrmContactResponse(BaseModel):
    """Schema for contact response."""

    id: int
    tenant_id: str
    email: str
    name: str
    phone: str | None = None
    source: str | None = None
    score: int
    status: str
    konfigurator_data: dict | None = None
    followup_step: int
    followup_paused: bool
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CrmContactStatusUpdate(BaseModel):
    """Schema for updating contact status."""

    status: str


class CrmFollowupPause(BaseModel):
    """Schema for pausing/resuming follow-up."""

    paused: bool


# ============== Pipeline Schemas ==============


class PipelineStageCreate(BaseModel):
    """Schema for creating a pipeline stage."""

    name: str = Field(..., min_length=1, max_length=100)
    position: int = 0
    probability: int = Field(default=0, ge=0, le=100)
    color: str = "#6B7280"
    is_won: bool = False
    is_lost: bool = False


class PipelineStageUpdate(BaseModel):
    """Schema for updating a pipeline stage."""

    name: str | None = Field(None, min_length=1, max_length=100)
    position: int | None = None
    probability: int | None = Field(None, ge=0, le=100)
    color: str | None = None
    is_won: bool | None = None
    is_lost: bool | None = None


class PipelineStageResponse(BaseModel):
    """Schema for pipeline stage response."""

    id: int
    pipeline_id: int
    name: str
    position: int
    probability: int
    color: str
    is_won: bool
    is_lost: bool

    model_config = ConfigDict(from_attributes=True)


class PipelineCreate(BaseModel):
    """Schema for creating a pipeline."""

    name: str = Field(..., min_length=1, max_length=100)
    is_default: bool = False
    color: str | None = None
    description: str | None = None
    stages: list[PipelineStageCreate] = Field(default_factory=list)


class PipelineUpdate(BaseModel):
    """Schema for updating a pipeline."""

    name: str | None = Field(None, min_length=1, max_length=100)
    is_default: bool | None = None
    color: str | None = None
    description: str | None = None


class PipelineResponse(BaseModel):
    """Schema for pipeline response."""

    id: int
    tenant_id: str
    name: str
    is_default: bool
    color: str | None
    description: str | None
    stages: list[PipelineStageResponse] = []
    deal_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PipelineListResponse(BaseModel):
    """Schema for pipeline list response."""

    id: int
    name: str
    is_default: bool
    color: str | None
    stage_count: int = 0
    deal_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# ============== Deal Schemas ==============


class DealCreate(BaseModel):
    """Schema for creating a deal."""

    title: str = Field(..., min_length=1, max_length=200)
    pipeline_id: int
    stage_id: int
    contact_id: int | None = None
    company_id: int | None = None
    owner_id: int | None = None
    value: Decimal | None = None
    currency: str = "EUR"
    expected_close: date | None = None
    priority: str = "medium"
    tags: list[str] = Field(default_factory=list)
    description: str | None = None
    custom_fields: dict = Field(default_factory=dict)


class DealUpdate(BaseModel):
    """Schema for updating a deal."""

    title: str | None = Field(None, min_length=1, max_length=200)
    contact_id: int | None = None
    company_id: int | None = None
    owner_id: int | None = None
    value: Decimal | None = None
    currency: str | None = None
    expected_close: date | None = None
    priority: str | None = None
    tags: list[str] | None = None
    description: str | None = None
    custom_fields: dict | None = None
    lost_reason: str | None = None


class DealMoveRequest(BaseModel):
    """Schema for moving a deal to a different stage."""

    stage_id: int
    position: int | None = None  # For reordering within stage


class DealResponse(BaseModel):
    """Schema for deal response."""

    id: int
    tenant_id: str
    title: str
    pipeline_id: int
    stage_id: int
    contact_id: int | None
    company_id: int | None
    owner_id: int | None
    value: Decimal | None
    currency: str
    probability: int
    expected_close: date | None
    status: str
    priority: str
    tags: list[str]
    description: str | None
    lost_reason: str | None
    won_at: datetime | None
    lost_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # Computed fields
    contact_name: str | None = None
    company_name: str | None = None
    stage_name: str | None = None
    owner_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DealListResponse(BaseModel):
    """Schema for deal list response (lighter)."""

    id: int
    title: str
    pipeline_id: int
    stage_id: int
    value: Decimal | None
    currency: str
    probability: int
    expected_close: date | None
    status: str
    priority: str
    tags: list[str]
    contact_name: str | None = None
    company_name: str | None = None
    stage_name: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KanbanStageResponse(BaseModel):
    """Schema for Kanban stage with deals."""

    id: int
    name: str
    position: int
    probability: int
    color: str
    is_won: bool
    is_lost: bool
    deals: list[DealListResponse] = []
    total_value: Decimal = Decimal("0")
    deal_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class KanbanBoardResponse(BaseModel):
    """Schema for full Kanban board response."""

    pipeline: PipelineListResponse
    stages: list[KanbanStageResponse]

    model_config = ConfigDict(from_attributes=True)


# ============== Activity Schemas ==============


class ActivityCreate(BaseModel):
    """Schema for creating an activity."""

    activity_type: str = Field(..., pattern="^(call|meeting|email|note|task_completed)$")
    subject: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    activity_date: datetime | None = None
    contact_id: int | None = None
    company_id: int | None = None
    deal_id: int | None = None
    metadata: dict | None = None


class ActivityResponse(BaseModel):
    """Schema for activity response."""

    id: int
    tenant_id: str
    activity_type: str
    subject: str
    description: str | None
    activity_date: datetime
    contact_id: int | None
    company_id: int | None
    deal_id: int | None
    user_id: int | None
    user_name: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============== Task Schemas ==============


class TaskCreate(BaseModel):
    """Schema for creating a task."""

    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    due_date: date | None = None
    priority: str = "medium"
    contact_id: int | None = None
    company_id: int | None = None
    deal_id: int | None = None
    assigned_to: int | None = None


# ============== Call Queue Schemas ==============


class CallActionResponse(BaseModel):
    """Schema for a phone action from engagement queue."""

    id: int
    contact_id: int | None = None
    pipeline_id: int | None = None
    enrollment_id: int | None = None
    action_type: str
    suggested_content: str | None = None
    priority: str
    due_at: datetime | None = None
    status: str
    created_at: datetime
    # Enriched fields
    contact_name: str | None = None
    contact_company: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    pipeline_name: str | None = None
    context: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class CallLogRequest(BaseModel):
    """Schema for logging a call result."""

    outcome: str = Field(
        ..., pattern="^(answered|no_answer|voicemail|wrong_number|callback|not_interested|qualified)$"
    )
    duration_seconds: int | None = Field(None, ge=0)
    notes: str | None = None
    follow_up_date: date | None = None
    deal_id: int | None = None


class CallStatsResponse(BaseModel):
    """Schema for call queue statistics."""

    total_pending: int = 0
    due_today: int = 0
    overdue: int = 0
    completed_today: int = 0
    by_priority: dict = Field(default_factory=dict)


class TaskUpdate(BaseModel):
    """Schema for updating a task."""

    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = None
    due_date: date | None = None
    priority: str | None = None
    status: str | None = None
    assigned_to: int | None = None


class TaskResponse(BaseModel):
    """Schema for task response."""

    id: int
    tenant_id: str
    title: str
    description: str | None
    due_date: date | None
    priority: str
    status: str
    completed_at: datetime | None
    contact_id: int | None
    company_id: int | None
    deal_id: int | None
    assigned_to: int | None
    created_by: int | None
    assignee_name: str | None = None
    creator_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
