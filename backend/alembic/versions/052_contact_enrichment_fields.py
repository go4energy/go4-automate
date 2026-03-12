"""Add enrichment fields to linkedin_contacts.

New fields: profile_urn, connected_at, connected_at_text, interests.

Revision ID: 052
Revises: 051
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "052"
down_revision = "051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "linkedin_contacts",
        sa.Column("profile_urn", sa.String(100), nullable=True),
    )
    op.add_column(
        "linkedin_contacts",
        sa.Column("connected_at", sa.DateTime, nullable=True),
    )
    op.add_column(
        "linkedin_contacts",
        sa.Column("connected_at_text", sa.String(100), nullable=True),
    )
    op.add_column(
        "linkedin_contacts",
        sa.Column("interests", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("linkedin_contacts", "interests")
    op.drop_column("linkedin_contacts", "connected_at_text")
    op.drop_column("linkedin_contacts", "connected_at")
    op.drop_column("linkedin_contacts", "profile_urn")
