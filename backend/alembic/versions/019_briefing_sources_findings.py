"""Briefing module — sources, findings, channel-source linking, output format.

Revision ID: 019
Revises: 018
Create Date: 2026-02-23
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- briefing_sources ---
    op.create_table(
        "briefing_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("keywords", JSONB, nullable=False, server_default="[]"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "fetch_interval_hours", sa.Integer(), nullable=False, server_default="24"
        ),
        sa.Column("last_fetched_at", sa.DateTime(), nullable=True),
        sa.Column("config", JSONB, nullable=True),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("streams", JSONB, nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_briefing_sources_tenant_active",
        "briefing_sources",
        ["tenant_id", "active"],
    )
    op.create_index(
        "ix_briefing_sources_tenant_type",
        "briefing_sources",
        ["tenant_id", "source_type"],
    )
    op.execute(
        "CREATE INDEX ix_briefing_sources_tags ON briefing_sources USING gin (tags)"
    )
    op.execute(
        "CREATE INDEX ix_briefing_sources_streams ON briefing_sources USING gin (streams)"
    )

    # --- briefing_findings ---
    op.create_table(
        "briefing_findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("briefing_sources.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("content_snippet", sa.Text(), nullable=True),
        sa.Column("found_at", sa.DateTime(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
        sa.Column("source_type", sa.String(30), nullable=True),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("streams", JSONB, nullable=False, server_default="[]"),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_unique_constraint(
        "uq_briefing_findings_tenant_url",
        "briefing_findings",
        ["tenant_id", "url"],
    )
    op.create_index(
        "ix_briefing_findings_tenant_status",
        "briefing_findings",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_briefing_findings_tenant_source",
        "briefing_findings",
        ["tenant_id", "source_id"],
    )
    op.execute(
        "CREATE INDEX ix_briefing_findings_tags ON briefing_findings USING gin (tags)"
    )
    op.execute(
        "CREATE INDEX ix_briefing_findings_streams ON briefing_findings USING gin (streams)"
    )

    # --- briefing_channel_sources (many-to-many) ---
    op.create_table(
        "briefing_channel_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "channel_id",
            sa.Integer(),
            sa.ForeignKey("briefing_channels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("briefing_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_briefing_channel_sources_channel_source",
        "briefing_channel_sources",
        ["channel_id", "source_id"],
    )

    # --- New columns on briefing_channels ---
    op.add_column(
        "briefing_channels",
        sa.Column(
            "output_format",
            sa.String(20),
            nullable=False,
            server_default="audio",
        ),
    )
    op.add_column(
        "briefing_channels",
        sa.Column(
            "text_format",
            sa.String(20),
            nullable=False,
            server_default="markdown",
        ),
    )

    # --- New columns on briefing_episodes ---
    op.add_column(
        "briefing_episodes",
        sa.Column("text_content", sa.Text(), nullable=True),
    )
    op.add_column(
        "briefing_episodes",
        sa.Column(
            "output_format",
            sa.String(20),
            nullable=False,
            server_default="audio",
        ),
    )


def downgrade() -> None:
    # Drop new episode columns
    op.drop_column("briefing_episodes", "output_format")
    op.drop_column("briefing_episodes", "text_content")

    # Drop new channel columns
    op.drop_column("briefing_channels", "text_format")
    op.drop_column("briefing_channels", "output_format")

    # Drop linking table
    op.drop_table("briefing_channel_sources")

    # Drop findings
    op.drop_table("briefing_findings")

    # Drop sources
    op.drop_table("briefing_sources")
