"""Leadgen module - campaigns, runs, places, impressum, llm_insights.

Revision ID: 067
Revises: 066
Create Date: 2026-04-22
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "067"
down_revision = "066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create leadgen tables."""
    # --- leadgen_campaigns ---
    op.create_table(
        "leadgen_campaigns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(50), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "queries", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "language", sa.String(10), nullable=False, server_default="de"
        ),
        sa.Column("region", sa.String(10), nullable=False, server_default="DE"),
        sa.Column(
            "pv_relevance_threshold",
            sa.Integer(),
            nullable=False,
            server_default="5",
        ),
        sa.Column("target_engagement_pipeline_id", sa.Integer(), nullable=True),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="draft"
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["target_engagement_pipeline_id"],
            ["engagement_pipelines.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_leadgen_campaign_slug"),
    )
    op.create_index(
        "ix_leadgen_campaigns_tenant", "leadgen_campaigns", ["tenant_id"]
    )

    # --- leadgen_runs ---
    op.create_table(
        "leadgen_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(50), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column(
            "current_stage",
            sa.String(20),
            nullable=False,
            server_default="places",
        ),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="queued"
        ),
        sa.Column(
            "processed_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "success_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "error_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("cost_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "stage_state",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["leadgen_campaigns.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_leadgen_runs_tenant_status",
        "leadgen_runs",
        ["tenant_id", "status"],
    )
    op.create_index("ix_leadgen_runs_campaign", "leadgen_runs", ["campaign_id"])

    # --- leadgen_places ---
    op.create_table(
        "leadgen_places",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(50), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=True),
        sa.Column("google_place_id", sa.String(255), nullable=False),
        sa.Column("source_query", sa.String(500), nullable=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("address_street", sa.String(300), nullable=True),
        sa.Column("address_zip", sa.String(20), nullable=True),
        sa.Column("address_city", sa.String(200), nullable=True),
        sa.Column("address_country", sa.String(10), nullable=True),
        sa.Column("formatted_address", sa.String(500), nullable=True),
        sa.Column("lat", sa.Numeric(10, 7), nullable=True),
        sa.Column("lng", sa.Numeric(10, 7), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column(
            "google_categories",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("rating", sa.Numeric(3, 2), nullable=True),
        sa.Column("user_ratings_total", sa.Integer(), nullable=True),
        sa.Column("business_status", sa.String(50), nullable=True),
        sa.Column(
            "raw_payload",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "status", sa.String(30), nullable=False, server_default="discovered"
        ),
        sa.Column("rejected_reason", sa.String(200), nullable=True),
        sa.Column("contact_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["leadgen_campaigns.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["leadgen_runs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"], ["contacts.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "google_place_id", name="uq_leadgen_place_google_id"
        ),
    )
    op.create_index(
        "ix_leadgen_places_campaign_status",
        "leadgen_places",
        ["campaign_id", "status"],
    )
    op.create_index("ix_leadgen_places_tenant", "leadgen_places", ["tenant_id"])

    # --- leadgen_impressum ---
    op.create_table(
        "leadgen_impressum",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(50), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column(
            "managing_directors",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("postal_address", sa.Text(), nullable=True),
        sa.Column("handelsregister", sa.String(100), nullable=True),
        sa.Column("ust_id", sa.String(50), nullable=True),
        sa.Column("extraction_error", sa.Text(), nullable=True),
        sa.Column("extracted_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["place_id"], ["leadgen_places.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("place_id", name="uq_leadgen_impressum_place"),
    )

    # --- leadgen_llm_insights ---
    op.create_table(
        "leadgen_llm_insights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(50), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("pv_relevance_score", sa.Integer(), nullable=True),
        sa.Column(
            "services", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "brands", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "customer_segments",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("company_size_indicator", sa.String(200), nullable=True),
        sa.Column("personalization_hook", sa.Text(), nullable=True),
        sa.Column(
            "red_flags",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "pages_analyzed",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("extraction_error", sa.Text(), nullable=True),
        sa.Column("extracted_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["place_id"], ["leadgen_places.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("place_id", name="uq_leadgen_llm_insights_place"),
    )


def downgrade() -> None:
    """Drop leadgen tables."""
    op.drop_table("leadgen_llm_insights")
    op.drop_table("leadgen_impressum")
    op.drop_index("ix_leadgen_places_tenant", table_name="leadgen_places")
    op.drop_index(
        "ix_leadgen_places_campaign_status", table_name="leadgen_places"
    )
    op.drop_table("leadgen_places")
    op.drop_index("ix_leadgen_runs_campaign", table_name="leadgen_runs")
    op.drop_index("ix_leadgen_runs_tenant_status", table_name="leadgen_runs")
    op.drop_table("leadgen_runs")
    op.drop_index(
        "ix_leadgen_campaigns_tenant", table_name="leadgen_campaigns"
    )
    op.drop_table("leadgen_campaigns")
