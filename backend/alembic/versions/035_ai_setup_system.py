"""AI Setup System - module_contexts table and prompt extensions.

Revision ID: 035
Revises: 034
Create Date: 2024-03-06 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create module_contexts table for storing extracted AI parameters
    op.create_table(
        "module_contexts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(50), nullable=False),
        sa.Column("module", sa.String(50), nullable=False),
        sa.Column(
            "context_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, default=False),
        sa.Column("onboarding_notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.tenant_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "module", name="uq_module_context_tenant_module"
        ),
    )
    op.create_index(
        "ix_module_context_tenant", "module_contexts", ["tenant_id"], unique=False
    )
    op.create_index(
        "ix_module_context_module", "module_contexts", ["module"], unique=False
    )

    # 2. Add new columns to prompts table
    op.add_column(
        "prompts",
        sa.Column(
            "module", sa.String(50), nullable=False, server_default="global"
        ),
    )
    op.add_column(
        "prompts",
        sa.Column(
            "prompt_type", sa.String(20), nullable=False, server_default="productive"
        ),
    )
    op.add_column(
        "prompts",
        sa.Column(
            "is_system", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "prompts",
        sa.Column(
            "variables_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # 3. Add indexes for new prompt columns
    op.create_index(
        "ix_prompt_tenant_module", "prompts", ["tenant_id", "module"], unique=False
    )
    op.create_index(
        "ix_prompt_module_type", "prompts", ["module", "prompt_type"], unique=False
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_prompt_module_type", table_name="prompts")
    op.drop_index("ix_prompt_tenant_module", table_name="prompts")

    # Drop new columns from prompts
    op.drop_column("prompts", "variables_schema")
    op.drop_column("prompts", "is_system")
    op.drop_column("prompts", "prompt_type")
    op.drop_column("prompts", "module")

    # Drop module_contexts table
    op.drop_index("ix_module_context_module", table_name="module_contexts")
    op.drop_index("ix_module_context_tenant", table_name="module_contexts")
    op.drop_table("module_contexts")
