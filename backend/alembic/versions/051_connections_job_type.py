"""Add connections_since_date to linkedin_scraper_jobs.

Revision ID: 051
Revises: 050
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa

revision = "051"
down_revision = "050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "linkedin_scraper_jobs",
        sa.Column("connections_since_date", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("linkedin_scraper_jobs", "connections_since_date")
