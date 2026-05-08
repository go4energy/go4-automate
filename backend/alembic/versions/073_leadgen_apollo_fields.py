"""Leadgen: Apollo enrichment columns on ``leadgen_contacts``.

Tracks per-contact whether Apollo's people_match has run, the match quality
Apollo reported back (``high``/``medium``/``low``/``no_match``), and the
credits consumed for that lookup. Lets the worker stage be idempotent (skip
contacts already seen) and lets us aggregate spend per run.

Revision ID: 073
Revises: 072
Create Date: 2026-04-27
"""

import sqlalchemy as sa

from alembic import op

revision = "073"
down_revision = "072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leadgen_contacts",
        sa.Column("apollo_enriched_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "leadgen_contacts",
        sa.Column("apollo_match_quality", sa.String(20), nullable=True),
    )
    op.add_column(
        "leadgen_contacts",
        sa.Column(
            "apollo_credits_used",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    # Partial index: cheaply find contacts that still need Apollo enrichment.
    op.create_index(
        "ix_leadgen_contacts_apollo_pending",
        "leadgen_contacts",
        ["tenant_id", "place_id"],
        postgresql_where=sa.text("apollo_enriched_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_leadgen_contacts_apollo_pending", table_name="leadgen_contacts"
    )
    op.drop_column("leadgen_contacts", "apollo_credits_used")
    op.drop_column("leadgen_contacts", "apollo_match_quality")
    op.drop_column("leadgen_contacts", "apollo_enriched_at")
