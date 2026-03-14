"""Add personal briefing account connections and settings.

Revision ID: 053
Revises: 052
Create Date: 2026-03-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "053"
down_revision = "052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "briefing_account_connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("integration_type", sa.String(length=20), nullable=False),
        sa.Column("connected_email", sa.String(length=255), nullable=True),
        sa.Column("encrypted_token", sa.Text(), nullable=True),
        sa.Column("scopes", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "user_id",
            "provider",
            "integration_type",
            name="uq_briefing_account_connections_scope",
        ),
    )
    op.create_index(
        "ix_briefing_account_connections_user",
        "briefing_account_connections",
        ["tenant_id", "user_id"],
        unique=False,
    )
    op.create_index(
        "ix_briefing_account_connections_status",
        "briefing_account_connections",
        ["tenant_id", "user_id", "status"],
        unique=False,
    )

    op.create_table(
        "briefing_personal_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "email_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "calendar_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("unread_only", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("days_back", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_items", sa.Integer(), nullable=False, server_default="8"),
        sa.Column(
            "timezone",
            sa.String(length=50),
            nullable=False,
            server_default="Europe/Berlin",
        ),
        sa.Column(
            "delivery_time",
            sa.String(length=10),
            nullable=False,
            server_default="07:00",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "user_id",
            name="uq_briefing_personal_settings_user",
        ),
    )
    op.create_index(
        "ix_briefing_personal_settings_user",
        "briefing_personal_settings",
        ["tenant_id", "user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_briefing_personal_settings_user",
        table_name="briefing_personal_settings",
    )
    op.drop_table("briefing_personal_settings")
    op.drop_index(
        "ix_briefing_account_connections_status",
        table_name="briefing_account_connections",
    )
    op.drop_index(
        "ix_briefing_account_connections_user",
        table_name="briefing_account_connections",
    )
    op.drop_table("briefing_account_connections")
