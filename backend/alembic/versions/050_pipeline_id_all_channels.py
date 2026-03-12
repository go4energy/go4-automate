"""Add pipeline_id to all channel campaign tables.

Revision ID: 050
Revises: 049
"""

import sqlalchemy as sa
from alembic import op

revision = "050"
down_revision = "049"
branch_labels = None
depends_on = None

# Tables that need pipeline_id FK to engagement_pipelines
TABLES_TO_ADD = [
    "email_campaigns",
    "email_sequences",
    "whatsapp_campaigns",
    "linkedin_campaigns",
    "campaigns",
]


def upgrade() -> None:
    # Add pipeline_id to all channel campaign tables
    for table in TABLES_TO_ADD:
        op.add_column(
            table,
            sa.Column(
                "pipeline_id",
                sa.Integer(),
                sa.ForeignKey("engagement_pipelines.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index(f"ix_{table}_pipeline_id", table, ["pipeline_id"])

    # Fix postmail_letters: add proper FK constraint (column exists but no FK)
    op.create_foreign_key(
        "fk_postmail_letters_pipeline",
        "postmail_letters",
        "engagement_pipelines",
        ["pipeline_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_postmail_letters_pipeline_id",
        "postmail_letters",
        ["pipeline_id"],
    )


def downgrade() -> None:
    # Remove postmail FK and index
    op.drop_constraint("fk_postmail_letters_pipeline", "postmail_letters", type_="foreignkey")
    op.drop_index("ix_postmail_letters_pipeline_id", table_name="postmail_letters")

    # Remove pipeline_id from all tables
    for table in reversed(TABLES_TO_ADD):
        op.drop_index(f"ix_{table}_pipeline_id", table_name=table)
        op.drop_column(table, "pipeline_id")
