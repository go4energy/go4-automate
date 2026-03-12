"""add scrape_full_profiles to linkedin_scraper_jobs

Revision ID: 9174f7719d75
Revises: 39a03ec9dc2e
Create Date: 2026-02-27 20:33:00.803384

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9174f7719d75'
down_revision: str | None = '39a03ec9dc2e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'linkedin_scraper_jobs',
        sa.Column('scrape_full_profiles', sa.Boolean(), server_default='false', nullable=False)
    )


def downgrade() -> None:
    op.drop_column('linkedin_scraper_jobs', 'scrape_full_profiles')
