"""add_linkedin_contact_fields

Revision ID: 70a1aa8c0ef5
Revises: 027
Create Date: 2026-02-27 16:12:47.559136

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '70a1aa8c0ef5'
down_revision: str | None = '027'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add new fields to linkedin_contacts
    op.add_column('linkedin_contacts', sa.Column('contact_degree', sa.Integer(), nullable=True))
    op.add_column('linkedin_contacts', sa.Column('is_premium', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('linkedin_contacts', sa.Column('gender', sa.String(length=20), nullable=True))
    op.add_column('linkedin_contacts', sa.Column('is_followed', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('linkedin_contacts', sa.Column('follower_count', sa.Integer(), nullable=True))
    op.add_column('linkedin_contacts', sa.Column('connection_count', sa.Integer(), nullable=True))
    op.add_column('linkedin_contacts', sa.Column('website', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('linkedin_contacts', 'website')
    op.drop_column('linkedin_contacts', 'connection_count')
    op.drop_column('linkedin_contacts', 'follower_count')
    op.drop_column('linkedin_contacts', 'is_followed')
    op.drop_column('linkedin_contacts', 'gender')
    op.drop_column('linkedin_contacts', 'is_premium')
    op.drop_column('linkedin_contacts', 'contact_degree')
