"""WhatsApp Business module - 6 tables.

Revision ID: 034
Revises: 033
Create Date: 2024-01-15 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. whatsapp_accounts - WhatsApp Business Account credentials
    op.create_table(
        "whatsapp_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("phone_number_id", sa.String(50), nullable=False),
        sa.Column("waba_id", sa.String(50), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=True),
        sa.Column("webhook_verify_token", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("daily_limit", sa.Integer(), server_default="1000", nullable=False),
        sa.Column("messages_sent_today", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_reset_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_whatsapp_accounts_tenant_status",
        "whatsapp_accounts",
        ["tenant_id", "status"],
    )

    # 2. whatsapp_templates - Meta-approved message templates
    op.create_table(
        "whatsapp_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(50), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("components", postgresql.JSONB(), nullable=False),
        sa.Column("variables", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(
            ["account_id"], ["whatsapp_accounts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_whatsapp_templates_account_status",
        "whatsapp_templates",
        ["account_id", "status"],
    )
    op.create_index(
        "ix_whatsapp_templates_tenant",
        "whatsapp_templates",
        ["tenant_id"],
    )

    # 3. whatsapp_conversations - Chat threads with contacts
    op.create_table(
        "whatsapp_conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(50), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("contact_id", sa.Integer(), nullable=True),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("contact_name", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column("window_expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_message_at", sa.DateTime(), nullable=True),
        sa.Column("last_message_preview", sa.String(200), nullable=True),
        sa.Column("unread_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(
            ["account_id"], ["whatsapp_accounts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"], ["contacts.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_whatsapp_conversations_tenant_status",
        "whatsapp_conversations",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_whatsapp_conversations_account_phone",
        "whatsapp_conversations",
        ["account_id", "phone"],
        unique=True,
    )
    op.create_index(
        "ix_whatsapp_conversations_last_message",
        "whatsapp_conversations",
        ["tenant_id", "last_message_at"],
    )

    # 4. whatsapp_messages - Individual messages in conversations
    op.create_table(
        "whatsapp_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(50), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("message_type", sa.String(30), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("template_name", sa.String(200), nullable=True),
        sa.Column("template_variables", postgresql.JSONB(), nullable=True),
        sa.Column("wamid", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("error_code", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["whatsapp_conversations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_whatsapp_messages_conversation",
        "whatsapp_messages",
        ["conversation_id", "created_at"],
    )
    op.create_index(
        "ix_whatsapp_messages_wamid",
        "whatsapp_messages",
        ["wamid"],
    )
    op.create_index(
        "ix_whatsapp_messages_status",
        "whatsapp_messages",
        ["tenant_id", "status"],
    )

    # 5. whatsapp_campaigns - Broadcast campaigns
    op.create_table(
        "whatsapp_campaigns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(50), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("segment_filters", postgresql.JSONB(), nullable=True),
        sa.Column("contact_ids", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("total_recipients", sa.Integer(), server_default="0", nullable=False),
        sa.Column("sent_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("delivered_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("read_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(
            ["account_id"], ["whatsapp_accounts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["template_id"], ["whatsapp_templates.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_whatsapp_campaigns_tenant_status",
        "whatsapp_campaigns",
        ["tenant_id", "status"],
    )

    # 6. whatsapp_campaign_recipients - Individual campaign recipients
    op.create_table(
        "whatsapp_campaign_recipients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(50), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("contact_id", sa.Integer(), nullable=True),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("contact_name", sa.String(200), nullable=True),
        sa.Column(
            "template_variables", postgresql.JSONB(), server_default="{}", nullable=False
        ),
        sa.Column("wamid", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["whatsapp_campaigns.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"], ["contacts.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_whatsapp_campaign_recipients_campaign_status",
        "whatsapp_campaign_recipients",
        ["campaign_id", "status"],
    )
    op.create_index(
        "ix_whatsapp_campaign_recipients_wamid",
        "whatsapp_campaign_recipients",
        ["wamid"],
    )


def downgrade() -> None:
    op.drop_table("whatsapp_campaign_recipients")
    op.drop_table("whatsapp_campaigns")
    op.drop_table("whatsapp_messages")
    op.drop_table("whatsapp_conversations")
    op.drop_table("whatsapp_templates")
    op.drop_table("whatsapp_accounts")
