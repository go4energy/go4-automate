"""Email assets (uploaded images) + per-template AI chat persistence.

Two related tables for the rich-template-editor:

- ``email_assets`` — User-uploaded images/files, tenant-scoped, served
  via FastAPI StaticFiles at ``/api/static/email-assets/{tenant}/{uuid}.ext``.
  ``EmailTemplate`` references them by URL inside ``html_content``.

- ``email_template_chats`` — Persistent Claude chat per template so the
  user can come back, see history, continue the conversation. Each row
  is one message (system / user / assistant / tool).

Revision ID: 080
Revises: 079
Create Date: 2026-05-02
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "080"
down_revision: str | None = "079"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "email_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(length=50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=200), nullable=False),
        sa.Column("original_filename", sa.String(length=300), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("url_path", sa.String(length=500), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_email_assets_tenant",
        "email_assets",
        ["tenant_id"],
    )

    op.create_table(
        "email_template_chats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(length=50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("email_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
        ),  # user | assistant | tool
        sa.Column("content", sa.Text(), nullable=True),
        # When role='assistant' and Claude called tools, store the tool_use blocks here
        # When role='tool', store the tool_result content here
        sa.Column("tool_calls", JSONB(), nullable=True),
        sa.Column("tool_use_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_email_template_chats_template",
        "email_template_chats",
        ["template_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_email_template_chats_template", table_name="email_template_chats"
    )
    op.drop_table("email_template_chats")
    op.drop_index("ix_email_assets_tenant", table_name="email_assets")
    op.drop_table("email_assets")
