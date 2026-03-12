"""Add last_error to email_campaigns for worker error tracking.

Revision ID: 031
Revises: 030
Create Date: 2025-03-04

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add last_error column to email_campaigns
    op.add_column(
        "email_campaigns",
        sa.Column("last_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("email_campaigns", "last_error")
