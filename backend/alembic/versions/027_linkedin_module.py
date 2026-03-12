"""LinkedIn module - Sales Navigator scraping.

Revision ID: 027
Revises: 026
Create Date: 2026-02-26
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create linkedin_accounts table
    op.create_table(
        "linkedin_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        # Account info
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_encrypted", sa.Text(), nullable=True),
        # Session management
        sa.Column("session_data", JSONB, nullable=True),
        sa.Column("session_expires_at", sa.DateTime(), nullable=True),
        # Status
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="'inactive'",
        ),
        sa.Column(
            "is_sales_navigator",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        # Rate limiting
        sa.Column(
            "daily_profile_limit",
            sa.Integer(),
            nullable=False,
            server_default="100",
        ),
        sa.Column(
            "profiles_scraped_today",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "total_profiles_scraped",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("last_scrape_date", sa.DateTime(), nullable=True),
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
    op.create_index("ix_linkedin_accounts_tenant", "linkedin_accounts", ["tenant_id"])
    op.create_index(
        "ix_linkedin_accounts_tenant_status",
        "linkedin_accounts",
        ["tenant_id", "status"],
    )

    # Create linkedin_scraper_jobs table
    op.create_table(
        "linkedin_scraper_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.Integer(),
            sa.ForeignKey("linkedin_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "funnel_id",
            sa.Integer(),
            sa.ForeignKey("funnel_funnels.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Job configuration
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "job_type",
            sa.String(30),
            nullable=False,
            server_default="'search'",
        ),
        sa.Column("search_url", sa.Text(), nullable=True),
        sa.Column("profile_urls", JSONB, nullable=True),
        # Limits
        sa.Column(
            "max_profiles",
            sa.Integer(),
            nullable=False,
            server_default="100",
        ),
        sa.Column(
            "daily_limit",
            sa.Integer(),
            nullable=False,
            server_default="50",
        ),
        sa.Column(
            "min_delay_seconds",
            sa.Integer(),
            nullable=False,
            server_default="30",
        ),
        sa.Column(
            "max_delay_seconds",
            sa.Integer(),
            nullable=False,
            server_default="120",
        ),
        # Status
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="'draft'",
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        # Progress
        sa.Column(
            "profiles_found",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "profiles_scraped",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "profiles_failed",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "current_page",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column("last_profile_url", sa.Text(), nullable=True),
        # Error handling
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        # Auto-import settings
        sa.Column(
            "auto_import",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "import_stage_id",
            sa.Integer(),
            sa.ForeignKey("funnel_stages.id", ondelete="SET NULL"),
            nullable=True,
        ),
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
        "ix_linkedin_jobs_tenant", "linkedin_scraper_jobs", ["tenant_id"]
    )
    op.create_index(
        "ix_linkedin_jobs_tenant_status",
        "linkedin_scraper_jobs",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_linkedin_jobs_account", "linkedin_scraper_jobs", ["account_id"]
    )

    # Create linkedin_contacts table
    op.create_table(
        "linkedin_contacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "scraper_job_id",
            sa.Integer(),
            sa.ForeignKey("linkedin_scraper_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # LinkedIn identifiers
        sa.Column("linkedin_url", sa.String(500), nullable=False),
        sa.Column("linkedin_id", sa.String(100), nullable=True),
        sa.Column("sales_navigator_url", sa.String(500), nullable=True),
        # Basic info
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("headline", sa.Text(), nullable=True),
        sa.Column("position", sa.String(200), nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("profile_picture_url", sa.String(500), nullable=True),
        # Company info
        sa.Column("company_name", sa.String(200), nullable=True),
        sa.Column("company_linkedin_url", sa.String(500), nullable=True),
        sa.Column("company_size", sa.String(50), nullable=True),
        sa.Column("company_industry", sa.String(100), nullable=True),
        # Contact info
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("twitter_url", sa.String(300), nullable=True),
        # Experience & Education
        sa.Column("experience", JSONB, nullable=True),
        sa.Column("education", JSONB, nullable=True),
        sa.Column("skills", JSONB, nullable=True),
        # Status
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="'scraped'",
        ),
        # Funnel integration
        sa.Column(
            "funnel_prospect_id",
            sa.Integer(),
            sa.ForeignKey("funnel_prospects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "funnel_company_id",
            sa.Integer(),
            sa.ForeignKey("funnel_companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("imported_at", sa.DateTime(), nullable=True),
        # Raw data
        sa.Column("raw_data", JSONB, nullable=True),
        sa.Column("scrape_error", sa.Text(), nullable=True),
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
    op.create_index("ix_linkedin_contacts_tenant", "linkedin_contacts", ["tenant_id"])
    op.create_index("ix_linkedin_contacts_job", "linkedin_contacts", ["scraper_job_id"])
    op.create_index(
        "ix_linkedin_contacts_status", "linkedin_contacts", ["tenant_id", "status"]
    )
    op.create_index(
        "ix_linkedin_contacts_linkedin_url",
        "linkedin_contacts",
        ["tenant_id", "linkedin_url"],
    )


def downgrade() -> None:
    # Drop linkedin_contacts
    op.drop_index("ix_linkedin_contacts_linkedin_url", "linkedin_contacts")
    op.drop_index("ix_linkedin_contacts_status", "linkedin_contacts")
    op.drop_index("ix_linkedin_contacts_job", "linkedin_contacts")
    op.drop_index("ix_linkedin_contacts_tenant", "linkedin_contacts")
    op.drop_table("linkedin_contacts")

    # Drop linkedin_scraper_jobs
    op.drop_index("ix_linkedin_jobs_account", "linkedin_scraper_jobs")
    op.drop_index("ix_linkedin_jobs_tenant_status", "linkedin_scraper_jobs")
    op.drop_index("ix_linkedin_jobs_tenant", "linkedin_scraper_jobs")
    op.drop_table("linkedin_scraper_jobs")

    # Drop linkedin_accounts
    op.drop_index("ix_linkedin_accounts_tenant_status", "linkedin_accounts")
    op.drop_index("ix_linkedin_accounts_tenant", "linkedin_accounts")
    op.drop_table("linkedin_accounts")
