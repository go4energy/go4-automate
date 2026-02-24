"""Briefing per user — user_id on sources/channels, cloned_from_id, partial unique slugs.

Revision ID: 020
Revises: 019
Create Date: 2026-02-24
"""

import sqlalchemy as sa

from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- briefing_sources: add user_id ---
    op.add_column(
        "briefing_sources",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_briefing_sources_tenant_user",
        "briefing_sources",
        ["tenant_id", "user_id"],
    )

    # --- briefing_channels: add user_id + cloned_from_id ---
    op.add_column(
        "briefing_channels",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.add_column(
        "briefing_channels",
        sa.Column(
            "cloned_from_id",
            sa.Integer(),
            sa.ForeignKey("briefing_channels.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_briefing_channels_tenant_user",
        "briefing_channels",
        ["tenant_id", "user_id"],
    )

    # Replace slug unique constraint with partial uniques
    op.drop_constraint(
        "uq_briefing_channels_tenant_slug", "briefing_channels", type_="unique"
    )
    # Org-level: slug unique per tenant where user_id IS NULL
    op.execute(
        "CREATE UNIQUE INDEX uq_briefing_channels_org_slug "
        "ON briefing_channels (tenant_id, slug) WHERE user_id IS NULL"
    )
    # User-level: slug unique per (tenant, user) where user_id IS NOT NULL
    op.execute(
        "CREATE UNIQUE INDEX uq_briefing_channels_user_slug "
        "ON briefing_channels (tenant_id, user_id, slug) WHERE user_id IS NOT NULL"
    )


def downgrade() -> None:
    # Drop partial unique indexes
    op.execute("DROP INDEX IF EXISTS uq_briefing_channels_user_slug")
    op.execute("DROP INDEX IF EXISTS uq_briefing_channels_org_slug")

    # Restore original unique constraint
    op.create_unique_constraint(
        "uq_briefing_channels_tenant_slug",
        "briefing_channels",
        ["tenant_id", "slug"],
    )

    # Drop indexes
    op.drop_index("ix_briefing_channels_tenant_user", "briefing_channels")
    op.drop_index("ix_briefing_sources_tenant_user", "briefing_sources")

    # Drop columns
    op.drop_column("briefing_channels", "cloned_from_id")
    op.drop_column("briefing_channels", "user_id")
    op.drop_column("briefing_sources", "user_id")
