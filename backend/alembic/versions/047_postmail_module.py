"""Post-Mail module tables.

Revision ID: 047_postmail_module
Revises: 046_optimization_engine
Create Date: 2026-03-07

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "047"
down_revision = "046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostmailTemplate - Brief-Templates
    op.create_table(
        "postmail_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # Template content
        sa.Column("format", sa.String(20), nullable=False, server_default="a4"),
        sa.Column("content_html", sa.Text(), nullable=False),
        sa.Column("header_html", sa.Text(), nullable=True),
        sa.Column("footer_html", sa.Text(), nullable=True),
        # Preview
        sa.Column("preview_image", sa.Text(), nullable=True),
        # Lifecycle
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_postmail_templates_tenant", "postmail_templates", ["tenant_id"]
    )

    # PostmailBatch - Batch for bulk sending
    op.create_table(
        "postmail_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("letter_count", sa.Integer(), nullable=False, server_default="0"),
        # Export
        sa.Column("export_format", sa.String(20), nullable=True),
        sa.Column("export_path", sa.String(500), nullable=True),
        # Status: collecting, ready, exported, sent
        sa.Column("status", sa.String(20), nullable=False, server_default="collecting"),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        # Lifecycle
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_postmail_batches_tenant", "postmail_batches", ["tenant_id"])
    op.create_index("ix_postmail_batches_status", "postmail_batches", ["status"])

    # PostmailLetter - Individual letters
    op.create_table(
        "postmail_letters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        # References
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("contact_id", sa.Integer(), nullable=True),
        sa.Column("pipeline_id", sa.Integer(), nullable=True),
        sa.Column("pending_action_id", sa.Integer(), nullable=True),
        sa.Column("batch_id", sa.Integer(), nullable=True),
        # Recipient
        sa.Column("recipient_name", sa.String(200), nullable=False),
        sa.Column("recipient_company", sa.String(200), nullable=True),
        sa.Column("recipient_street", sa.String(200), nullable=True),
        sa.Column("recipient_zip", sa.String(20), nullable=True),
        sa.Column("recipient_city", sa.String(100), nullable=True),
        sa.Column("recipient_country", sa.String(10), nullable=False, server_default="DE"),
        # Content
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        # Status: draft, approved, queued, sent, delivered, returned
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("return_reason", sa.String(200), nullable=True),
        # Lifecycle
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["template_id"], ["postmail_templates.id"]),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"]),
        sa.ForeignKeyConstraint(["batch_id"], ["postmail_batches.id"]),
    )
    op.create_index("ix_postmail_letters_tenant", "postmail_letters", ["tenant_id"])
    op.create_index("ix_postmail_letters_status", "postmail_letters", ["status"])
    op.create_index("ix_postmail_letters_contact", "postmail_letters", ["contact_id"])
    op.create_index("ix_postmail_letters_batch", "postmail_letters", ["batch_id"])


def downgrade() -> None:
    op.drop_table("postmail_letters")
    op.drop_table("postmail_batches")
    op.drop_table("postmail_templates")
