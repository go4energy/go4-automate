"""Leadgen: pluggable data source + hybrid search config.

Adds to leadgen_campaigns:
- source: which data source (google_places, northdata, ...)
- source_config: JSONB with source-specific parameters (search modes,
  types/synonyms, geographic scope, max_api_calls, ...)

Adds to leadgen_places:
- source: which source the place came from
- source_record_id: source-native id (e.g. google_place_id). Kept in sync with
  the existing google_place_id column for backwards compatibility during
  transition; new source implementations use this field directly.

Revision ID: 068
Revises: 067
Create Date: 2026-04-24
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "068"
down_revision = "067"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- leadgen_campaigns ---
    op.add_column(
        "leadgen_campaigns",
        sa.Column(
            "source",
            sa.String(30),
            nullable=False,
            server_default="google_places",
        ),
    )
    op.add_column(
        "leadgen_campaigns",
        sa.Column(
            "source_config",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    # --- leadgen_places ---
    op.add_column(
        "leadgen_places",
        sa.Column(
            "source",
            sa.String(30),
            nullable=False,
            server_default="google_places",
        ),
    )
    op.add_column(
        "leadgen_places",
        sa.Column("source_record_id", sa.String(255), nullable=True),
    )
    # Backfill source_record_id from google_place_id for existing rows.
    op.execute(
        "UPDATE leadgen_places SET source_record_id = google_place_id "
        "WHERE source_record_id IS NULL"
    )
    # Not made NOT NULL to keep the door open for quelle-specific ids later.

    op.create_index(
        "ix_leadgen_places_source_record",
        "leadgen_places",
        ["tenant_id", "source", "source_record_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_leadgen_places_source_record", table_name="leadgen_places")
    op.drop_column("leadgen_places", "source_record_id")
    op.drop_column("leadgen_places", "source")
    op.drop_column("leadgen_campaigns", "source_config")
    op.drop_column("leadgen_campaigns", "source")
