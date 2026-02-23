"""Add detail column to collector_topics.

Revision ID: 015
Revises: 014
Create Date: 2026-02-22
"""

import sqlalchemy as sa

from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "collector_topics",
        sa.Column("detail", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("collector_topics", "detail")
