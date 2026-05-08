"""Add assistant category registry.

Revision ID: 059
Revises: 058
Create Date: 2026-03-16
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "059"
down_revision = "058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_category_registry",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "category_type",
            sa.String(length=20),
            nullable=False,
            server_default="fixed",
        ),
        sa.Column("color", sa.String(length=30), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "system_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_assistant_category_registry_tenant_name",
        ),
    )
    op.create_index(
        "ix_assistant_category_registry_tenant",
        "assistant_category_registry",
        ["tenant_id"],
    )
    op.create_index(
        "ix_assistant_category_registry_type",
        "assistant_category_registry",
        ["tenant_id", "category_type"],
    )
    op.create_index(
        "ix_assistant_category_registry_active",
        "assistant_category_registry",
        ["tenant_id", "active"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assistant_category_registry_active",
        table_name="assistant_category_registry",
    )
    op.drop_index(
        "ix_assistant_category_registry_type",
        table_name="assistant_category_registry",
    )
    op.drop_index(
        "ix_assistant_category_registry_tenant",
        table_name="assistant_category_registry",
    )
    op.drop_table("assistant_category_registry")
