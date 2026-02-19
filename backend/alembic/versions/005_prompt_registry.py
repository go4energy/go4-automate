"""Prompt registry - configurable prompt templates with versioning.

Revision ID: 005
Revises: 004
Create Date: 2026-02-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "prompts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(50), nullable=False, server_default="general"),
        # Template fields
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt", sa.Text(), nullable=False),
        # Variable definitions
        sa.Column("variables", postgresql.JSONB(), nullable=True),
        # Output configuration
        sa.Column(
            "output_format", sa.String(20), nullable=False, server_default="text"
        ),
        sa.Column("output_schema", postgresql.JSONB(), nullable=True),
        # LLM configuration
        sa.Column(
            "provider", sa.String(30), nullable=False, server_default="anthropic"
        ),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="2048"),
        # Versioning
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
        ),
        # Constraints
        sa.UniqueConstraint(
            "tenant_id", "slug", "version", name="uq_prompt_tenant_slug_version"
        ),
    )
    op.create_index("ix_prompt_tenant_slug", "prompts", ["tenant_id", "slug"])
    op.create_index("ix_prompt_tenant_category", "prompts", ["tenant_id", "category"])
    op.create_index("ix_prompt_tenant_active", "prompts", ["tenant_id", "is_active"])


def downgrade() -> None:
    op.drop_table("prompts")
