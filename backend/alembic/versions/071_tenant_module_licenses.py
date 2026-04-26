"""Per-tenant module licensing.

Adds the ``tenant_module_licenses`` table — additive only, no existing
tables touched. The middleware that consumes this table runs in
permissive mode by default: if a tenant has zero licence rows, all
modules stay accessible. This means rolling out the migration is safe
on the running platform; gating is opt-in per tenant later.

Schema:
- tenant_id (FK, CASCADE on tenant delete)
- module_key (e.g. "leadgen", "engagement", "ads")
- enabled_at  — when the module was activated
- expires_at  — NULL means unlimited (Managed Service); set for trials
- plan_tier   — free-form label ("trial", "starter", "growth", "scale")
- metadata    — JSONB extras (limits, custom config)

Unique on (tenant_id, module_key) so re-activations update rather than
duplicate.

Revision ID: 071
Revises: 070
Create Date: 2026-04-27
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "071"
down_revision = "070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_module_licenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("module_key", sa.String(50), nullable=False),
        sa.Column(
            "enabled_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("plan_tier", sa.String(30), nullable=True),
        sa.Column(
            "metadata",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_unique_constraint(
        "uq_tenant_module_license",
        "tenant_module_licenses",
        ["tenant_id", "module_key"],
    )
    op.create_index(
        "ix_tenant_module_licenses_tenant",
        "tenant_module_licenses",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_module_licenses_tenant", "tenant_module_licenses")
    op.drop_constraint("uq_tenant_module_license", "tenant_module_licenses")
    op.drop_table("tenant_module_licenses")
