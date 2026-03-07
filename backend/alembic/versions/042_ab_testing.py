"""A/B Testing for engagement module.

Revision ID: 042_ab_testing
Revises: 041_contact_activities
Create Date: 2024-03-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision: str = "042"
down_revision: Union[str, None] = "041"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A/B Tests table
    op.create_table(
        "ab_tests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pipeline_id",
            sa.Integer(),
            sa.ForeignKey("engagement_pipelines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Test configuration
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("test_type", sa.String(50), nullable=False),  # message, subject, timing, channel
        sa.Column("channel", sa.String(50), nullable=True),  # linkedin, email, etc.
        sa.Column("action_type", sa.String(100), nullable=True),  # first_contact, follow_up, etc.
        # Status
        sa.Column("status", sa.String(50), nullable=False, default="draft"),  # draft, running, paused, completed
        sa.Column("is_active", sa.Boolean(), nullable=False, default=False),
        # Targeting
        sa.Column("sample_size", sa.Integer(), nullable=True),  # Target sample size
        sa.Column("traffic_split", postgresql.JSONB(), nullable=False, default=dict),  # Variant weights
        # Timing
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        # Results
        sa.Column("winner_variant_id", sa.Integer(), nullable=True),
        sa.Column("results_summary", postgresql.JSONB(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, default=sa.func.now(), onupdate=sa.func.now()),
    )

    # A/B Test Variants table
    op.create_table(
        "ab_test_variants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ab_test_id",
            sa.Integer(),
            sa.ForeignKey("ab_tests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Variant configuration
        sa.Column("name", sa.String(100), nullable=False),  # A, B, Control, etc.
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),  # The content/message for this variant
        sa.Column("subject", sa.String(500), nullable=True),  # Subject line for emails
        sa.Column("config", postgresql.JSONB(), nullable=False, default=dict),  # Additional config
        sa.Column("weight", sa.Integer(), nullable=False, default=50),  # Traffic weight percentage
        # Statistics
        sa.Column("impressions", sa.Integer(), nullable=False, default=0),
        sa.Column("clicks", sa.Integer(), nullable=False, default=0),
        sa.Column("conversions", sa.Integer(), nullable=False, default=0),
        sa.Column("responses", sa.Integer(), nullable=False, default=0),
        # Is this the control variant?
        sa.Column("is_control", sa.Boolean(), nullable=False, default=False),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Add ab_test_variant_id to pending_actions to track which variant was used
    op.add_column(
        "pending_actions",
        sa.Column("ab_test_variant_id", sa.Integer(), sa.ForeignKey("ab_test_variants.id", ondelete="SET NULL"), nullable=True),
    )

    # Create indexes
    op.create_index("ix_ab_tests_tenant", "ab_tests", ["tenant_id"])
    op.create_index("ix_ab_tests_pipeline", "ab_tests", ["pipeline_id"])
    op.create_index("ix_ab_tests_status", "ab_tests", ["tenant_id", "status"])
    op.create_index("ix_ab_test_variants_test", "ab_test_variants", ["ab_test_id"])
    op.create_index("ix_pending_actions_ab_variant", "pending_actions", ["ab_test_variant_id"])


def downgrade() -> None:
    op.drop_index("ix_pending_actions_ab_variant", table_name="pending_actions")
    op.drop_index("ix_ab_test_variants_test", table_name="ab_test_variants")
    op.drop_index("ix_ab_tests_status", table_name="ab_tests")
    op.drop_index("ix_ab_tests_pipeline", table_name="ab_tests")
    op.drop_index("ix_ab_tests_tenant", table_name="ab_tests")
    op.drop_column("pending_actions", "ab_test_variant_id")
    op.drop_table("ab_test_variants")
    op.drop_table("ab_tests")
