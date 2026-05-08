"""Add skip_confirmation to assistant_profiles.

Revision ID: 062
Revises: 061
Create Date: 2026-03-17
"""

import sqlalchemy as sa

from alembic import op

revision = "062"
down_revision = "061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assistant_profiles",
        sa.Column(
            "skip_confirmation",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("assistant_profiles", "skip_confirmation")
