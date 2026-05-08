"""add assistant autopilot trust settings

Revision ID: 061
Revises: 060
Create Date: 2026-03-16
"""

import sqlalchemy as sa

from alembic import op

revision = "061"
down_revision = "060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assistant_profiles",
        sa.Column(
            "autopilot_min_confidence",
            sa.Float(),
            nullable=False,
            server_default="0.85",
        ),
    )
    op.add_column(
        "assistant_profiles",
        sa.Column(
            "autopilot_max_rule_risk",
            sa.String(length=20),
            nullable=False,
            server_default="medium",
        ),
    )
    op.add_column(
        "assistant_profiles",
        sa.Column(
            "suggestion_min_confidence",
            sa.Float(),
            nullable=False,
            server_default="0.70",
        ),
    )


def downgrade() -> None:
    op.drop_column("assistant_profiles", "suggestion_min_confidence")
    op.drop_column("assistant_profiles", "autopilot_max_rule_risk")
    op.drop_column("assistant_profiles", "autopilot_min_confidence")
