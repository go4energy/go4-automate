"""Add prompt_slug column to collector_topics.

Revision ID: 016
Revises: 015
Create Date: 2026-02-22
"""

import sqlalchemy as sa

from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "collector_topics",
        sa.Column("prompt_slug", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("collector_topics", "prompt_slug")
