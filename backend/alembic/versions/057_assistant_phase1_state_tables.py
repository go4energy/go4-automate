"""Add persistent assistant state tables for voice phase 1.

Revision ID: 057
Revises: 056
Create Date: 2026-03-15
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "057"
down_revision = "056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_pending_intents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=True),
        sa.Column("connection_id", sa.Integer(), nullable=True),
        sa.Column("intent_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="awaiting_confirmation"),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_ref_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confirmation_token", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["integration_connections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["conversation_id"], ["assistant_conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_assistant_pending_intent_tenant",
        "assistant_pending_intents",
        ["tenant_id", "user_id"],
    )
    op.create_index(
        "ix_assistant_pending_intent_status",
        "assistant_pending_intents",
        ["status"],
    )
    op.create_index(
        "ix_assistant_pending_intent_conv",
        "assistant_pending_intents",
        ["conversation_id"],
    )

    op.create_table(
        "assistant_drafts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=True),
        sa.Column("connection_id", sa.Integer(), nullable=True),
        sa.Column("draft_type", sa.String(length=30), nullable=False, server_default="reply"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("target_external_id", sa.String(length=500), nullable=True),
        sa.Column("thread_external_id", sa.String(length=500), nullable=True),
        sa.Column("to_recipients_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("cc_recipients_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("bcc_recipients_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("provider_draft_id", sa.String(length=500), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("discarded_at", sa.DateTime(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["integration_connections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["conversation_id"], ["assistant_conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assistant_draft_tenant", "assistant_drafts", ["tenant_id", "user_id"])
    op.create_index("ix_assistant_draft_status", "assistant_drafts", ["status"])
    op.create_index("ix_assistant_draft_conv", "assistant_drafts", ["conversation_id"])

    op.create_table(
        "assistant_conversation_turns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("turn_type", sa.String(length=30), nullable=False, server_default="message"),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("tool_name", sa.String(length=100), nullable=True),
        sa.Column("tool_args_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tool_result_text", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["assistant_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assistant_conv_turn_conv", "assistant_conversation_turns", ["conversation_id"])
    op.create_index("ix_assistant_conv_turn_tenant", "assistant_conversation_turns", ["tenant_id", "user_id"])
    op.create_index("ix_assistant_conv_turn_role", "assistant_conversation_turns", ["role"])


def downgrade() -> None:
    op.drop_index("ix_assistant_conv_turn_role", table_name="assistant_conversation_turns")
    op.drop_index("ix_assistant_conv_turn_tenant", table_name="assistant_conversation_turns")
    op.drop_index("ix_assistant_conv_turn_conv", table_name="assistant_conversation_turns")
    op.drop_table("assistant_conversation_turns")

    op.drop_index("ix_assistant_draft_conv", table_name="assistant_drafts")
    op.drop_index("ix_assistant_draft_status", table_name="assistant_drafts")
    op.drop_index("ix_assistant_draft_tenant", table_name="assistant_drafts")
    op.drop_table("assistant_drafts")

    op.drop_index("ix_assistant_pending_intent_conv", table_name="assistant_pending_intents")
    op.drop_index("ix_assistant_pending_intent_status", table_name="assistant_pending_intents")
    op.drop_index("ix_assistant_pending_intent_tenant", table_name="assistant_pending_intents")
    op.drop_table("assistant_pending_intents")
