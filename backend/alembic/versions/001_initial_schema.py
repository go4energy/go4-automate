"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Tenants
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(50), nullable=False, unique=True),
        sa.Column("tenant_name", sa.String(200), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
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
    op.create_index("ix_tenants_tenant_id", "tenants", ["tenant_id"])

    # Leads
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="'new'"),
        sa.Column("konfigurator_data", postgresql.JSONB(), nullable=True),
        sa.Column("followup_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "followup_paused",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
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
    op.create_index("ix_leads_status", "leads", ["status"])
    op.create_index("ix_leads_tenant_status", "leads", ["tenant_id", "status"])

    # Content Queue
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

    # Email Logs
    op.create_table(
        "email_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "lead_id",
            sa.Integer(),
            sa.ForeignKey("leads.id"),
            nullable=False,
        ),
        sa.Column("email_type", sa.String(50), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="'pending'"),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("opened_at", sa.DateTime(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
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

    # Ad Performances
    op.create_table(
        "ad_performances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("campaign_id", sa.String(200), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("spend", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("leads", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cpl", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
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
        "ix_ad_performance_tenant_date",
        "ad_performances",
        ["tenant_id", "date"],
    )


def downgrade() -> None:
    op.drop_table("ad_performances")
    op.drop_table("email_logs")
    op.drop_table("content_queue")
    op.drop_table("leads")
    op.drop_table("tenants")
