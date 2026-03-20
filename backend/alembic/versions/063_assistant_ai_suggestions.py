"""Add ai_suggestions_enabled to assistant_profiles.

Revision ID: 063
Revises: 062
Create Date: 2026-03-17
"""

import sqlalchemy as sa

from alembic import op

revision = "063"
down_revision = "062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assistant_profiles",
        sa.Column(
            "ai_suggestions_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("assistant_profiles", "ai_suggestions_enabled")
