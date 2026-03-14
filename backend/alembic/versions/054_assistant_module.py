"""Create assistant module tables.

Revision ID: 054
Revises: 053
Create Date: 2026-03-14
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "054"
down_revision = "053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- A. Platform integration tables --

    op.create_table(
        "integration_connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("integration_type", sa.String(length=50), nullable=False),
        sa.Column(
            "auth_mode",
            sa.String(length=30),
            nullable=False,
            server_default="delegated",
        ),
        sa.Column("external_account_id", sa.String(length=255), nullable=True),
        sa.Column("mailbox_address", sa.String(length=255), nullable=True),
        sa.Column("connected_email", sa.String(length=255), nullable=True),
        sa.Column("account_label", sa.String(length=200), nullable=True),
        sa.Column("encrypted_token", sa.Text(), nullable=True),
        sa.Column("scopes", JSONB, nullable=True),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("metadata_json", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "user_id",
            "provider",
            "integration_type",
            "connected_email",
            name="uq_integration_conn_tenant_user_provider_type_email",
        ),
    )
    op.create_index(
        "ix_integration_conn_tenant",
        "integration_connections",
        ["tenant_id"],
    )
    op.create_index(
        "ix_integration_conn_user",
        "integration_connections",
        ["tenant_id", "user_id"],
    )

    op.create_table(
        "integration_connection_capabilities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("connection_id", sa.Integer(), nullable=False),
        sa.Column("capability", sa.String(length=50), nullable=False),
        sa.Column(
            "granted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["integration_connections.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("connection_id", "capability", name="uq_conn_capability"),
    )
    op.create_index(
        "ix_conn_cap_connection",
        "integration_connection_capabilities",
        ["connection_id"],
    )

    # -- B. Assistant-specific tables --

    op.create_table(
        "assistant_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "briefing_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "voice_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "autopilot_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "timezone",
            sa.String(length=50),
            nullable=False,
            server_default="Europe/Vienna",
        ),
        sa.Column("delivery_time", sa.String(length=10), nullable=True),
        sa.Column(
            "llm_provider",
            sa.String(length=50),
            nullable=False,
            server_default="ollama",
        ),
        sa.Column("llm_model", sa.String(length=100), nullable=True),
        sa.Column(
            "tts_provider",
            sa.String(length=50),
            nullable=False,
            server_default="piper",
        ),
        sa.Column("tts_voice", sa.String(length=100), nullable=True),
        sa.Column(
            "stt_provider",
            sa.String(length=50),
            nullable=False,
            server_default="faster-whisper",
        ),
        sa.Column(
            "max_items_per_run",
            sa.Integer(),
            nullable=False,
            server_default="30",
        ),
        sa.Column(
            "default_reply_mode",
            sa.String(length=20),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_assistant_profile_user"),
    )
    op.create_index(
        "ix_assistant_profile_tenant",
        "assistant_profiles",
        ["tenant_id"],
    )

    op.create_table(
        "assistant_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("connection_id", sa.Integer(), nullable=False),
        sa.Column(
            "briefing_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "voice_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "reply_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "autopilot_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("settings_json", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["integration_connections.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "user_id",
            "connection_id",
            name="uq_assistant_source_user_conn",
        ),
    )
    op.create_index(
        "ix_assistant_source_tenant_user",
        "assistant_sources",
        ["tenant_id", "user_id"],
    )

    op.create_table(
        "assistant_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("connection_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=500), nullable=False),
        sa.Column("thread_id", sa.String(length=500), nullable=True),
        sa.Column("raw_payload_hash", sa.String(length=64), nullable=False),
        sa.Column("payload_json", JSONB, nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["integration_connections.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "connection_id",
            "external_id",
            "raw_payload_hash",
            name="uq_assistant_event_dedup",
        ),
    )
    op.create_index(
        "ix_assistant_event_tenant_user",
        "assistant_events",
        ["tenant_id", "user_id"],
    )
    op.create_index(
        "ix_assistant_event_unprocessed",
        "assistant_events",
        ["processed_at"],
    )

    op.create_table(
        "assistant_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("connection_id", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(length=30), nullable=False),
        sa.Column("external_id", sa.String(length=500), nullable=False),
        sa.Column("thread_id", sa.String(length=500), nullable=True),
        sa.Column("mailbox_address", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content_snippet", sa.Text(), nullable=True),
        sa.Column("sender", sa.String(length=255), nullable=True),
        sa.Column("recipients_json", JSONB, nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=True),
        sa.Column("raw_metadata_json", JSONB, nullable=True),
        sa.Column("raw_payload_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="new",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["integration_connections.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "connection_id",
            "external_id",
            name="uq_assistant_item_ext",
        ),
    )
    op.create_index(
        "ix_assistant_item_tenant_user",
        "assistant_items",
        ["tenant_id", "user_id"],
    )
    op.create_index("ix_assistant_item_status", "assistant_items", ["status"])
    op.create_index("ix_assistant_item_occurred", "assistant_items", ["occurred_at"])

    op.create_table(
        "assistant_decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("decision_type", sa.String(length=50), nullable=False),
        sa.Column("decision_value", sa.String(length=100), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "source",
            sa.String(length=20),
            nullable=False,
            server_default="rule",
        ),
        sa.Column("metadata_json", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["item_id"], ["assistant_items.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assistant_decision_item", "assistant_decisions", ["item_id"])
    op.create_index(
        "ix_assistant_decision_tenant",
        "assistant_decisions",
        ["tenant_id", "user_id"],
    )

    op.create_table(
        "assistant_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "scope",
            sa.String(length=30),
            nullable=False,
            server_default="user",
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("match_criteria_json", JSONB, nullable=True),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("action_payload_json", JSONB, nullable=True),
        sa.Column(
            "risk_level",
            sa.String(length=10),
            nullable=False,
            server_default="low",
        ),
        sa.Column(
            "origin",
            sa.String(length=20),
            nullable=False,
            server_default="manual",
        ),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_assistant_rule_tenant_user",
        "assistant_rules",
        ["tenant_id", "user_id"],
    )
    op.create_index("ix_assistant_rule_enabled", "assistant_rules", ["enabled"])

    op.create_table(
        "assistant_actions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="suggested",
        ),
        sa.Column(
            "risk_level",
            sa.String(length=10),
            nullable=False,
            server_default="low",
        ),
        sa.Column(
            "requires_confirmation",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["item_id"], ["assistant_items.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assistant_action_item", "assistant_actions", ["item_id"])
    op.create_index("ix_assistant_action_status", "assistant_actions", ["status"])
    op.create_index(
        "ix_assistant_action_tenant",
        "assistant_actions",
        ["tenant_id", "user_id"],
    )

    op.create_table(
        "assistant_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=True),
        sa.Column("feedback_type", sa.String(length=50), nullable=False),
        sa.Column("feedback_payload_json", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["item_id"], ["assistant_items.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_assistant_feedback_tenant",
        "assistant_feedback",
        ["tenant_id", "user_id"],
    )
    op.create_index("ix_assistant_feedback_item", "assistant_feedback", ["item_id"])

    op.create_table(
        "assistant_conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "channel",
            sa.String(length=30),
            nullable=False,
            server_default="web_chat",
        ),
        sa.Column(
            "state",
            sa.String(length=20),
            nullable=False,
            server_default="active",
        ),
        sa.Column("context_json", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_assistant_conv_tenant_user",
        "assistant_conversations",
        ["tenant_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_assistant_conv_tenant_user", table_name="assistant_conversations")
    op.drop_table("assistant_conversations")

    op.drop_index("ix_assistant_feedback_item", table_name="assistant_feedback")
    op.drop_index("ix_assistant_feedback_tenant", table_name="assistant_feedback")
    op.drop_table("assistant_feedback")

    op.drop_index("ix_assistant_action_tenant", table_name="assistant_actions")
    op.drop_index("ix_assistant_action_status", table_name="assistant_actions")
    op.drop_index("ix_assistant_action_item", table_name="assistant_actions")
    op.drop_table("assistant_actions")

    op.drop_index("ix_assistant_rule_enabled", table_name="assistant_rules")
    op.drop_index("ix_assistant_rule_tenant_user", table_name="assistant_rules")
    op.drop_table("assistant_rules")

    op.drop_index("ix_assistant_decision_tenant", table_name="assistant_decisions")
    op.drop_index("ix_assistant_decision_item", table_name="assistant_decisions")
    op.drop_table("assistant_decisions")

    op.drop_index("ix_assistant_item_occurred", table_name="assistant_items")
    op.drop_index("ix_assistant_item_status", table_name="assistant_items")
    op.drop_index("ix_assistant_item_tenant_user", table_name="assistant_items")
    op.drop_table("assistant_items")

    op.drop_index("ix_assistant_event_unprocessed", table_name="assistant_events")
    op.drop_index("ix_assistant_event_tenant_user", table_name="assistant_events")
    op.drop_table("assistant_events")

    op.drop_index("ix_assistant_source_tenant_user", table_name="assistant_sources")
    op.drop_table("assistant_sources")

    op.drop_index("ix_assistant_profile_tenant", table_name="assistant_profiles")
    op.drop_table("assistant_profiles")

    op.drop_index(
        "ix_conn_cap_connection", table_name="integration_connection_capabilities"
    )
    op.drop_table("integration_connection_capabilities")

    op.drop_index("ix_integration_conn_user", table_name="integration_connections")
    op.drop_index("ix_integration_conn_tenant", table_name="integration_connections")
    op.drop_table("integration_connections")
