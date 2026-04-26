"""Leadgen: enrichment_flags JSONB on places.

Generic bag for sales-relevant signals discovered during enrichment that don't
fit on the LLM insights row (which the LLM owns). Examples:

- homepage_not_in_google: bool — Serper found a homepage that Google Places
  didn't have. Useful as a sales angle ("your site isn't on Google").
- no_calendar_in_google: bool — opt-in heuristic per campaign; flagged when
  the Places payload has no booking/appointment indicator.
- serper_checked_at: ISO timestamp — idempotency marker so the verify stage
  doesn't redo the work on resumed runs.

Revision ID: 070
Revises: 069
Create Date: 2026-04-26
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "070"
down_revision = "069"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leadgen_places",
        sa.Column(
            "enrichment_flags",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("leadgen_places", "enrichment_flags")
