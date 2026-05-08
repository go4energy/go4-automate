"""Add UTM fields to journey_ref_codes.

Revision ID: 065
Revises: 064
Create Date: 2026-03-26
"""

import sqlalchemy as sa

from alembic import op

revision = "065"
down_revision = "064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("journey_ref_codes", sa.Column("utm_source", sa.String(100), nullable=True))
    op.add_column("journey_ref_codes", sa.Column("utm_medium", sa.String(100), nullable=True))
    op.add_column("journey_ref_codes", sa.Column("utm_campaign", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("journey_ref_codes", "utm_campaign")
    op.drop_column("journey_ref_codes", "utm_medium")
    op.drop_column("journey_ref_codes", "utm_source")
