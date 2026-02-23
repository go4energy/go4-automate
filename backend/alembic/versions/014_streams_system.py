"""Streams system — streams table + streams JSONB column on module tables.

Revision ID: 014
Revises: 013
Create Date: 2026-02-22
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create streams table
    op.create_table(
        "streams",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("color", sa.String(7), nullable=False, server_default="#3B82F6"),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_streams_tenant_slug"),
        sa.Index("ix_streams_tenant", "tenant_id"),
    )

    # 2. Add streams JSONB column to collector tables
    for table in [
        "collector_groups",
        "collector_sources",
        "collector_findings",
        "collector_topics",
    ]:
        op.add_column(
            table,
            sa.Column("streams", JSONB, nullable=False, server_default="[]"),
        )
        op.create_index(
            f"ix_{table}_streams_gin",
            table,
            ["streams"],
            postgresql_using="gin",
        )

    # 3. Add streams JSONB column to briefing_channels
    op.add_column(
        "briefing_channels",
        sa.Column("streams", JSONB, nullable=False, server_default="[]"),
    )
    op.create_index(
        "ix_briefing_channels_streams_gin",
        "briefing_channels",
        ["streams"],
        postgresql_using="gin",
    )

    # 4. Add tags + streams JSONB columns to creator_pieces
    op.add_column(
        "creator_pieces",
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
    )
    op.add_column(
        "creator_pieces",
        sa.Column("streams", JSONB, nullable=False, server_default="[]"),
    )
    op.create_index(
        "ix_creator_pieces_tags_gin",
        "creator_pieces",
        ["tags"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_creator_pieces_streams_gin",
        "creator_pieces",
        ["streams"],
        postgresql_using="gin",
    )

    # 5. Add tags + streams JSONB columns to distributor_campaigns
    op.add_column(
        "distributor_campaigns",
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
    )
    op.add_column(
        "distributor_campaigns",
        sa.Column("streams", JSONB, nullable=False, server_default="[]"),
    )
    op.create_index(
        "ix_distributor_campaigns_tags_gin",
        "distributor_campaigns",
        ["tags"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_distributor_campaigns_streams_gin",
        "distributor_campaigns",
        ["streams"],
        postgresql_using="gin",
    )

    # 6. Add tags + streams JSONB columns to distributor_campaign_configs
    op.add_column(
        "distributor_campaign_configs",
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
    )
    op.add_column(
        "distributor_campaign_configs",
        sa.Column("streams", JSONB, nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    # Drop columns from distributor_campaign_configs
    op.drop_column("distributor_campaign_configs", "streams")
    op.drop_column("distributor_campaign_configs", "tags")

    # Drop GIN indexes and columns from distributor_campaigns
    op.drop_index(
        "ix_distributor_campaigns_streams_gin", table_name="distributor_campaigns"
    )
    op.drop_index(
        "ix_distributor_campaigns_tags_gin", table_name="distributor_campaigns"
    )
    op.drop_column("distributor_campaigns", "streams")
    op.drop_column("distributor_campaigns", "tags")

    # Drop GIN indexes and columns from creator_pieces
    op.drop_index("ix_creator_pieces_streams_gin", table_name="creator_pieces")
    op.drop_index("ix_creator_pieces_tags_gin", table_name="creator_pieces")
    op.drop_column("creator_pieces", "streams")
    op.drop_column("creator_pieces", "tags")

    # Drop streams from briefing_channels
    op.drop_index("ix_briefing_channels_streams_gin", table_name="briefing_channels")
    op.drop_column("briefing_channels", "streams")

    # Drop streams from collector tables
    for table in [
        "collector_topics",
        "collector_findings",
        "collector_sources",
        "collector_groups",
    ]:
        op.drop_index(f"ix_{table}_streams_gin", table_name=table)
        op.drop_column(table, "streams")

    # Drop streams table
    op.drop_table("streams")
