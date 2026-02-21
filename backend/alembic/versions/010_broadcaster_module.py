"""Broadcaster module — channels, episodes, listener users, subscriptions, feedback, external feeds.

Revision ID: 010
Revises: 009
Create Date: 2026-02-21
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- briefing_channels ---
    op.create_table(
        "briefing_channels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("target_audience", sa.String(200)),
        sa.Column("categories", JSONB, server_default="[]"),
        sa.Column("schedule", sa.String(50)),
        sa.Column(
            "voice",
            sa.String(100),
            server_default="de_DE-thorsten-high",
            nullable=False,
        ),
        sa.Column("language", sa.String(10), server_default="de", nullable=False),
        sa.Column("intro_text", sa.Text()),
        sa.Column("outro_text", sa.Text()),
        sa.Column(
            "personal_context_enabled",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("max_items", sa.Integer(), server_default="10", nullable=False),
        sa.Column(
            "max_duration_minutes", sa.Integer(), server_default="5", nullable=False
        ),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("cover_image_url", sa.String(500)),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "tenant_id", "slug", name="uq_briefing_channels_tenant_slug"
        ),
    )
    op.create_index("ix_briefing_channels_tenant", "briefing_channels", ["tenant_id"])

    # --- briefing_episodes ---
    op.create_table(
        "briefing_episodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "channel_id",
            sa.Integer(),
            sa.ForeignKey("briefing_channels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("transcript", sa.Text()),
        sa.Column("summary", sa.Text()),
        sa.Column("audio_url", sa.String(500)),
        sa.Column("audio_duration_seconds", sa.Integer()),
        sa.Column("audio_size_bytes", sa.BigInteger()),
        sa.Column(
            "audio_mime_type",
            sa.String(50),
            server_default="audio/wav",
            nullable=False,
        ),
        sa.Column("findings_used", JSONB),
        sa.Column("status", sa.String(20), server_default="generating", nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("generated_at", sa.DateTime()),
        sa.Column("published_at", sa.DateTime()),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_briefing_episodes_channel",
        "briefing_episodes",
        ["channel_id", "published_at"],
    )
    op.create_index("ix_briefing_episodes_status", "briefing_episodes", ["status"])

    # --- listener_users ---
    op.create_table(
        "listener_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column("email", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(100)),
        sa.Column("role", sa.String(50)),
        sa.Column("preferences", JSONB, server_default="{}"),
        sa.Column("personal_webhook_url", sa.String(500)),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_login_at", sa.DateTime()),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "tenant_id", "email", name="uq_listener_users_tenant_email"
        ),
    )
    op.create_index("ix_listener_users_email", "listener_users", ["tenant_id", "email"])

    # --- listener_subscriptions ---
    op.create_table(
        "listener_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("listener_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "channel_id",
            sa.Integer(),
            sa.ForeignKey("briefing_channels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("subscribed_at", sa.DateTime()),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id", "channel_id", name="uq_listener_subscriptions_user_channel"
        ),
    )

    # --- listener_feedback ---
    op.create_table(
        "listener_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("listener_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "episode_id",
            sa.Integer(),
            sa.ForeignKey("briefing_episodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("finding_id", sa.Integer()),
        sa.Column("rating", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id",
            "episode_id",
            "finding_id",
            name="uq_listener_feedback_user_episode_finding",
        ),
    )
    op.create_index("ix_listener_feedback_user", "listener_feedback", ["user_id"])
    op.create_index("ix_listener_feedback_episode", "listener_feedback", ["episode_id"])

    # --- listener_external_feeds ---
    op.create_table(
        "listener_external_feeds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("listener_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("listener_external_feeds")
    op.drop_table("listener_feedback")
    op.drop_table("listener_subscriptions")
    op.drop_table("listener_users")
    op.drop_table("briefing_episodes")
    op.drop_table("briefing_channels")
