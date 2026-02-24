"""Briefing speakers table + XTTS fields on channels.

Revision ID: 021
Revises: 020
Create Date: 2026-02-24
"""

import sqlalchemy as sa

from alembic import op

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "briefing_speakers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("language", sa.String(10), nullable=False, server_default="de"),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("sample_rate", sa.Integer(), nullable=True),
        sa.Column("xtts_speaker_name", sa.String(200), nullable=True),
        sa.Column(
            "active", sa.Boolean(), nullable=False, server_default=sa.text("true")
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
        sa.UniqueConstraint(
            "tenant_id", "name", name="uq_briefing_speakers_tenant_name"
        ),
    )
    op.create_index(
        "ix_briefing_speakers_tenant",
        "briefing_speakers",
        ["tenant_id"],
    )

    # Extend briefing_channels with TTS engine override + speaker FK
    op.add_column(
        "briefing_channels",
        sa.Column("tts_engine", sa.String(20), nullable=True),
    )
    op.add_column(
        "briefing_channels",
        sa.Column(
            "xtts_speaker_id",
            sa.Integer(),
            sa.ForeignKey("briefing_speakers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("briefing_channels", "xtts_speaker_id")
    op.drop_column("briefing_channels", "tts_engine")
    op.drop_index("ix_briefing_speakers_tenant", table_name="briefing_speakers")
    op.drop_table("briefing_speakers")
