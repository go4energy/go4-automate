"""Per-pipeline channel-specific prompts.

Each engagement pipeline can hold any number of LLM prompts, scoped to a
channel (email, letter, whatsapp, linkedin, phone) and a slot (initial,
followup_1, reply, ...). The Brain looks up the matching prompt at runtime
when generating the body for a touch.

Revision ID: 083
Revises: 082
Create Date: 2026-05-03
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "083"
down_revision: str | None = "082"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "pipeline_prompts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(length=50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "pipeline_id",
            sa.Integer(),
            sa.ForeignKey("engagement_pipelines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(length=30), nullable=False),
        sa.Column("slot", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column(
            "model",
            sa.String(length=100),
            nullable=True,
        ),  # null -> use Standard class default
        sa.Column(
            "temperature",
            sa.Float(),
            nullable=False,
            server_default="0.7",
        ),
        sa.Column(
            "max_tokens",
            sa.Integer(),
            nullable=False,
            server_default="600",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
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
        "ix_pipeline_prompts_lookup",
        "pipeline_prompts",
        ["tenant_id", "pipeline_id", "channel", "slot"],
    )
    op.create_index(
        "ix_pipeline_prompts_pipeline",
        "pipeline_prompts",
        ["pipeline_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_pipeline_prompts_pipeline", table_name="pipeline_prompts")
    op.drop_index("ix_pipeline_prompts_lookup", table_name="pipeline_prompts")
    op.drop_table("pipeline_prompts")
