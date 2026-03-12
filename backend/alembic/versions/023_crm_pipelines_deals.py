"""CRM pipelines, deals, activities, and tasks.

Revision ID: 023
Revises: 022
Create Date: 2026-02-25
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create pipelines table
    op.create_table(
        "crm_pipelines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
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
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_crm_pipelines_tenant", "crm_pipelines", ["tenant_id"])

    # Create pipeline stages table
    op.create_table(
        "crm_pipeline_stages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "pipeline_id",
            sa.Integer(),
            sa.ForeignKey("crm_pipelines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("probability", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("color", sa.String(20), nullable=False, server_default="'#6B7280'"),
        sa.Column("is_won", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_lost", sa.Boolean(), nullable=False, server_default="false"),
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
            onupdate=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_crm_pipeline_stages_pipeline",
        "crm_pipeline_stages",
        ["pipeline_id", "position"],
    )

    # Create deals table
    op.create_table(
        "crm_deals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "contact_id",
            sa.Integer(),
            sa.ForeignKey("contacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "pipeline_id",
            sa.Integer(),
            sa.ForeignKey("crm_pipelines.id"),
            nullable=False,
        ),
        sa.Column(
            "stage_id",
            sa.Integer(),
            sa.ForeignKey("crm_pipeline_stages.id"),
            nullable=False,
        ),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Deal info
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("value", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="'EUR'"),
        sa.Column("probability", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expected_close", sa.Date(), nullable=True),
        # Status
        sa.Column("status", sa.String(20), nullable=False, server_default="'open'"),
        sa.Column("lost_reason", sa.String(500), nullable=True),
        sa.Column("won_at", sa.DateTime(), nullable=True),
        sa.Column("lost_at", sa.DateTime(), nullable=True),
        # Priority & Tags
        sa.Column("priority", sa.String(20), nullable=False, server_default="'medium'"),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        # Notes & Custom
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("custom_fields", JSONB, nullable=False, server_default="{}"),
        # Timestamps
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
            onupdate=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_crm_deals_tenant_pipeline_stage",
        "crm_deals",
        ["tenant_id", "pipeline_id", "stage_id"],
    )
    op.create_index(
        "ix_crm_deals_tenant_status", "crm_deals", ["tenant_id", "status"]
    )

    # Create activities table
    op.create_table(
        "crm_activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "contact_id",
            sa.Integer(),
            sa.ForeignKey("contacts.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "deal_id",
            sa.Integer(),
            sa.ForeignKey("crm_deals.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("activity_type", sa.String(30), nullable=False),
        sa.Column("subject", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("activity_date", sa.DateTime(), nullable=False),
        sa.Column("metadata", JSONB, nullable=True),
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
            onupdate=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_crm_activities_tenant_contact",
        "crm_activities",
        ["tenant_id", "contact_id"],
    )
    op.create_index(
        "ix_crm_activities_tenant_deal", "crm_activities", ["tenant_id", "deal_id"]
    )

    # Create tasks table
    op.create_table(
        "crm_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "contact_id",
            sa.Integer(),
            sa.ForeignKey("contacts.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "deal_id",
            sa.Integer(),
            sa.ForeignKey("crm_deals.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "assigned_to",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("priority", sa.String(20), nullable=False, server_default="'medium'"),
        sa.Column("status", sa.String(20), nullable=False, server_default="'open'"),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
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
            onupdate=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_crm_tasks_tenant_status", "crm_tasks", ["tenant_id", "status"]
    )
    op.create_index(
        "ix_crm_tasks_tenant_assigned", "crm_tasks", ["tenant_id", "assigned_to"]
    )


def downgrade() -> None:
    op.drop_index("ix_crm_tasks_tenant_assigned", "crm_tasks")
    op.drop_index("ix_crm_tasks_tenant_status", "crm_tasks")
    op.drop_table("crm_tasks")

    op.drop_index("ix_crm_activities_tenant_deal", "crm_activities")
    op.drop_index("ix_crm_activities_tenant_contact", "crm_activities")
    op.drop_table("crm_activities")

    op.drop_index("ix_crm_deals_tenant_status", "crm_deals")
    op.drop_index("ix_crm_deals_tenant_pipeline_stage", "crm_deals")
    op.drop_table("crm_deals")

    op.drop_index("ix_crm_pipeline_stages_pipeline", "crm_pipeline_stages")
    op.drop_table("crm_pipeline_stages")

    op.drop_index("ix_crm_pipelines_tenant", "crm_pipelines")
    op.drop_table("crm_pipelines")
