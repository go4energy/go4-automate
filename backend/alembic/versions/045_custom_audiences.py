"""Add Custom Audiences tables for Meta integration.

Revision ID: 045_custom_audiences
Revises: 044_meta_integrations
Create Date: 2024-03-07

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create custom_audiences table
    op.create_table(
        "custom_audiences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("meta_integration_id", sa.Integer(), nullable=False),
        # Audience Info
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # Meta Audience Reference
        sa.Column("meta_audience_id", sa.String(length=50), nullable=True),
        sa.Column("meta_audience_name", sa.String(length=200), nullable=True),
        # Segment Definition
        sa.Column("pipeline_id", sa.Integer(), nullable=True),
        sa.Column(
            "segment_filter",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
            comment="Filter: {stages: [], tags: [], source_modules: []}",
        ),
        # Sync Configuration
        sa.Column(
            "sync_mode",
            sa.String(length=20),
            nullable=False,
            server_default="manual",
            comment="manual, daily, realtime",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        # Statistics
        sa.Column("audience_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "last_sync_status",
            sa.String(length=20),
            nullable=True,
            comment="success, partial, failed",
        ),
        # Lifecycle
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["meta_integration_id"],
            ["meta_integrations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_id"],
            ["engagement_pipelines.id"],
            ondelete="SET NULL",
        ),
    )

    # Create indexes for custom_audiences
    op.create_index(
        "ix_custom_audiences_tenant",
        "custom_audiences",
        ["tenant_id"],
    )
    op.create_index(
        "ix_custom_audiences_integration",
        "custom_audiences",
        ["meta_integration_id"],
    )
    op.create_index(
        "ix_custom_audiences_pipeline",
        "custom_audiences",
        ["pipeline_id"],
    )

    # Create audience_sync_logs table
    op.create_table(
        "audience_sync_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("audience_id", sa.Integer(), nullable=False),
        # Operation Details
        sa.Column(
            "operation",
            sa.String(length=20),
            nullable=False,
            comment="add, remove, replace",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        # Statistics
        sa.Column("contacts_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contacts_added", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contacts_removed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contacts_failed", sa.Integer(), nullable=False, server_default="0"),
        # Result
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
            comment="pending, success, partial, failed",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("meta_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["audience_id"],
            ["custom_audiences.id"],
            ondelete="CASCADE",
        ),
    )

    # Create indexes for audience_sync_logs
    op.create_index(
        "ix_audience_sync_logs_tenant",
        "audience_sync_logs",
        ["tenant_id"],
    )
    op.create_index(
        "ix_audience_sync_logs_audience",
        "audience_sync_logs",
        ["audience_id"],
    )
    op.create_index(
        "ix_audience_sync_logs_started",
        "audience_sync_logs",
        ["started_at"],
    )


def downgrade() -> None:
    op.drop_table("audience_sync_logs")
    op.drop_table("custom_audiences")
