"""LinkedIn automation: templates, connections, messages, campaigns.

Revision ID: 033
Revises: 032
Create Date: 2026-03-04
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to linkedin_accounts for limits and warmup
    op.add_column(
        "linkedin_accounts",
        sa.Column("daily_connection_limit", sa.Integer(), nullable=False, server_default="25"),
    )
    op.add_column(
        "linkedin_accounts",
        sa.Column("daily_message_limit", sa.Integer(), nullable=False, server_default="50"),
    )
    op.add_column(
        "linkedin_accounts",
        sa.Column("connections_sent_today", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "linkedin_accounts",
        sa.Column("messages_sent_today", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "linkedin_accounts",
        sa.Column("warmup_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "linkedin_accounts",
        sa.Column("warmup_day", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "linkedin_accounts",
        sa.Column("warmup_started_at", sa.DateTime(), nullable=True),
    )

    # Create linkedin_message_templates table
    op.create_table(
        "linkedin_message_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(50), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default="general"),
        sa.Column("subject", sa.String(200), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("variables", JSONB, nullable=True),
        sa.Column("variant_of_id", sa.Integer(), sa.ForeignKey("linkedin_message_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("variant_name", sa.String(50), nullable=True),
        sa.Column("times_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("responses_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_linkedin_templates_tenant", "linkedin_message_templates", ["tenant_id"])
    op.create_index("ix_linkedin_templates_category", "linkedin_message_templates", ["tenant_id", "category"])

    # Create linkedin_campaigns table
    op.create_table(
        "linkedin_campaigns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(50), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("linkedin_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="Europe/Berlin"),
        sa.Column("daily_connection_limit", sa.Integer(), nullable=True),
        sa.Column("daily_message_limit", sa.Integer(), nullable=True),
        sa.Column("schedule_days", JSONB, nullable=True),
        sa.Column("schedule_start_time", sa.String(5), nullable=True),
        sa.Column("schedule_end_time", sa.String(5), nullable=True),
        sa.Column("stop_on_reply", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("stop_on_connect", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("total_leads", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leads_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leads_active", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("connections_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("connections_accepted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("messages_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("replies_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_linkedin_campaigns_tenant", "linkedin_campaigns", ["tenant_id"])
    op.create_index("ix_linkedin_campaigns_status", "linkedin_campaigns", ["tenant_id", "status"])
    op.create_index("ix_linkedin_campaigns_account", "linkedin_campaigns", ["account_id"])

    # Create linkedin_campaign_steps table
    op.create_table(
        "linkedin_campaign_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(50), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("linkedin_campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("step_type", sa.String(30), nullable=False),
        sa.Column("wait_days", sa.Integer(), nullable=True),
        sa.Column("wait_hours", sa.Integer(), nullable=True),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("linkedin_message_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("template_ids", JSONB, nullable=True),
        sa.Column("ab_test_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("condition_type", sa.String(50), nullable=True),
        sa.Column("condition_true_step_id", sa.Integer(), nullable=True),
        sa.Column("condition_false_step_id", sa.Integer(), nullable=True),
        sa.Column("leads_entered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leads_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leads_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_linkedin_campaign_steps_campaign", "linkedin_campaign_steps", ["campaign_id"])
    op.create_index("ix_linkedin_campaign_steps_order", "linkedin_campaign_steps", ["campaign_id", "order"])

    # Create linkedin_campaign_leads table
    op.create_table(
        "linkedin_campaign_leads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(50), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("linkedin_campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", sa.Integer(), sa.ForeignKey("linkedin_contacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=False),
        sa.Column("linkedin_id", sa.String(100), nullable=True),
        sa.Column("profile_name", sa.String(200), nullable=False),
        sa.Column("profile_headline", sa.Text(), nullable=True),
        sa.Column("company_name", sa.String(200), nullable=True),
        sa.Column("profile_picture_url", sa.String(500), nullable=True),
        sa.Column("custom_variables", JSONB, nullable=True),
        sa.Column("current_step_id", sa.Integer(), sa.ForeignKey("linkedin_campaign_steps.id", ondelete="SET NULL"), nullable=True),
        sa.Column("current_step_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("connection_status", sa.String(30), nullable=True),
        sa.Column("has_replied", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("reply_received_at", sa.DateTime(), nullable=True),
        sa.Column("entered_campaign_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("next_action_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ab_variant", sa.String(10), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_linkedin_campaign_leads_campaign", "linkedin_campaign_leads", ["campaign_id"])
    op.create_index("ix_linkedin_campaign_leads_status", "linkedin_campaign_leads", ["campaign_id", "status"])
    op.create_index("ix_linkedin_campaign_leads_next_action", "linkedin_campaign_leads", ["next_action_at"])
    op.create_index("ix_linkedin_campaign_leads_linkedin_url", "linkedin_campaign_leads", ["tenant_id", "linkedin_url"])

    # Create linkedin_connections table
    op.create_table(
        "linkedin_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(50), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("linkedin_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", sa.Integer(), sa.ForeignKey("linkedin_contacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=False),
        sa.Column("linkedin_id", sa.String(100), nullable=True),
        sa.Column("profile_name", sa.String(200), nullable=False),
        sa.Column("profile_headline", sa.Text(), nullable=True),
        sa.Column("profile_picture_url", sa.String(500), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("linkedin_message_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("linkedin_campaigns.id", ondelete="SET NULL"), nullable=True),
        sa.Column("campaign_lead_id", sa.Integer(), sa.ForeignKey("linkedin_campaign_leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_linkedin_connections_tenant", "linkedin_connections", ["tenant_id"])
    op.create_index("ix_linkedin_connections_account", "linkedin_connections", ["account_id"])
    op.create_index("ix_linkedin_connections_status", "linkedin_connections", ["tenant_id", "status"])
    op.create_index("ix_linkedin_connections_linkedin_url", "linkedin_connections", ["tenant_id", "linkedin_url"])
    op.create_index("ix_linkedin_connections_campaign", "linkedin_connections", ["campaign_id"])

    # Create linkedin_messages table
    op.create_table(
        "linkedin_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(50), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("linkedin_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", sa.Integer(), sa.ForeignKey("linkedin_contacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("connection_id", sa.Integer(), sa.ForeignKey("linkedin_connections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("conversation_id", sa.String(100), nullable=True),
        sa.Column("thread_id", sa.String(100), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=False),
        sa.Column("profile_name", sa.String(200), nullable=False),
        sa.Column("message_type", sa.String(30), nullable=False, server_default="direct"),
        sa.Column("subject", sa.String(200), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("linkedin_message_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("direction", sa.String(10), nullable=False, server_default="outbound"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("replied_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("linkedin_campaigns.id", ondelete="SET NULL"), nullable=True),
        sa.Column("campaign_lead_id", sa.Integer(), sa.ForeignKey("linkedin_campaign_leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("campaign_step_id", sa.Integer(), sa.ForeignKey("linkedin_campaign_steps.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_linkedin_messages_tenant", "linkedin_messages", ["tenant_id"])
    op.create_index("ix_linkedin_messages_account", "linkedin_messages", ["account_id"])
    op.create_index("ix_linkedin_messages_status", "linkedin_messages", ["tenant_id", "status"])
    op.create_index("ix_linkedin_messages_conversation", "linkedin_messages", ["conversation_id"])
    op.create_index("ix_linkedin_messages_campaign", "linkedin_messages", ["campaign_id"])
    op.create_index("ix_linkedin_messages_direction", "linkedin_messages", ["tenant_id", "direction"])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("linkedin_messages")
    op.drop_table("linkedin_connections")
    op.drop_table("linkedin_campaign_leads")
    op.drop_table("linkedin_campaign_steps")
    op.drop_table("linkedin_campaigns")
    op.drop_table("linkedin_message_templates")

    # Remove columns from linkedin_accounts
    op.drop_column("linkedin_accounts", "warmup_started_at")
    op.drop_column("linkedin_accounts", "warmup_day")
    op.drop_column("linkedin_accounts", "warmup_enabled")
    op.drop_column("linkedin_accounts", "messages_sent_today")
    op.drop_column("linkedin_accounts", "connections_sent_today")
    op.drop_column("linkedin_accounts", "daily_message_limit")
    op.drop_column("linkedin_accounts", "daily_connection_limit")
