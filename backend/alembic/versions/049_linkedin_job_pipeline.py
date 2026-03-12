"""Add pipeline_id to linkedin_scraper_jobs for pipeline context.

Revision ID: 049
Revises: 048
Create Date: 2026-03-08

"""

from alembic import op
import sqlalchemy as sa

revision = "049"
down_revision = "048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "linkedin_scraper_jobs",
        sa.Column(
            "pipeline_id",
            sa.Integer(),
            sa.ForeignKey("engagement_pipelines.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    # Auto-enroll scraped contacts into the pipeline
    op.add_column(
        "linkedin_scraper_jobs",
        sa.Column(
            "auto_enroll_pipeline",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    op.create_index(
        "ix_linkedin_jobs_pipeline",
        "linkedin_scraper_jobs",
        ["pipeline_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_linkedin_jobs_pipeline", "linkedin_scraper_jobs")
    op.drop_column("linkedin_scraper_jobs", "auto_enroll_pipeline")
    op.drop_column("linkedin_scraper_jobs", "pipeline_id")
