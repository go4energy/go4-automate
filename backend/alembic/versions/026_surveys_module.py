"""Surveys module - feedback and NPS surveys.

Revision ID: 026
Revises: 025
Create Date: 2024-01-15

"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers
revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Surveys table
    op.create_table(
        "surveys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(50), nullable=False, index=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        # Basics
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("slug", sa.String(100), nullable=False),
        # Status
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("survey_type", sa.String(20), nullable=False, server_default="general"),
        # Settings
        sa.Column("anonymous", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("show_progress", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("one_response_per_contact", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("allow_multiple_submissions", sa.Boolean(), nullable=False, server_default="true"),
        # Branding
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("primary_color", sa.String(7), nullable=False, server_default="#FF6600"),
        sa.Column("background_color", sa.String(7), nullable=False, server_default="#FFFFFF"),
        # Zeitsteuerung
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        # Thank you page
        sa.Column("thank_you_title", sa.String(255), nullable=False, server_default="Vielen Dank!"),
        sa.Column("thank_you_message", sa.Text(), nullable=True),
        sa.Column("redirect_url", sa.String(500), nullable=True),
        # Stats (cached)
        sa.Column("response_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_rate", sa.Float(), nullable=True),
        sa.Column("avg_completion_time", sa.Integer(), nullable=True),
        # n8n Integration
        sa.Column("webhook_url", sa.String(500), nullable=True),
        sa.Column("webhook_on_complete", sa.Boolean(), nullable=False, server_default="false"),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Unique constraint on tenant_id + slug
    op.create_unique_constraint("uq_surveys_tenant_slug", "surveys", ["tenant_id", "slug"])

    # Survey Questions table
    op.create_table(
        "survey_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(50), nullable=False, index=True),
        sa.Column("survey_id", sa.Integer(), sa.ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False),
        # Position
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("page", sa.Integer(), nullable=False, server_default="1"),
        # Question
        sa.Column("question_type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False, server_default="false"),
        # Options (for choice questions)
        sa.Column("options", JSONB, nullable=True),
        # Settings per type
        sa.Column("settings", JSONB, nullable=True),
        # Simple logic
        sa.Column("show_if_question_id", sa.Integer(), sa.ForeignKey("survey_questions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("show_if_value", sa.String(255), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_index("ix_survey_questions_survey_position", "survey_questions", ["survey_id", "position"])

    # Survey Responses table (one per participant)
    op.create_table(
        "survey_responses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(50), nullable=False, index=True),
        sa.Column("survey_id", sa.Integer(), sa.ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False),
        # Participant (optional for non-anonymous)
        sa.Column("contact_id", sa.Integer(), sa.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        # Token for participation
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        # Status
        sa.Column("status", sa.String(20), nullable=False, server_default="started"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        # Meta
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        # NPS score (if NPS survey)
        sa.Column("nps_score", sa.Integer(), nullable=True),
        sa.Column("nps_category", sa.String(20), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_index("ix_survey_responses_survey_status", "survey_responses", ["survey_id", "status"])
    op.create_index("ix_survey_responses_contact", "survey_responses", ["contact_id"])

    # Survey Answers table
    op.create_table(
        "survey_answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(50), nullable=False, index=True),
        sa.Column("response_id", sa.Integer(), sa.ForeignKey("survey_responses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("survey_questions.id", ondelete="CASCADE"), nullable=False),
        # Answer values (depending on question type)
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_number", sa.Integer(), nullable=True),
        sa.Column("value_float", sa.Float(), nullable=True),
        sa.Column("value_list", JSONB, nullable=True),
        sa.Column("value_bool", sa.Boolean(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_index("ix_survey_answers_response", "survey_answers", ["response_id"])
    op.create_index("ix_survey_answers_question", "survey_answers", ["question_id"])
    op.create_unique_constraint("uq_survey_answers_response_question", "survey_answers", ["response_id", "question_id"])


def downgrade() -> None:
    op.drop_table("survey_answers")
    op.drop_table("survey_responses")
    op.drop_table("survey_questions")
    op.drop_table("surveys")
