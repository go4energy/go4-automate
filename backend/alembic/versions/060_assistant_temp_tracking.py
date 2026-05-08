"""Add assistant TEMP tracking table.

Revision ID: 060
Revises: 059
Create Date: 2026-03-16
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "060"
down_revision = "059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_temp_tracking",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("connection_id", sa.Integer(), nullable=True),
        sa.Column("message_external_id", sa.String(length=500), nullable=False),
        sa.Column("thread_external_id", sa.String(length=500), nullable=True),
        sa.Column("mailbox_address", sa.String(length=255), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("sender", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolution_status", sa.String(length=30), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["connection_id"], ["integration_connections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "connection_id",
            "message_external_id",
            name="uq_assistant_temp_tracking_message",
        ),
    )
    op.create_index(
        "ix_assistant_temp_tracking_tenant_user",
        "assistant_temp_tracking",
        ["tenant_id", "user_id"],
    )
    op.create_index(
        "ix_assistant_temp_tracking_expires",
        "assistant_temp_tracking",
        ["tenant_id", "expires_at"],
    )
    op.create_index(
        "ix_assistant_temp_tracking_open",
        "assistant_temp_tracking",
        ["tenant_id", "resolved_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assistant_temp_tracking_open",
        table_name="assistant_temp_tracking",
    )
    op.drop_index(
        "ix_assistant_temp_tracking_expires",
        table_name="assistant_temp_tracking",
    )
    op.drop_index(
        "ix_assistant_temp_tracking_tenant_user",
        table_name="assistant_temp_tracking",
    )
    op.drop_table("assistant_temp_tracking")
