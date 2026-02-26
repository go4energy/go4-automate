"""Funnels module - prospecting before CRM.

Revision ID: 025
Revises: 024
Create Date: 2026-02-26
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create funnel_funnels table
    op.create_table(
        "funnel_funnels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="'active'",
        ),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("target_criteria", JSONB, nullable=True),
        # Handoff configuration
        sa.Column(
            "handoff_pipeline_id",
            sa.Integer(),
            sa.ForeignKey("crm_pipelines.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "handoff_stage_id",
            sa.Integer(),
            sa.ForeignKey("crm_pipeline_stages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("external_crm_config", JSONB, nullable=True),
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
    op.create_index("ix_funnel_funnels_tenant", "funnel_funnels", ["tenant_id"])
    op.create_index(
        "ix_funnel_funnels_tenant_status", "funnel_funnels", ["tenant_id", "status"]
    )

    # Create funnel_stages table
    op.create_table(
        "funnel_stages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "funnel_id",
            sa.Integer(),
            sa.ForeignKey("funnel_funnels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("color", sa.String(20), nullable=False, server_default="'#6B7280'"),
        sa.Column("is_handoff", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "is_disqualified", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("auto_actions", JSONB, nullable=True),
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
        "ix_funnel_stages_funnel_position",
        "funnel_stages",
        ["funnel_id", "position"],
    )

    # Create funnel_companies table
    op.create_table(
        "funnel_companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "funnel_id",
            sa.Integer(),
            sa.ForeignKey("funnel_funnels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Basic Info
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("domain", sa.String(200), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("size", sa.String(50), nullable=True),
        # Address & Contact
        sa.Column("address", JSONB, nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(320), nullable=True),
        # Source & Verification
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("source_id", sa.String(200), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        # Dedup
        sa.Column("dedup_key", sa.String(200), nullable=True),
        # CRM Link (after handoff)
        sa.Column(
            "crm_company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Metadata
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("custom_fields", JSONB, nullable=False, server_default="{}"),
        sa.Column("enrichment_data", JSONB, nullable=True),
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
        "ix_funnel_companies_tenant_funnel",
        "funnel_companies",
        ["tenant_id", "funnel_id"],
    )
    op.create_index(
        "ix_funnel_companies_dedup_key",
        "funnel_companies",
        ["tenant_id", "dedup_key"],
    )

    # Create funnel_prospects table
    op.create_table(
        "funnel_prospects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "funnel_id",
            sa.Integer(),
            sa.ForeignKey("funnel_funnels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("funnel_companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "stage_id",
            sa.Integer(),
            sa.ForeignKey("funnel_stages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Person
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("mobile", sa.String(50), nullable=True),
        sa.Column("position", sa.String(150), nullable=True),
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column("seniority", sa.String(50), nullable=True),
        sa.Column("linkedin_url", sa.String(300), nullable=True),
        sa.Column("twitter_url", sa.String(300), nullable=True),
        # Dedup Keys (normalized)
        sa.Column("dedup_email", sa.String(320), nullable=True),
        sa.Column("dedup_linkedin", sa.String(100), nullable=True),
        sa.Column("dedup_phone", sa.String(20), nullable=True),
        # Verification
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("source_id", sa.String(200), nullable=True),
        sa.Column(
            "email_verified", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("email_verified_at", sa.DateTime(), nullable=True),
        # Score & Status
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score_factors", JSONB, nullable=True),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="'new'",
        ),
        # Duplicate handling
        sa.Column("is_duplicate", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "master_prospect_id",
            sa.Integer(),
            sa.ForeignKey("funnel_prospects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "duplicate_of_crm_contact",
            sa.Integer(),
            sa.ForeignKey("contacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # CRM Links (after handoff)
        sa.Column(
            "crm_contact_id",
            sa.Integer(),
            sa.ForeignKey("contacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "crm_deal_id",
            sa.Integer(),
            sa.ForeignKey("crm_deals.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Metadata
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("custom_fields", JSONB, nullable=False, server_default="{}"),
        sa.Column("enrichment_data", JSONB, nullable=True),
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
        "ix_funnel_prospects_tenant_funnel",
        "funnel_prospects",
        ["tenant_id", "funnel_id"],
    )
    op.create_index(
        "ix_funnel_prospects_funnel_stage",
        "funnel_prospects",
        ["funnel_id", "stage_id"],
    )
    op.create_index(
        "ix_funnel_prospects_dedup_email",
        "funnel_prospects",
        ["tenant_id", "dedup_email"],
    )
    op.create_index(
        "ix_funnel_prospects_dedup_linkedin",
        "funnel_prospects",
        ["tenant_id", "dedup_linkedin"],
    )
    op.create_index(
        "ix_funnel_prospects_status",
        "funnel_prospects",
        ["tenant_id", "status"],
    )

    # Create funnel_activities table
    op.create_table(
        "funnel_activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "prospect_id",
            sa.Integer(),
            sa.ForeignKey("funnel_prospects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Activity details
        sa.Column("activity_type", sa.String(50), nullable=False),
        sa.Column("subject", sa.String(300), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("channel", sa.String(30), nullable=True),
        # External reference
        sa.Column("external_id", sa.String(200), nullable=True),
        sa.Column("external_url", sa.String(500), nullable=True),
        # Status
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="'completed'",
        ),
        sa.Column("activity_date", sa.DateTime(), nullable=False),
        sa.Column("metadata", JSONB, nullable=True),
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
        "ix_funnel_activities_prospect",
        "funnel_activities",
        ["prospect_id", "activity_date"],
    )
    op.create_index(
        "ix_funnel_activities_tenant_type",
        "funnel_activities",
        ["tenant_id", "activity_type"],
    )

    # Create funnel_handoffs table
    op.create_table(
        "funnel_handoffs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "funnel_id",
            sa.Integer(),
            sa.ForeignKey("funnel_funnels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prospect_id",
            sa.Integer(),
            sa.ForeignKey("funnel_prospects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("funnel_companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Status
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="'pending'",
        ),
        # Internal CRM references
        sa.Column(
            "crm_contact_id",
            sa.Integer(),
            sa.ForeignKey("contacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "crm_company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "crm_deal_id",
            sa.Integer(),
            sa.ForeignKey("crm_deals.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # External CRM references
        sa.Column("external_crm_type", sa.String(30), nullable=True),
        sa.Column("external_crm_contact_id", sa.String(100), nullable=True),
        sa.Column("external_crm_deal_id", sa.String(100), nullable=True),
        # Trigger info
        sa.Column(
            "triggered_by",
            sa.String(20),
            nullable=False,
            server_default="'manual'",
        ),
        sa.Column("triggered_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        # Error handling
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        # Snapshot
        sa.Column("prospect_data", JSONB, nullable=True),
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
        "ix_funnel_handoffs_tenant_status",
        "funnel_handoffs",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_funnel_handoffs_prospect",
        "funnel_handoffs",
        ["prospect_id"],
    )


def downgrade() -> None:
    # Drop funnel_handoffs
    op.drop_index("ix_funnel_handoffs_prospect", "funnel_handoffs")
    op.drop_index("ix_funnel_handoffs_tenant_status", "funnel_handoffs")
    op.drop_table("funnel_handoffs")

    # Drop funnel_activities
    op.drop_index("ix_funnel_activities_tenant_type", "funnel_activities")
    op.drop_index("ix_funnel_activities_prospect", "funnel_activities")
    op.drop_table("funnel_activities")

    # Drop funnel_prospects
    op.drop_index("ix_funnel_prospects_status", "funnel_prospects")
    op.drop_index("ix_funnel_prospects_dedup_linkedin", "funnel_prospects")
    op.drop_index("ix_funnel_prospects_dedup_email", "funnel_prospects")
    op.drop_index("ix_funnel_prospects_funnel_stage", "funnel_prospects")
    op.drop_index("ix_funnel_prospects_tenant_funnel", "funnel_prospects")
    op.drop_table("funnel_prospects")

    # Drop funnel_companies
    op.drop_index("ix_funnel_companies_dedup_key", "funnel_companies")
    op.drop_index("ix_funnel_companies_tenant_funnel", "funnel_companies")
    op.drop_table("funnel_companies")

    # Drop funnel_stages
    op.drop_index("ix_funnel_stages_funnel_position", "funnel_stages")
    op.drop_table("funnel_stages")

    # Drop funnel_funnels
    op.drop_index("ix_funnel_funnels_tenant_status", "funnel_funnels")
    op.drop_index("ix_funnel_funnels_tenant", "funnel_funnels")
    op.drop_table("funnel_funnels")
