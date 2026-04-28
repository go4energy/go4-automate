"""Letter: provider/Letterxpress fields + letterhead asset.

Adds Letterxpress-specific tracking columns to ``letters`` (job id,
provider status, send mode, cost) and a letterhead background image
column to ``letter_templates``.

Revision ID: 075
Revises: 074
Create Date: 2026-04-28
"""

import sqlalchemy as sa

from alembic import op

revision = "075"
down_revision = "074"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "letter_templates",
        sa.Column("letterhead_image_url", sa.String(500), nullable=True),
    )
    op.add_column(
        "letter_templates",
        sa.Column("css_styles", sa.Text(), nullable=True),
    )

    op.add_column(
        "letters",
        sa.Column("letterxpress_job_id", sa.String(100), nullable=True),
    )
    op.add_column(
        "letters",
        sa.Column(
            "send_mode",
            sa.String(10),
            nullable=False,
            server_default="test",
        ),
    )
    op.add_column(
        "letters",
        sa.Column("provider_status", sa.String(50), nullable=True),
    )
    op.add_column(
        "letters",
        sa.Column("provider_cost_cents", sa.Integer(), nullable=True),
    )
    op.add_column(
        "letters",
        sa.Column("provider_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_letters_letterxpress_job",
        "letters",
        ["letterxpress_job_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_letters_letterxpress_job", table_name="letters")
    op.drop_column("letters", "provider_synced_at")
    op.drop_column("letters", "provider_cost_cents")
    op.drop_column("letters", "provider_status")
    op.drop_column("letters", "send_mode")
    op.drop_column("letters", "letterxpress_job_id")
    op.drop_column("letter_templates", "css_styles")
    op.drop_column("letter_templates", "letterhead_image_url")
