"""Add analysis_prompt_slug column to collector_groups.

Revision ID: 017
Revises: 016
Create Date: 2026-02-22
"""

import sqlalchemy as sa

from alembic import op

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "collector_groups",
        sa.Column("analysis_prompt_slug", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("collector_groups", "analysis_prompt_slug")
