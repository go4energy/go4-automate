"""LinkedIn job logs and schedule settings.

Revision ID: 028
Revises: 027
Create Date: 2026-03-03
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "028"
down_revision = "9174f7719d75"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add schedule fields to linkedin_scraper_jobs
    op.add_column(
        "linkedin_scraper_jobs",
        sa.Column(
            "schedule_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "linkedin_scraper_jobs",
        sa.Column("schedule_days", JSONB, nullable=True),
    )
    op.add_column(
        "linkedin_scraper_jobs",
        sa.Column("schedule_start_time", sa.String(5), nullable=True),
    )
    op.add_column(
        "linkedin_scraper_jobs",
        sa.Column("schedule_end_time", sa.String(5), nullable=True),
    )
    op.add_column(
        "linkedin_scraper_jobs",
        sa.Column(
            "max_pages_per_run",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),
    )

    # Create linkedin_job_logs table
    op.create_table(
        "linkedin_job_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("linkedin_scraper_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Execution timing
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        # Progress tracking
        sa.Column("start_page", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("end_page", sa.Integer(), nullable=True),
        sa.Column("profiles_scraped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("profiles_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("profiles_skipped", sa.Integer(), nullable=False, server_default="0"),
        # Status
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="'running'",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
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

    # Create indexes
    op.create_index(
        "ix_linkedin_job_logs_job",
        "linkedin_job_logs",
        ["job_id"],
    )
    op.create_index(
        "ix_linkedin_job_logs_job_created",
        "linkedin_job_logs",
        ["job_id", "created_at"],
    )
    op.create_index(
        "ix_linkedin_job_logs_tenant",
        "linkedin_job_logs",
        ["tenant_id"],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_linkedin_job_logs_tenant", table_name="linkedin_job_logs")
    op.drop_index("ix_linkedin_job_logs_job_created", table_name="linkedin_job_logs")
    op.drop_index("ix_linkedin_job_logs_job", table_name="linkedin_job_logs")

    # Drop table
    op.drop_table("linkedin_job_logs")

    # Remove schedule columns from linkedin_scraper_jobs
    op.drop_column("linkedin_scraper_jobs", "max_pages_per_run")
    op.drop_column("linkedin_scraper_jobs", "schedule_end_time")
    op.drop_column("linkedin_scraper_jobs", "schedule_start_time")
    op.drop_column("linkedin_scraper_jobs", "schedule_days")
    op.drop_column("linkedin_scraper_jobs", "schedule_enabled")
