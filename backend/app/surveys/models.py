"""Surveys module database models."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.auth.models import User
    from app.contacts.models import Contact


class SurveyStatus(str, Enum):
    """Survey status."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class SurveyType(str, Enum):
    """Survey type."""

    GENERAL = "general"
    NPS = "nps"
    CSAT = "csat"
    FEEDBACK = "feedback"


class QuestionType(str, Enum):
    """Question type."""

    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT = "text"
    TEXTAREA = "textarea"
    SCALE = "scale"
    NPS = "nps"
    YES_NO = "yes_no"
    RATING = "rating"


class ResponseStatus(str, Enum):
    """Response status."""

    STARTED = "started"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class NpsCategory(str, Enum):
    """NPS category."""

    DETRACTOR = "detractor"
    PASSIVE = "passive"
    PROMOTER = "promoter"


class Survey(Base):
    """Survey/questionnaire model."""

    __tablename__ = "surveys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    owner_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Basics
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SurveyStatus.DRAFT.value
    )
    survey_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SurveyType.GENERAL.value
    )

    # Settings
    anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    show_progress: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    one_response_per_contact: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    allow_multiple_submissions: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Branding
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    primary_color: Mapped[str] = mapped_column(
        String(7), nullable=False, default="#FF6600"
    )
    background_color: Mapped[str] = mapped_column(
        String(7), nullable=False, default="#FFFFFF"
    )

    # Zeitsteuerung
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Thank you page
    thank_you_title: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Vielen Dank!"
    )
    thank_you_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    redirect_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Stats (cached)
    response_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_completion_time: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # n8n Integration
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    webhook_on_complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="surveys")
    questions: Mapped[list["SurveyQuestion"]] = relationship(
        "SurveyQuestion",
        back_populates="survey",
        cascade="all, delete-orphan",
        order_by="SurveyQuestion.position",
    )
    responses: Mapped[list["SurveyResponse"]] = relationship(
        "SurveyResponse",
        back_populates="survey",
        cascade="all, delete-orphan",
    )


class SurveyQuestion(Base):
    """Survey question model."""

    __tablename__ = "survey_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    survey_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False
    )

    # Position
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Question
    question_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Options (for choice questions)
    options: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Settings per type
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Simple logic
    show_if_question_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("survey_questions.id", ondelete="SET NULL"), nullable=True
    )
    show_if_value: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    survey: Mapped["Survey"] = relationship("Survey", back_populates="questions")
    answers: Mapped[list["SurveyAnswer"]] = relationship(
        "SurveyAnswer",
        back_populates="question",
        cascade="all, delete-orphan",
    )
    show_if_question: Mapped["SurveyQuestion | None"] = relationship(
        "SurveyQuestion",
        remote_side=[id],
        foreign_keys=[show_if_question_id],
    )


class SurveyResponse(Base):
    """Survey response (one per participant)."""

    __tablename__ = "survey_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    survey_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False
    )

    # Participant (optional for non-anonymous)
    contact_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Token for participation
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ResponseStatus.STARTED.value
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Meta
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # NPS score (if NPS survey)
    nps_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nps_category: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    survey: Mapped["Survey"] = relationship("Survey", back_populates="responses")
    contact: Mapped["Contact | None"] = relationship("Contact")
    answers: Mapped[list["SurveyAnswer"]] = relationship(
        "SurveyAnswer",
        back_populates="response",
        cascade="all, delete-orphan",
    )


class SurveyAnswer(Base):
    """Individual answer to a question."""

    __tablename__ = "survey_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    response_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("survey_responses.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("survey_questions.id", ondelete="CASCADE"), nullable=False
    )

    # Answer values (depending on question type)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_float: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_list: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    value_bool: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    response: Mapped["SurveyResponse"] = relationship(
        "SurveyResponse", back_populates="answers"
    )
    question: Mapped["SurveyQuestion"] = relationship(
        "SurveyQuestion", back_populates="answers"
    )
