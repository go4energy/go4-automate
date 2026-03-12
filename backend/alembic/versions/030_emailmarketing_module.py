"""Email Marketing module - campaigns, sequences, tracking.

Revision ID: 030
Revises: 028
Create Date: 2025-01-20

"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers
revision = "030"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Email Providers
    op.create_table(
        "email_providers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        # Provider type
        sa.Column("provider_type", sa.String(30), nullable=False),
        # Credentials
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        # Sender settings
        sa.Column("sender_email", sa.String(320), nullable=False),
        sa.Column("sender_name", sa.String(200), nullable=False),
        sa.Column("reply_to_email", sa.String(320), nullable=True),
        # Domain settings
        sa.Column("tracking_domain", sa.String(200), nullable=True),
        # Rate limits
        sa.Column("hourly_limit", sa.Integer(), nullable=False, server_default="500"),
        sa.Column("daily_limit", sa.Integer(), nullable=False, server_default="10000"),
        # Status
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(), nullable=True),
        # Usage tracking
        sa.Column(
            "emails_sent_today", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("emails_sent_hour", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_reset_at", sa.DateTime(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_email_providers_tenant_status", "email_providers", ["tenant_id", "status"]
    )

    # 2. Email Templates
    op.create_table(
        "email_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        # Basics
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # Content
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=True),
        # Merge tags
        sa.Column("variables", JSONB, nullable=False, server_default="[]"),
        # Status
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        # Categories
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_unique_constraint(
        "uq_email_templates_tenant_slug", "email_templates", ["tenant_id", "slug"]
    )
    op.create_index("ix_email_templates_tenant", "email_templates", ["tenant_id"])

    # 3. Email Campaigns
    op.create_table(
        "email_campaigns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "provider_id",
            sa.Integer(),
            sa.ForeignKey("email_providers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("email_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Basics
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        # Content
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=True),
        # Recipient selection
        sa.Column("segment_filters", JSONB, nullable=True),
        sa.Column("contact_ids", JSONB, nullable=True),
        # Scheduling
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        # Stats
        sa.Column(
            "total_recipients", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delivered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("opened_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clicked_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bounced_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "unsubscribed_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("spam_count", sa.Integer(), nullable=False, server_default="0"),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_email_campaigns_tenant_status", "email_campaigns", ["tenant_id", "status"]
    )

    # 4. Email Recipients
    op.create_table(
        "email_recipients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "campaign_id",
            sa.Integer(),
            sa.ForeignKey("email_campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "contact_id",
            sa.Integer(),
            sa.ForeignKey("contacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Recipient info
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(200), nullable=True),
        # Personalization
        sa.Column("merge_data", JSONB, nullable=False, server_default="{}"),
        # Tracking
        sa.Column("tracking_token", sa.String(36), nullable=False, unique=True),
        # Status
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        # Timestamps
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("opened_at", sa.DateTime(), nullable=True),
        sa.Column("clicked_at", sa.DateTime(), nullable=True),
        sa.Column("bounced_at", sa.DateTime(), nullable=True),
        # Provider reference
        sa.Column("provider_message_id", sa.String(200), nullable=True),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_email_recipients_campaign_status",
        "email_recipients",
        ["campaign_id", "status"],
    )
    op.create_index(
        "ix_email_recipients_token", "email_recipients", ["tracking_token"]
    )

    # 5. Email Clicks
    op.create_table(
        "email_clicks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "recipient_id",
            sa.Integer(),
            sa.ForeignKey("email_recipients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Click info
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column("clicked_at", sa.DateTime(), nullable=False),
        # Meta
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_email_clicks_recipient", "email_clicks", ["recipient_id"])

    # 6. Email Sequences
    op.create_table(
        "email_sequences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "provider_id",
            sa.Integer(),
            sa.ForeignKey("email_providers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Basics
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # Trigger
        sa.Column(
            "trigger_type", sa.String(30), nullable=False, server_default="manual"
        ),
        sa.Column("trigger_filters", JSONB, nullable=True),
        # Status
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        # Send window
        sa.Column("send_window_start", sa.String(5), nullable=True),
        sa.Column("send_window_end", sa.String(5), nullable=True),
        sa.Column(
            "skip_weekends", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column(
            "timezone", sa.String(50), nullable=False, server_default="'Europe/Berlin'"
        ),
        # Stats
        sa.Column("total_enrolled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "total_unsubscribed", sa.Integer(), nullable=False, server_default="0"
        ),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_email_sequences_tenant_status", "email_sequences", ["tenant_id", "status"]
    )

    # 7. Email Sequence Steps
    op.create_table(
        "email_sequence_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "sequence_id",
            sa.Integer(),
            sa.ForeignKey("email_sequences.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("email_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Position
        sa.Column("position", sa.Integer(), nullable=False),
        # Delay
        sa.Column("delay_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("delay_hours", sa.Integer(), nullable=False, server_default="0"),
        # Content
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=True),
        # Conditional sending
        sa.Column("send_if_opened_previous", sa.Boolean(), nullable=True),
        sa.Column("send_if_clicked_previous", sa.Boolean(), nullable=True),
        # Stats
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("opened_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clicked_count", sa.Integer(), nullable=False, server_default="0"),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_email_sequence_steps_sequence_position",
        "email_sequence_steps",
        ["sequence_id", "position"],
    )

    # 8. Email Sequence Enrollments
    op.create_table(
        "email_sequence_enrollments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "sequence_id",
            sa.Integer(),
            sa.ForeignKey("email_sequences.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "contact_id",
            sa.Integer(),
            sa.ForeignKey("contacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Progress
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        # Scheduling
        sa.Column("next_send_at", sa.DateTime(), nullable=True),
        sa.Column("last_sent_at", sa.DateTime(), nullable=True),
        # Tracking
        sa.Column("enrolled_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("unsubscribed_at", sa.DateTime(), nullable=True),
        # Source
        sa.Column("source", sa.String(50), nullable=False, server_default="'manual'"),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_unique_constraint(
        "uq_email_enrollments_sequence_contact",
        "email_sequence_enrollments",
        ["sequence_id", "contact_id"],
    )
    op.create_index(
        "ix_email_enrollments_status_next",
        "email_sequence_enrollments",
        ["status", "next_send_at"],
    )

    # 9. Email Unsubscribes
    op.create_table(
        "email_unsubscribes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        # Unsubscribed email
        sa.Column("email", sa.String(320), nullable=False),
        # Reason
        sa.Column(
            "reason", sa.String(30), nullable=False, server_default="'user_request'"
        ),
        # Source
        sa.Column("source_type", sa.String(30), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        # Meta
        sa.Column("ip_address", sa.String(45), nullable=True),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_unique_constraint(
        "uq_email_unsubscribes_tenant_email",
        "email_unsubscribes",
        ["tenant_id", "email"],
    )
    op.create_index(
        "ix_email_unsubscribes_tenant_email",
        "email_unsubscribes",
        ["tenant_id", "email"],
    )


def downgrade() -> None:
    op.drop_table("email_unsubscribes")
    op.drop_table("email_sequence_enrollments")
    op.drop_table("email_sequence_steps")
    op.drop_table("email_sequences")
    op.drop_table("email_clicks")
    op.drop_table("email_recipients")
    op.drop_table("email_campaigns")
    op.drop_table("email_templates")
    op.drop_table("email_providers")
