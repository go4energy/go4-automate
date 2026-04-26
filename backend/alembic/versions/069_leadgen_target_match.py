"""Leadgen: target-match score + structured primary contact.

Renames the legacy "pv_relevance" naming to "target_match" so the score
correctly reflects "matches the campaign's target profile" (not specifically
PV) and adds a structured primary_contact JSONB on llm_insights so the
downstream mail/letter module can address the right person directly.

Adds:
- leadgen_llm_insights.primary_contact (JSONB nullable)

Renames (data preserved):
- leadgen_campaigns.pv_relevance_threshold -> target_match_threshold
- leadgen_llm_insights.pv_relevance_score  -> target_match_score

Revision ID: 069
Revises: 068
Create Date: 2026-04-25
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "069"
down_revision = "068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "leadgen_campaigns",
        "pv_relevance_threshold",
        new_column_name="target_match_threshold",
    )
    op.alter_column(
        "leadgen_llm_insights",
        "pv_relevance_score",
        new_column_name="target_match_score",
    )
    op.add_column(
        "leadgen_llm_insights",
        sa.Column("primary_contact", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("leadgen_llm_insights", "primary_contact")
    op.alter_column(
        "leadgen_llm_insights",
        "target_match_score",
        new_column_name="pv_relevance_score",
    )
    op.alter_column(
        "leadgen_campaigns",
        "target_match_threshold",
        new_column_name="pv_relevance_threshold",
    )
