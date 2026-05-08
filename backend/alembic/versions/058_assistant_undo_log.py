"""Add assistant undo log table.

Revision ID: 058
Revises: 057
Create Date: 2026-03-15
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "058"
down_revision = "057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_undo_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=True),
        sa.Column("connection_id", sa.Integer(), nullable=True),
        sa.Column("draft_id", sa.Integer(), nullable=True),
        sa.Column("pending_intent_id", sa.Integer(), nullable=True),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="executed"),
        sa.Column("can_undo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("undone_at", sa.DateTime(), nullable=True),
        sa.Column("target_ref_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("before_state_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_state_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["integration_connections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["conversation_id"], ["assistant_conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["draft_id"], ["assistant_drafts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["pending_intent_id"], ["assistant_pending_intents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assistant_undo_log_tenant", "assistant_undo_logs", ["tenant_id", "user_id"])
    op.create_index("ix_assistant_undo_log_status", "assistant_undo_logs", ["status"])
    op.create_index("ix_assistant_undo_log_conv", "assistant_undo_logs", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_assistant_undo_log_conv", table_name="assistant_undo_logs")
    op.drop_index("ix_assistant_undo_log_status", table_name="assistant_undo_logs")
    op.drop_index("ix_assistant_undo_log_tenant", table_name="assistant_undo_logs")
    op.drop_table("assistant_undo_logs")
