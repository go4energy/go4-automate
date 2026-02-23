"""Collector groups — thematic grouping for sources, findings, topics, snapshots.

Revision ID: 013
Revises: 012
Create Date: 2026-02-22
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create collector_groups table and add group_id FK to existing tables."""
    # 1. Create collector_groups table
    op.create_table(
        "collector_groups",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "fetch_interval_hours", sa.Integer, nullable=False, server_default="24"
        ),
        sa.Column("distribution_channels", JSONB, nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "tenant_id", "slug", name="uq_collector_groups_tenant_slug"
        ),
    )
    op.create_index(
        "ix_collector_groups_tenant_active",
        "collector_groups",
        ["tenant_id", "active"],
    )

    # 2. Add group_id column to existing tables
    for table in [
        "collector_sources",
        "collector_findings",
        "collector_topics",
        "collector_snapshots",
    ]:
        op.add_column(
            table,
            sa.Column(
                "group_id",
                sa.Integer,
                sa.ForeignKey("collector_groups.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index(f"ix_{table}_group_id", table, ["group_id"])

    # 3. Data migration: create default "Allgemein" group per tenant
    conn = op.get_bind()
    tenants = conn.execute(sa.text("SELECT tenant_id FROM tenants")).fetchall()

    for (tenant_id,) in tenants:
        result = conn.execute(
            sa.text(
                "INSERT INTO collector_groups (tenant_id, name, slug, fetch_interval_hours, tags) "
                "VALUES (:tid, 'Allgemein', 'allgemein', 24, '[]') RETURNING id"
            ),
            {"tid": tenant_id},
        )
        group_id = result.fetchone()[0]

        for table in [
            "collector_sources",
            "collector_findings",
            "collector_topics",
            "collector_snapshots",
        ]:
            conn.execute(
                sa.text(
                    f"UPDATE {table} SET group_id = :gid WHERE tenant_id = :tid AND group_id IS NULL"
                ),
                {"gid": group_id, "tid": tenant_id},
            )


def downgrade() -> None:
    """Remove group_id columns and drop collector_groups table."""
    for table in [
        "collector_snapshots",
        "collector_topics",
        "collector_findings",
        "collector_sources",
    ]:
        op.drop_index(f"ix_{table}_group_id", table_name=table)
        op.drop_column(table, "group_id")

    op.drop_index("ix_collector_groups_tenant_active", table_name="collector_groups")
    op.drop_table("collector_groups")
