"""Intel module — initial schema.

Adds pgvector extension + five tables for the Marketing-Intelligence
module:

- ``intel_watch_target``   — Wettbewerber/Regulator/Markt-Segment im Visier
- ``intel_source``         — Konkrete URLs/Endpoints zum Watch-Target
- ``intel_snapshot``       — Fetch-Resultat mit Text + Embedding (1024d)
- ``intel_change_event``   — erkannter Wechsel zwischen zwei Snapshots
- ``intel_briefing``       — verdichtetes Tages-/Wochenbriefing (JSONB)

Embeddings nutzen pgvector (Postgres-Extension). Vector-Dimension 1024
passt zu ``BAAI/bge-m3`` (lokal via TEI im docker_go4net).

Vor dieser Migration muss ``pgvector/pgvector:pg16`` als Postgres-Image
laufen, sonst schlägt ``CREATE EXTENSION vector`` fehl.

Revision ID: 089
Revises: 088
Create Date: 2026-05-08
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "089"
down_revision: str | None = "088"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # ── intel_watch_target ────────────────────────────────────────────
    op.create_table(
        "intel_watch_target",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "kind",
            sa.String(30),
            nullable=False,
            comment="competitor | regulator | segment",
        ),
        sa.Column("context", JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_intel_watch_target_tenant", "intel_watch_target", ["tenant_id"])
    op.create_index(
        "ix_intel_watch_target_active",
        "intel_watch_target",
        ["tenant_id", "is_active"],
    )

    # ── intel_source ──────────────────────────────────────────────────
    op.create_table(
        "intel_source",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            sa.Integer,
            sa.ForeignKey("intel_watch_target.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "adapter",
            sa.String(40),
            nullable=False,
            comment="web | web_js | rss | jobs_board | structured_api",
        ),
        sa.Column("config", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "fetch_interval_sec",
            sa.Integer,
            nullable=False,
            server_default=sa.text("3600"),
        ),
        sa.Column("last_fetched_at", sa.DateTime, nullable=True),
        sa.Column(
            "last_status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
            comment="pending | ok | failed",
        ),
        sa.Column(
            "consecutive_failures",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_intel_source_tenant", "intel_source", ["tenant_id"])
    op.create_index("ix_intel_source_target", "intel_source", ["target_id"])
    op.create_index(
        "ix_intel_source_due",
        "intel_source",
        ["is_active", "last_fetched_at"],
    )

    # ── intel_snapshot (with pgvector embedding) ──────────────────────
    op.create_table(
        "intel_snapshot",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.Integer,
            sa.ForeignKey("intel_source.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fetched_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("parsed", JSONB, nullable=True),
        sa.Column(
            "embedding",
            Vector(1024),
            nullable=True,
            comment="BAAI/bge-m3 via local TEI; NULL when TEI unreachable",
        ),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("byte_size", sa.Integer, nullable=True),
    )
    op.create_index("ix_intel_snapshot_tenant", "intel_snapshot", ["tenant_id"])
    op.create_index(
        "ix_intel_snapshot_source_fetched",
        "intel_snapshot",
        ["source_id", "fetched_at"],
    )
    op.create_index(
        "ix_intel_snapshot_content_hash",
        "intel_snapshot",
        ["source_id", "content_hash"],
    )
    # HNSW index over the embedding for cosine similarity search.
    # Note: HNSW indexes in pgvector don't support per-tenant filtering at
    # the index level — we filter via WHERE source_id IN (...) at query time.
    op.execute(
        "CREATE INDEX ix_intel_snapshot_embedding "
        "ON intel_snapshot USING hnsw (embedding vector_cosine_ops) "
        "WHERE embedding IS NOT NULL;"
    )

    # ── intel_change_event ────────────────────────────────────────────
    op.create_table(
        "intel_change_event",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.Integer,
            sa.ForeignKey("intel_source.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prev_snapshot_id",
            sa.Integer,
            sa.ForeignKey("intel_snapshot.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "new_snapshot_id",
            sa.Integer,
            sa.ForeignKey("intel_snapshot.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "change_type",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'unclassified'"),
        ),
        sa.Column(
            "significance",
            sa.Numeric(3, 2),
            nullable=False,
            server_default=sa.text("0.50"),
        ),
        sa.Column("raw_diff", JSONB, nullable=True),
        sa.Column("headline", sa.String(500), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("impact_assessment", sa.Text, nullable=True),
        sa.Column("evidence", JSONB, nullable=True),
        sa.Column("processed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column(
            "engagement_action_id",
            sa.Integer,
            sa.ForeignKey("pending_actions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_intel_change_event_tenant", "intel_change_event", ["tenant_id"])
    op.create_index("ix_intel_change_event_source", "intel_change_event", ["source_id"])
    op.create_index(
        "ix_intel_change_event_significance",
        "intel_change_event",
        ["tenant_id", "significance"],
    )

    # ── intel_briefing ────────────────────────────────────────────────
    op.create_table(
        "intel_briefing",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("briefing_uuid", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("period_start", sa.DateTime, nullable=False),
        sa.Column("period_end", sa.DateTime, nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("tts_summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_intel_briefing_tenant", "intel_briefing", ["tenant_id"])
    op.create_index(
        "ix_intel_briefing_period",
        "intel_briefing",
        ["tenant_id", "period_end"],
    )


def downgrade() -> None:
    # Drop tables only, leave the pgvector extension installed —
    # other migrations / modules might rely on it later.
    op.drop_index("ix_intel_briefing_period", table_name="intel_briefing")
    op.drop_index("ix_intel_briefing_tenant", table_name="intel_briefing")
    op.drop_table("intel_briefing")

    op.drop_index("ix_intel_change_event_significance", table_name="intel_change_event")
    op.drop_index("ix_intel_change_event_source", table_name="intel_change_event")
    op.drop_index("ix_intel_change_event_tenant", table_name="intel_change_event")
    op.drop_table("intel_change_event")

    op.execute("DROP INDEX IF EXISTS ix_intel_snapshot_embedding;")
    op.drop_index("ix_intel_snapshot_content_hash", table_name="intel_snapshot")
    op.drop_index("ix_intel_snapshot_source_fetched", table_name="intel_snapshot")
    op.drop_index("ix_intel_snapshot_tenant", table_name="intel_snapshot")
    op.drop_table("intel_snapshot")

    op.drop_index("ix_intel_source_due", table_name="intel_source")
    op.drop_index("ix_intel_source_target", table_name="intel_source")
    op.drop_index("ix_intel_source_tenant", table_name="intel_source")
    op.drop_table("intel_source")

    op.drop_index("ix_intel_watch_target_active", table_name="intel_watch_target")
    op.drop_index("ix_intel_watch_target_tenant", table_name="intel_watch_target")
    op.drop_table("intel_watch_target")
