"""Meta Conversions API Integration

Revision ID: 044
Revises: 043
Create Date: 2024-01-15

Adds tables for Meta (Facebook) Conversions API integration:
- meta_integrations: Connection to Meta Business Account per tenant
- conversion_events: Log of all events sent to Meta
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Meta Integration per Tenant
    op.create_table(
        "meta_integrations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        # Meta Account Details
        sa.Column("pixel_id", sa.String(50), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),  # Encrypted
        # Optional: Ad Account for Custom Audiences (Phase 9b)
        sa.Column("ad_account_id", sa.String(50), nullable=True),
        # Configuration
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("test_mode", sa.Boolean(), default=False, nullable=False),
        # Statistics
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_events_sent", sa.Integer(), default=0, nullable=False),
        sa.Column("total_events_failed", sa.Integer(), default=0, nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_meta_integrations_tenant",
        "meta_integrations",
        ["tenant_id"],
        unique=True,  # One integration per tenant
    )

    # Conversion Event Log
    op.create_table(
        "conversion_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column(
            "meta_integration_id",
            sa.Integer(),
            sa.ForeignKey("meta_integrations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Event Details
        sa.Column("event_name", sa.String(50), nullable=False),  # PageView, Lead, etc.
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_id", sa.String(100), nullable=False),  # For deduplication
        # Contact Reference
        sa.Column(
            "contact_id",
            sa.Integer(),
            sa.ForeignKey("contacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Optional Pipeline/Enrollment Reference
        sa.Column(
            "pipeline_id",
            sa.Integer(),
            sa.ForeignKey("engagement_pipelines.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "enrollment_id",
            sa.Integer(),
            sa.ForeignKey("pipeline_enrollments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Payload (for debugging, PII already hashed)
        sa.Column("user_data_fields", JSONB, nullable=True),  # Which fields were sent
        sa.Column("custom_data", JSONB, nullable=True),  # Event-specific data
        # Response
        sa.Column(
            "status", sa.String(20), default="pending", nullable=False
        ),  # pending, sent, failed, test
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("response_body", JSONB, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Lifecycle
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversion_events_tenant_time",
        "conversion_events",
        ["tenant_id", "event_time"],
    )
    op.create_index(
        "ix_conversion_events_contact",
        "conversion_events",
        ["contact_id"],
    )
    op.create_index(
        "ix_conversion_events_event_id",
        "conversion_events",
        ["event_id"],
        unique=True,
    )
    op.create_index(
        "ix_conversion_events_status",
        "conversion_events",
        ["status"],
    )


def downgrade() -> None:
    op.drop_table("conversion_events")
    op.drop_table("meta_integrations")
