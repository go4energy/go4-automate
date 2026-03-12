"""Module parameters table for dynamic onboarding.

Revision ID: 036_module_parameters
Revises: 035_ai_setup_system
Create Date: 2025-03-06
"""

from alembic import op
import sqlalchemy as sa

revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "module_parameters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("module", sa.String(50), nullable=False),
        sa.Column("variable", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("var_type", sa.String(20), server_default="string", nullable=False),
        sa.Column("required", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "module", "variable", name="uq_module_param"),
    )
    op.create_index(
        "ix_module_parameters_tenant_module",
        "module_parameters",
        ["tenant_id", "module"],
    )


def downgrade() -> None:
    op.drop_index("ix_module_parameters_tenant_module")
    op.drop_table("module_parameters")
