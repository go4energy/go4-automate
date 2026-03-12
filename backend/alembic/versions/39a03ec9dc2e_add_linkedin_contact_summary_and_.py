"""add linkedin contact summary and languages

Revision ID: 39a03ec9dc2e
Revises: 70a1aa8c0ef5
Create Date: 2026-02-27 17:39:29.598756

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '39a03ec9dc2e'
down_revision: str | None = '70a1aa8c0ef5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('linkedin_contacts', sa.Column('summary', sa.Text(), nullable=True))
    op.add_column('linkedin_contacts', sa.Column('languages', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('linkedin_contacts', 'languages')
    op.drop_column('linkedin_contacts', 'summary')
