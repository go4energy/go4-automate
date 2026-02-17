"""content_pieces, content_calendar, ad_campaigns

Revision ID: 002
Revises: 001
Create Date: 2026-02-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Content Pieces
    op.create_table(
        "content_pieces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("topic", sa.String(200), nullable=True),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("short", sa.Text(), nullable=True),
        sa.Column("hashtags", sa.Text(), nullable=True),
        sa.Column("hook", sa.Text(), nullable=True),
        sa.Column("cta", sa.String(300), nullable=True),
        sa.Column("media_urls", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="'draft'"),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("posted_at", sa.DateTime(), nullable=True),
        sa.Column("funnel_stage", sa.String(50), nullable=True),
        sa.Column("buyer_persona", sa.String(100), nullable=True),
        sa.Column("reach", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("engagement", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("engagement_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("link_clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leads_generated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("ai_model", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_content_pieces_tenant_status",
        "content_pieces",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_content_pieces_tenant_platform",
        "content_pieces",
        ["tenant_id", "platform"],
    )

    # Content Calendar
    op.create_table(
        "content_calendar",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "content_id",
            sa.Integer(),
            sa.ForeignKey("content_pieces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(), nullable=False),
        sa.Column("time_slot", sa.String(50), nullable=True),
        sa.Column("is_posted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("posted_platform_id", sa.String(200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_content_calendar_tenant_scheduled",
        "content_calendar",
        ["tenant_id", "scheduled_at"],
    )

    # Ad Campaigns
    op.create_table(
        "ad_campaigns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("platform_campaign_id", sa.String(200), nullable=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("objective", sa.String(100), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="'draft'"),
        sa.Column("daily_budget", sa.Numeric(10, 2), nullable=True),
        sa.Column("total_budget", sa.Numeric(10, 2), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("spend", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ctr", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("cpc", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("conversions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "cost_per_lead", sa.Numeric(10, 2), nullable=False, server_default="0"
        ),
        sa.Column("roas", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_ad_campaigns_tenant_status",
        "ad_campaigns",
        ["tenant_id", "status"],
    )

    # Add ad_campaign_id FK to ad_performances
    op.add_column(
        "ad_performances",
        sa.Column(
            "ad_campaign_id",
            sa.Integer(),
            sa.ForeignKey("ad_campaigns.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Drop old content_queue table
    op.drop_table("content_queue")


def downgrade() -> None:
    # Recreate content_queue
    op.create_table(
        "content_queue",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("image_prompt", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="'draft'"),
        sa.Column("engagement_data", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_content_queue_tenant_scheduled",
        "content_queue",
        ["tenant_id", "scheduled_at"],
    )

    # Remove ad_campaign_id from ad_performances
    op.drop_column("ad_performances", "ad_campaign_id")

    # Drop new tables
    op.drop_table("ad_campaigns")
    op.drop_table("content_calendar")
    op.drop_table("content_pieces")
