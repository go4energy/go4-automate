"""Multi-prompt per group with batch/each processing mode.

Revision ID: 018
Revises: 017
Create Date: 2026-02-22
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add new JSONB column for multiple prompt slugs
    op.add_column(
        "collector_groups",
        sa.Column(
            "analysis_prompt_slugs",
            JSONB,
            nullable=False,
            server_default="[]",
        ),
    )

    # 2. Migrate existing data: single slug -> array
    op.execute(
        """
        UPDATE collector_groups
        SET analysis_prompt_slugs = jsonb_build_array(analysis_prompt_slug)
        WHERE analysis_prompt_slug IS NOT NULL
        """
    )

    # 3. Drop old column
    op.drop_column("collector_groups", "analysis_prompt_slug")

    # 4. Add processing_mode to prompts table
    op.add_column(
        "prompts",
        sa.Column(
            "processing_mode",
            sa.String(10),
            nullable=False,
            server_default="batch",
        ),
    )


def downgrade() -> None:
    # 1. Re-add old column
    op.add_column(
        "collector_groups",
        sa.Column("analysis_prompt_slug", sa.String(100), nullable=True),
    )

    # 2. Migrate back: take first element of array
    op.execute(
        """
        UPDATE collector_groups
        SET analysis_prompt_slug = analysis_prompt_slugs->>0
        WHERE jsonb_array_length(analysis_prompt_slugs) > 0
        """
    )

    # 3. Drop new column
    op.drop_column("collector_groups", "analysis_prompt_slugs")

    # 4. Drop processing_mode from prompts
    op.drop_column("prompts", "processing_mode")
