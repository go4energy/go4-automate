"""Merge AI-Helper into Chat — add `topic` field to conversations, drop ai_help_chats.

The KI-Helper had its own table `ai_help_chats` which duplicated the existing
chat infrastructure. Conversations now carry an optional `topic` so a context-
specific help thread is just a regular chat with a topic tag.

Revision ID: 082
Revises: 081
Create Date: 2026-05-03
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "082"
down_revision: str | None = "081"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("topic", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_conversations_tenant_topic",
        "conversations",
        ["tenant_id", "topic"],
    )

    op.drop_index("ix_ai_help_chats_lookup", table_name="ai_help_chats")
    op.drop_table("ai_help_chats")


def downgrade() -> None:
    op.create_table(
        "ai_help_chats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(length=50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column(
            "context_data",
            sa.dialects.postgresql.JSONB(),
            nullable=True,
        ),
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

    op.drop_index("ix_conversations_tenant_topic", table_name="conversations")
    op.drop_column("conversations", "topic")
