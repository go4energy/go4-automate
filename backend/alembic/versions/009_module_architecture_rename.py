"""Module architecture rename: Collector, Creator, Distributor, CRM.

Revision ID: 009
Revises: 008
Create Date: 2026-02-20

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # === TABLE RENAMES ===
    op.rename_table("research_sources", "collector_sources")
    op.rename_table("research_findings", "collector_findings")
    op.rename_table("topic_suggestions", "collector_topics")
    op.rename_table("content_pieces", "creator_pieces")
    op.rename_table("content_calendar", "creator_calendar")
    op.rename_table("ad_campaigns", "distributor_campaigns")
    op.rename_table("ad_campaign_configs", "distributor_campaign_configs")
    op.rename_table("ad_performances", "distributor_performances")
    op.rename_table("conversion_events", "distributor_conversions")
    op.rename_table("leads", "crm_contacts")
    op.rename_table("email_logs", "crm_email_logs")

    # === NEW COLUMNS: collector_sources ===
    op.execute(
        "ALTER TABLE collector_sources "
        "ADD COLUMN categories JSONB NOT NULL DEFAULT '[]'"
    )
    op.add_column(
        "collector_sources",
        sa.Column(
            "change_detection_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # === NEW COLUMNS: collector_findings ===
    op.execute(
        "ALTER TABLE collector_findings "
        "ADD COLUMN categories JSONB NOT NULL DEFAULT '[]'"
    )

    # === NEW COLUMNS: collector_topics ===
    op.execute(
        "ALTER TABLE collector_topics "
        "ADD COLUMN categories JSONB NOT NULL DEFAULT '[]'"
    )
    op.execute(
        "ALTER TABLE collector_topics "
        "ADD COLUMN target_modules JSONB DEFAULT '[\"creator\"]'"
    )

    # === FK DECOUPLING: collector_topics.content_piece_id ===
    # Drop FK constraint if it exists (topic_suggestions -> content_pieces)
    op.drop_constraint(
        "topic_suggestions_content_piece_id_fkey",
        "collector_topics",
        type_="foreignkey",
    )

    # === NEW TABLE: collector_snapshots ===
    op.create_table(
        "collector_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("collector_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(), nullable=False),
        sa.Column("diff_from_previous", sa.Text(), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("change_significance", sa.String(20), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # === GIN INDEXES for JSONB category filtering ===
    op.execute(
        "CREATE INDEX ix_collector_sources_categories "
        "ON collector_sources USING GIN (categories jsonb_ops)"
    )
    op.execute(
        "CREATE INDEX ix_collector_findings_categories "
        "ON collector_findings USING GIN (categories jsonb_ops)"
    )
    op.create_index(
        "ix_collector_snapshots_source",
        "collector_snapshots",
        ["source_id", sa.text("snapshot_at DESC")],
    )

    # === DATA MIGRATION: set default categories ===
    op.execute(
        "UPDATE collector_sources SET categories = '[\"social_media\"]' "
        "WHERE source_type IN ('rss', 'website') AND name NOT LIKE 'Wettbewerber%'"
    )
    op.execute(
        "UPDATE collector_sources SET categories = '[\"competitor\"]' "
        "WHERE name LIKE 'Wettbewerber%'"
    )

    # === UPDATE FK references in crm_email_logs (leads.id -> crm_contacts.id) ===
    # The FK constraint name was auto-generated; rename is handled by ALTER TABLE RENAME


def downgrade() -> None:
    # Drop new indexes
    op.execute("DROP INDEX IF EXISTS ix_collector_sources_categories")
    op.execute("DROP INDEX IF EXISTS ix_collector_findings_categories")
    op.drop_index("ix_collector_snapshots_source", table_name="collector_snapshots")

    # Drop new table
    op.drop_table("collector_snapshots")

    # Re-add FK constraint for content_piece_id
    op.create_foreign_key(
        "topic_suggestions_content_piece_id_fkey",
        "collector_topics",
        "creator_pieces",
        ["content_piece_id"],
        ["id"],
    )

    # Drop new columns
    op.drop_column("collector_topics", "target_modules")
    op.drop_column("collector_topics", "categories")
    op.drop_column("collector_findings", "categories")
    op.drop_column("collector_sources", "change_detection_enabled")
    op.drop_column("collector_sources", "categories")

    # Rename tables back
    op.rename_table("crm_email_logs", "email_logs")
    op.rename_table("crm_contacts", "leads")
    op.rename_table("distributor_conversions", "conversion_events")
    op.rename_table("distributor_performances", "ad_performances")
    op.rename_table("distributor_campaign_configs", "ad_campaign_configs")
    op.rename_table("distributor_campaigns", "ad_campaigns")
    op.rename_table("creator_calendar", "content_calendar")
    op.rename_table("creator_pieces", "content_pieces")
    op.rename_table("collector_topics", "topic_suggestions")
    op.rename_table("collector_findings", "research_findings")
    op.rename_table("collector_sources", "research_sources")
