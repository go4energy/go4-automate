"""Research agent - sources, findings, topic suggestions.

Revision ID: 006
Revises: 005
Create Date: 2026-02-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create research_sources, research_findings, topic_suggestions tables."""
    op.create_table(
        "research_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("keywords", postgresql.JSONB(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "fetch_interval_hours", sa.Integer(), nullable=False, server_default="24"
        ),
        sa.Column("last_fetched_at", sa.DateTime(), nullable=True),
        sa.Column("config", postgresql.JSONB(), nullable=True),
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
    )
    op.create_index(
        "ix_research_sources_tenant_active",
        "research_sources",
        ["tenant_id", "active"],
    )
    op.create_index(
        "ix_research_sources_tenant_type",
        "research_sources",
        ["tenant_id", "source_type"],
    )

    op.create_table(
        "research_findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("research_sources.id"),
            nullable=True,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("content_snippet", sa.Text(), nullable=True),
        sa.Column("found_at", sa.DateTime(), nullable=False),
        sa.Column("topics_extracted", postgresql.JSONB(), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
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
        sa.UniqueConstraint("tenant_id", "url", name="uq_research_findings_tenant_url"),
    )
    op.create_index(
        "ix_research_findings_tenant_status",
        "research_findings",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_research_findings_tenant_source",
        "research_findings",
        ["tenant_id", "source_id"],
    )

    op.create_table(
        "topic_suggestions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "finding_id",
            sa.Integer(),
            sa.ForeignKey("research_findings.id"),
            nullable=True,
        ),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default="general"),
        sa.Column("platforms", postgresql.JSONB(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="3"),
        sa.Column(
            "source_type", sa.String(20), nullable=False, server_default="research"
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="suggested"),
        sa.Column(
            "content_piece_id",
            sa.Integer(),
            sa.ForeignKey("content_pieces.id"),
            nullable=True,
        ),
        sa.Column("image_url", sa.Text(), nullable=True),
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
    )
    op.create_index(
        "ix_topic_suggestions_tenant_status",
        "topic_suggestions",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_topic_suggestions_tenant_source_type",
        "topic_suggestions",
        ["tenant_id", "source_type"],
    )


def downgrade() -> None:
    """Drop research tables."""
    op.drop_table("topic_suggestions")
    op.drop_table("research_findings")
    op.drop_table("research_sources")
