"""Add content pipeline fields to content_pieces.

Revision ID: 003
Revises: 002
Create Date: 2026-02-17

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "content_pieces",
        sa.Column("meta_post_id", sa.String(100), nullable=True),
    )
    op.add_column(
        "content_pieces",
        sa.Column("approved_by", sa.String(100), nullable=True),
    )
    op.add_column(
        "content_pieces",
        sa.Column("approved_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "content_pieces",
        sa.Column("error_message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("content_pieces", "error_message")
    op.drop_column("content_pieces", "approved_at")
    op.drop_column("content_pieces", "approved_by")
    op.drop_column("content_pieces", "meta_post_id")
