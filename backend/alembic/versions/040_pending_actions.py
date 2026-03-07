"""Pending actions table.

Revision ID: 040
Revises: 039
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pending_actions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(50), nullable=False),
        # Foreign Keys
        sa.Column("contact_id", sa.Integer(), nullable=False),
        sa.Column("pipeline_id", sa.Integer(), nullable=False),
        sa.Column("enrollment_id", sa.Integer(), nullable=False),
        # Action Definition
        sa.Column("module", sa.String(100), nullable=False),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("context", JSONB, nullable=False, server_default="{}"),
        sa.Column("suggested_content", sa.Text(), nullable=True),
        # Priority & Scheduling
        sa.Column("priority", sa.String(20), server_default="normal", nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        # Approval
        sa.Column("needs_approval", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        # Result
        sa.Column("result", JSONB, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        # Keys
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pipeline_id"], ["engagement_pipelines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["enrollment_id"], ["pipeline_enrollments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_index("ix_pending_actions_tenant", "pending_actions", ["tenant_id"])
    op.create_index("ix_pending_actions_contact", "pending_actions", ["contact_id"])
    op.create_index("ix_pending_actions_enrollment", "pending_actions", ["enrollment_id"])
    op.create_index("ix_pending_actions_module", "pending_actions", ["tenant_id", "module"])
    op.create_index("ix_pending_actions_status", "pending_actions", ["tenant_id", "status"])
    op.create_index("ix_pending_actions_due", "pending_actions", ["tenant_id", "status", "due_at"])


def downgrade() -> None:
    op.drop_index("ix_pending_actions_due", table_name="pending_actions")
    op.drop_index("ix_pending_actions_status", table_name="pending_actions")
    op.drop_index("ix_pending_actions_module", table_name="pending_actions")
    op.drop_index("ix_pending_actions_enrollment", table_name="pending_actions")
    op.drop_index("ix_pending_actions_contact", table_name="pending_actions")
    op.drop_index("ix_pending_actions_tenant", table_name="pending_actions")
    op.drop_table("pending_actions")
