"""Pipeline enrollments table.

Revision ID: 039
Revises: 038
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pipeline_enrollments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(50), nullable=False),
        # Foreign Keys
        sa.Column("contact_id", sa.Integer(), nullable=False),
        sa.Column("pipeline_id", sa.Integer(), nullable=False),
        # Source Information
        sa.Column("source_module", sa.String(100), nullable=True),
        sa.Column("source_campaign", sa.String(200), nullable=True),
        sa.Column("source_context", JSONB, nullable=True),
        # Stage & Status
        sa.Column("stage", sa.String(50), server_default="lead", nullable=False),
        sa.Column("status", sa.String(50), server_default="active", nullable=False),
        # Engagement Tracking
        sa.Column("touch_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_touch_at", sa.DateTime(), nullable=True),
        sa.Column("last_response_at", sa.DateTime(), nullable=True),
        # Outcome
        sa.Column("outcome", sa.String(100), nullable=True),
        # Timestamps
        sa.Column("enrolled_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        # Keys
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pipeline_id"], ["engagement_pipelines.id"], ondelete="CASCADE"),
        # Prevent duplicate enrollments in same pipeline
        sa.UniqueConstraint("contact_id", "pipeline_id", name="uq_enrollments_contact_pipeline"),
    )

    op.create_index("ix_enrollments_tenant", "pipeline_enrollments", ["tenant_id"])
    op.create_index("ix_enrollments_contact", "pipeline_enrollments", ["contact_id"])
    op.create_index("ix_enrollments_pipeline", "pipeline_enrollments", ["pipeline_id"])
    op.create_index("ix_enrollments_status", "pipeline_enrollments", ["tenant_id", "status"])
    op.create_index("ix_enrollments_stage", "pipeline_enrollments", ["tenant_id", "pipeline_id", "stage"])


def downgrade() -> None:
    op.drop_index("ix_enrollments_stage", table_name="pipeline_enrollments")
    op.drop_index("ix_enrollments_status", table_name="pipeline_enrollments")
    op.drop_index("ix_enrollments_pipeline", table_name="pipeline_enrollments")
    op.drop_index("ix_enrollments_contact", table_name="pipeline_enrollments")
    op.drop_index("ix_enrollments_tenant", table_name="pipeline_enrollments")
    op.drop_table("pipeline_enrollments")
