"""Add Optimization Engine tables.

Revision ID: 046_optimization_engine
Revises: 045_custom_audiences
Create Date: 2024-03-07

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create optimization_reports table
    op.create_table(
        "optimization_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("pipeline_id", sa.Integer(), nullable=False),
        # Report Type
        sa.Column(
            "report_type",
            sa.String(length=20),
            nullable=False,
            comment="weekly, monthly, ad_hoc",
        ),
        # Analysis Period
        sa.Column("analysis_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("analysis_period_end", sa.DateTime(timezone=True), nullable=False),
        # Metrics
        sa.Column("total_enrollments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_enrollments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successful_enrollments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conversion_rate", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("avg_touches_to_conversion", sa.Numeric(5, 2), nullable=True),
        sa.Column("avg_days_to_conversion", sa.Numeric(7, 2), nullable=True),
        # Channel Performance
        sa.Column(
            "channel_stats",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
            comment="Stats per channel",
        ),
        # Stage Progression
        sa.Column(
            "stage_progression",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
            comment="How contacts move through stages",
        ),
        # Patterns Found
        sa.Column(
            "patterns_found",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
            comment="List of identified patterns",
        ),
        # Recommendations
        sa.Column(
            "recommendations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
            comment="List of actionable recommendations",
        ),
        # Suggested Changes
        sa.Column("suggested_playbook_changes", sa.Text(), nullable=True),
        # Status
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
            comment="pending, analyzing, completed, failed",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Application
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_by", sa.Integer(), nullable=True),
        # Lifecycle
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["pipeline_id"],
            ["engagement_pipelines.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["applied_by"],
            ["users.id"],
            ondelete="SET NULL",
        ),
    )

    # Create indexes for optimization_reports
    op.create_index(
        "ix_optimization_reports_tenant",
        "optimization_reports",
        ["tenant_id"],
    )
    op.create_index(
        "ix_optimization_reports_pipeline",
        "optimization_reports",
        ["pipeline_id"],
    )
    op.create_index(
        "ix_optimization_reports_created",
        "optimization_reports",
        ["created_at"],
    )

    # Create optimization_insights table
    op.create_table(
        "optimization_insights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        # Insight Details
        sa.Column(
            "insight_type",
            sa.String(length=30),
            nullable=False,
            comment="pattern, recommendation, warning, opportunity",
        ),
        sa.Column(
            "category",
            sa.String(length=30),
            nullable=False,
            comment="channel, timing, content, targeting, sequence",
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        # Priority & Confidence
        sa.Column(
            "priority",
            sa.String(length=10),
            nullable=False,
            server_default="medium",
            comment="high, medium, low",
        ),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=False, server_default="0.8"),
        # Impact Estimate
        sa.Column("estimated_impact", sa.String(length=100), nullable=True),
        # Supporting Data
        sa.Column(
            "supporting_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        # Action
        sa.Column("suggested_action", sa.Text(), nullable=True),
        sa.Column("is_actionable", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_applied", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        # Lifecycle
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["optimization_reports.id"],
            ondelete="CASCADE",
        ),
    )

    # Create indexes for optimization_insights
    op.create_index(
        "ix_optimization_insights_tenant",
        "optimization_insights",
        ["tenant_id"],
    )
    op.create_index(
        "ix_optimization_insights_report",
        "optimization_insights",
        ["report_id"],
    )
    op.create_index(
        "ix_optimization_insights_type",
        "optimization_insights",
        ["insight_type"],
    )
    op.create_index(
        "ix_optimization_insights_priority",
        "optimization_insights",
        ["priority"],
    )


def downgrade() -> None:
    op.drop_table("optimization_insights")
    op.drop_table("optimization_reports")
