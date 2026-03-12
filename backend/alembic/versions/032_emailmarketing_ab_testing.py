"""Add A/B testing fields to email campaigns and recipients.

Revision ID: 032
Revises: 031
Create Date: 2025-03-04

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A/B Testing fields for email_campaigns
    op.add_column(
        "email_campaigns",
        sa.Column("ab_test_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "email_campaigns",
        sa.Column("ab_variant_b_subject", sa.String(500), nullable=True),
    )
    op.add_column(
        "email_campaigns",
        sa.Column("ab_variant_b_html", sa.Text(), nullable=True),
    )
    op.add_column(
        "email_campaigns",
        sa.Column("ab_split_percentage", sa.Integer(), nullable=False, server_default="50"),
    )
    op.add_column(
        "email_campaigns",
        sa.Column("ab_winner_metric", sa.String(20), nullable=False, server_default="'open_rate'"),
    )
    op.add_column(
        "email_campaigns",
        sa.Column("ab_winner_variant", sa.String(1), nullable=True),
    )

    # A/B Stats for email_campaigns
    op.add_column(
        "email_campaigns",
        sa.Column("ab_a_sent", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "email_campaigns",
        sa.Column("ab_a_opened", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "email_campaigns",
        sa.Column("ab_a_clicked", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "email_campaigns",
        sa.Column("ab_b_sent", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "email_campaigns",
        sa.Column("ab_b_opened", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "email_campaigns",
        sa.Column("ab_b_clicked", sa.Integer(), nullable=False, server_default="0"),
    )

    # A/B variant for email_recipients
    op.add_column(
        "email_recipients",
        sa.Column("ab_variant", sa.String(1), nullable=True),
    )


def downgrade() -> None:
    # Remove from email_recipients
    op.drop_column("email_recipients", "ab_variant")

    # Remove from email_campaigns
    op.drop_column("email_campaigns", "ab_b_clicked")
    op.drop_column("email_campaigns", "ab_b_opened")
    op.drop_column("email_campaigns", "ab_b_sent")
    op.drop_column("email_campaigns", "ab_a_clicked")
    op.drop_column("email_campaigns", "ab_a_opened")
    op.drop_column("email_campaigns", "ab_a_sent")
    op.drop_column("email_campaigns", "ab_winner_variant")
    op.drop_column("email_campaigns", "ab_winner_metric")
    op.drop_column("email_campaigns", "ab_split_percentage")
    op.drop_column("email_campaigns", "ab_variant_b_html")
    op.drop_column("email_campaigns", "ab_variant_b_subject")
    op.drop_column("email_campaigns", "ab_test_enabled")
