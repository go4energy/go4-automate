"""Engagement pipelines table.

Revision ID: 038
Revises: 037
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "engagement_pipelines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(50), nullable=False),
        # Basic Info
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        # Product Info
        sa.Column("product_name", sa.String(200), nullable=True),
        sa.Column("product_description", sa.Text(), nullable=True),
        sa.Column("target_audience", sa.Text(), nullable=True),
        # Configuration
        sa.Column("channels", JSONB, nullable=False, server_default="[]"),
        sa.Column("goal", sa.String(100), nullable=True),
        sa.Column("playbook", sa.Text(), nullable=True),
        sa.Column("tone_of_voice", sa.String(50), server_default="professionell"),
        sa.Column("min_days_between_touches", sa.Integer(), server_default="3"),
        sa.Column("auto_actions", JSONB, nullable=False, server_default="{}"),
        # Status
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        # Keys
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_engagement_pipelines_tenant_slug"),
    )

    op.create_index("ix_engagement_pipelines_tenant", "engagement_pipelines", ["tenant_id"])
    op.create_index("ix_engagement_pipelines_active", "engagement_pipelines", ["tenant_id", "is_active"])


def downgrade() -> None:
    op.drop_index("ix_engagement_pipelines_active", table_name="engagement_pipelines")
    op.drop_index("ix_engagement_pipelines_tenant", table_name="engagement_pipelines")
    op.drop_table("engagement_pipelines")
