"""Add utm_term and utm_content to journey_events.

Revision ID: 066
Revises: 065
Create Date: 2026-03-26
"""

import sqlalchemy as sa

from alembic import op

revision = "066"
down_revision = "065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("journey_events", sa.Column("utm_term", sa.String(100), nullable=True))
    op.add_column("journey_events", sa.Column("utm_content", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("journey_events", "utm_content")
    op.drop_column("journey_events", "utm_term")
