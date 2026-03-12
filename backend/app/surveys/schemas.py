"""Surveys module Pydantic schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


# Enums
class SurveyStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class SurveyType(str, Enum):
    GENERAL = "general"
    NPS = "nps"
    CSAT = "csat"
    FEEDBACK = "feedback"


class QuestionType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT = "text"
    TEXTAREA = "textarea"
    SCALE = "scale"
    NPS = "nps"
    YES_NO = "yes_no"
    RATING = "rating"


class ResponseStatus(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class NpsCategory(str, Enum):
    DETRACTOR = "detractor"
    PASSIVE = "passive"
    PROMOTER = "promoter"


# Question Schemas
class QuestionSettings(BaseModel):
    """Question type-specific settings."""

    # Scale settings
    min_value: int | None = None
    max_value: int | None = None
    min_label: str | None = None
    max_label: str | None = None

    # Text settings
    multiline: bool | None = None
    max_length: int | None = None
    placeholder: str | None = None


class QuestionCreate(BaseModel):
    """Schema for creating a question."""

    question_type: QuestionType
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    required: bool = False
    position: int | None = None
    page: int = 1
    options: list[str] | None = None
    settings: QuestionSettings | None = None
    show_if_question_id: int | None = None
    show_if_value: str | None = None


class QuestionUpdate(BaseModel):
    """Schema for updating a question."""

    question_type: QuestionType | None = None
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    required: bool | None = None
    position: int | None = None
    page: int | None = None
    options: list[str] | None = None
    settings: QuestionSettings | None = None
    show_if_question_id: int | None = None
    show_if_value: str | None = None


class QuestionResponse(BaseModel):
    """Schema for question response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_id: int
    question_type: str
    title: str
    description: str | None
    required: bool
    position: int
    page: int
    options: list[str] | None
    settings: dict | None
    show_if_question_id: int | None
    show_if_value: str | None
    created_at: datetime


class QuestionReorder(BaseModel):
    """Schema for reordering questions."""

    question_ids: list[int]


# Survey Schemas
class SurveyCreate(BaseModel):
    """Schema for creating a survey."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    survey_type: SurveyType = SurveyType.GENERAL
    anonymous: bool = True
    show_progress: bool = True
    one_response_per_contact: bool = False
    allow_multiple_submissions: bool = True
    logo_url: str | None = None
    primary_color: str = "#FF6600"
    background_color: str = "#FFFFFF"
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    thank_you_title: str = "Vielen Dank!"
    thank_you_message: str | None = None
    redirect_url: str | None = None
    webhook_url: str | None = None
    webhook_on_complete: bool = False


class SurveyUpdate(BaseModel):
    """Schema for updating a survey."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    survey_type: SurveyType | None = None
    anonymous: bool | None = None
    show_progress: bool | None = None
    one_response_per_contact: bool | None = None
    allow_multiple_submissions: bool | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    background_color: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    thank_you_title: str | None = None
    thank_you_message: str | None = None
    redirect_url: str | None = None
    webhook_url: str | None = None
    webhook_on_complete: bool | None = None


class SurveyResponse(BaseModel):
    """Schema for survey response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: str
    owner_id: int | None
    title: str
    description: str | None
    slug: str
    status: str
    survey_type: str
    anonymous: bool
    show_progress: bool
    one_response_per_contact: bool
    allow_multiple_submissions: bool
    logo_url: str | None
    primary_color: str
    background_color: str
    starts_at: datetime | None
    ends_at: datetime | None
    thank_you_title: str
    thank_you_message: str | None
    redirect_url: str | None
    response_count: int
    completion_rate: float | None
    avg_completion_time: int | None
    webhook_url: str | None
    webhook_on_complete: bool
    created_at: datetime
    updated_at: datetime


class SurveyWithQuestions(SurveyResponse):
    """Survey with questions included."""

    questions: list[QuestionResponse] = []


class SurveyStatusUpdate(BaseModel):
    """Schema for updating survey status."""

    status: SurveyStatus


# Response Schemas (Participant Answers)
class AnswerSubmit(BaseModel):
    """Schema for submitting an answer."""

    question_id: int
    value_text: str | None = None
    value_number: int | None = None
    value_float: float | None = None
    value_list: list[str] | None = None
    value_bool: bool | None = None


class ResponseStart(BaseModel):
    """Schema for starting a response."""

    email: str | None = None
    name: str | None = None
    contact_id: int | None = None


class ResponseComplete(BaseModel):
    """Schema for completing a response."""

    answers: list[AnswerSubmit] = []


class AnswerResponse(BaseModel):
    """Schema for answer in response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    value_text: str | None
    value_number: int | None
    value_float: float | None
    value_list: list[str] | None
    value_bool: bool | None


class ParticipantResponse(BaseModel):
    """Schema for participant response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_id: int
    contact_id: int | None
    email: str | None
    name: str | None
    token: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: int | None
    nps_score: int | None
    nps_category: str | None
    answers: list[AnswerResponse] = []


class ParticipantResponseList(BaseModel):
    """Schema for listing participant responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_id: int
    contact_id: int | None
    email: str | None
    name: str | None
    status: str
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: int | None
    nps_score: int | None
    nps_category: str | None


# Public Schemas (for survey takers)
class PublicSurvey(BaseModel):
    """Public survey schema (no sensitive data)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    survey_type: str
    show_progress: bool
    logo_url: str | None
    primary_color: str
    background_color: str
    thank_you_title: str
    thank_you_message: str | None
    redirect_url: str | None
    questions: list[QuestionResponse] = []


class PublicStartResponse(BaseModel):
    """Response after starting a survey."""

    response_id: int
    token: str


# Stats Schemas
class NpsStats(BaseModel):
    """NPS statistics."""

    score: int
    total_responses: int
    promoters: int
    passives: int
    detractors: int
    promoter_percentage: float
    passive_percentage: float
    detractor_percentage: float


class QuestionStats(BaseModel):
    """Statistics for a single question."""

    question_id: int
    question_title: str
    question_type: str
    total_answers: int
    # For choice questions
    option_counts: dict[str, int] | None = None
    # For numeric questions
    average: float | None = None
    min_value: float | None = None
    max_value: float | None = None
    # Distribution for scale/rating/nps
    distribution: dict[int, int] | None = None


class SurveyStats(BaseModel):
    """Overall survey statistics."""

    survey_id: int
    total_responses: int
    completed_responses: int
    completion_rate: float
    avg_completion_time: int | None
    nps: NpsStats | None = None
    questions: list[QuestionStats] = []


# Share/Distribution
class ShareLink(BaseModel):
    """Share link response."""

    url: str
    slug: str
    qr_code_url: str | None = None


class SendInvites(BaseModel):
    """Schema for sending email invites."""

    contact_ids: list[int] = []
    emails: list[str] = []
    subject: str | None = None
    message: str | None = None
