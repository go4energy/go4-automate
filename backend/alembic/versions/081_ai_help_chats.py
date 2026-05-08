"""AI-Help chat persistence — per user + topic + tenant.

The KI-Helper drawer (clickable from any contextual button in the UI)
keeps a chat history per topic so users can come back and continue.
Each chat is scoped to one user, one topic, and one tenant.

Revision ID: 081
Revises: 080
Create Date: 2026-05-03
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "081"
down_revision: str | None = "080"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "ai_help_chats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(length=50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "topic",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
        ),  # user | assistant
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("context_data", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_ai_help_chats_lookup",
        "ai_help_chats",
        ["tenant_id", "user_id", "topic", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_help_chats_lookup", table_name="ai_help_chats")
    op.drop_table("ai_help_chats")
