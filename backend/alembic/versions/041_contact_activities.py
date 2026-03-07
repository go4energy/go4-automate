"""Contact activities table.

Revision ID: 041
Revises: 040
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contact_activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(50), nullable=False),
        # Foreign Keys
        sa.Column("contact_id", sa.Integer(), nullable=False),
        sa.Column("pipeline_id", sa.Integer(), nullable=True),
        sa.Column("enrollment_id", sa.Integer(), nullable=True),
        # Activity Info
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("activity_type", sa.String(100), nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        # Source
        sa.Column("source_module", sa.String(100), nullable=True),
        sa.Column("source_action_id", sa.Integer(), nullable=True),
        sa.Column("external_id", sa.String(200), nullable=True),
        # AI Analysis
        sa.Column("sentiment", sa.String(20), nullable=True),
        sa.Column("detected_intent", sa.String(50), nullable=True),
        sa.Column("ai_analysis", JSONB, nullable=True),
        # Status
        sa.Column("status", sa.String(50), nullable=True),
        # Metadata
        sa.Column("metadata_", JSONB, nullable=True),
        # Actor
        sa.Column("performed_by", sa.Integer(), nullable=True),
        sa.Column("performed_at", sa.DateTime(), nullable=False),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        # Keys
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pipeline_id"], ["engagement_pipelines.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["enrollment_id"], ["pipeline_enrollments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_action_id"], ["pending_actions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["performed_by"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_index("ix_contact_activities_tenant", "contact_activities", ["tenant_id"])
    op.create_index("ix_contact_activities_contact", "contact_activities", ["contact_id"])
    op.create_index("ix_contact_activities_enrollment", "contact_activities", ["enrollment_id"])
    op.create_index("ix_contact_activities_channel", "contact_activities", ["tenant_id", "channel"])
    op.create_index("ix_contact_activities_performed", "contact_activities", ["contact_id", "performed_at"])
    op.create_index("ix_contact_activities_external", "contact_activities", ["tenant_id", "external_id"])


def downgrade() -> None:
    op.drop_index("ix_contact_activities_external", table_name="contact_activities")
    op.drop_index("ix_contact_activities_performed", table_name="contact_activities")
    op.drop_index("ix_contact_activities_channel", table_name="contact_activities")
    op.drop_index("ix_contact_activities_enrollment", table_name="contact_activities")
    op.drop_index("ix_contact_activities_contact", table_name="contact_activities")
    op.drop_index("ix_contact_activities_tenant", table_name="contact_activities")
    op.drop_table("contact_activities")
