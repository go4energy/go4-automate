"""Tags system — tags table + rename categories to tags on existing models.

Revision ID: 011
Revises: 010
Create Date: 2026-02-21
"""

import sqlalchemy as sa

from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create tags table
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("color", sa.String(7), nullable=False, server_default="#6B7280"),
        sa.Column("icon", sa.String(50), nullable=True),
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
        sa.UniqueConstraint("tenant_id", "slug", name="uq_tags_tenant_slug"),
        sa.Index("ix_tags_tenant", "tenant_id"),
    )

    # 2. Rename categories → tags on collector_sources
    op.alter_column(
        "collector_sources",
        "categories",
        new_column_name="tags",
    )

    # 3. Rename categories → tags on collector_findings
    op.alter_column(
        "collector_findings",
        "categories",
        new_column_name="tags",
    )

    # 4. Rename categories → tags on collector_topics
    op.alter_column(
        "collector_topics",
        "categories",
        new_column_name="tags",
    )

    # 5. Rename categories → tags on briefing_channels
    op.alter_column(
        "briefing_channels",
        "categories",
        new_column_name="tags",
    )

    # 6. Add GIN indexes on JSONB tags columns for fast overlap queries
    op.create_index(
        "ix_collector_sources_tags_gin",
        "collector_sources",
        ["tags"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_collector_findings_tags_gin",
        "collector_findings",
        ["tags"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_collector_topics_tags_gin",
        "collector_topics",
        ["tags"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_briefing_channels_tags_gin",
        "briefing_channels",
        ["tags"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    # Drop GIN indexes
    op.drop_index("ix_briefing_channels_tags_gin", table_name="briefing_channels")
    op.drop_index("ix_collector_topics_tags_gin", table_name="collector_topics")
    op.drop_index("ix_collector_findings_tags_gin", table_name="collector_findings")
    op.drop_index("ix_collector_sources_tags_gin", table_name="collector_sources")

    # Rename tags → categories
    op.alter_column("briefing_channels", "tags", new_column_name="categories")
    op.alter_column("collector_topics", "tags", new_column_name="categories")
    op.alter_column("collector_findings", "tags", new_column_name="categories")
    op.alter_column("collector_sources", "tags", new_column_name="categories")

    # Drop tags table
    op.drop_table("tags")
