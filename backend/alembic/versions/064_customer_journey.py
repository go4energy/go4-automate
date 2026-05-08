"""Customer Journey module - new tables and contact extensions.

Revision ID: 064
Revises: 063
Create Date: 2026-03-24
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "064"
down_revision = "063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create journey tables and extend contacts."""
    # --- Extend contacts table ---
    op.add_column(
        "contacts", sa.Column("tracking_hash", sa.String(12), nullable=True)
    )
    op.add_column(
        "contacts", sa.Column("journey_status", sa.String(20), nullable=True)
    )
    op.add_column(
        "contacts", sa.Column("odoo_id", sa.Integer(), nullable=True)
    )
    op.create_index(
        "ix_contacts_tracking_hash",
        "contacts",
        ["tracking_hash"],
        unique=True,
        postgresql_where=sa.text("tracking_hash IS NOT NULL"),
    )

    # --- journey_campaigns ---
    op.create_table(
        "journey_campaigns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("channel", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_journey_campaigns_tenant",
        "journey_campaigns",
        ["tenant_id"],
    )

    # --- journey_ref_codes ---
    op.create_table(
        "journey_ref_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(50), nullable=False),
        sa.Column("contact_id", sa.Integer(), nullable=True),
        sa.Column("campaign_id", sa.Integer(), nullable=True),
        sa.Column("ref_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("context", sa.String(200), nullable=True),
        sa.Column("target_url", sa.String(500), nullable=True),
        sa.Column("notify_on_visit", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notify_channel", sa.String(20), nullable=False, server_default="none"),
        sa.Column("notify_target", sa.String(200), nullable=True),
        sa.Column("visit_count", sa.Integer(), nullable=False, server_default="0"),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(
            ["contact_id"], ["contacts.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["journey_campaigns.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "ref_code", name="uq_journey_ref_code"),
    )
    op.create_index(
        "ix_journey_refs_tenant", "journey_ref_codes", ["tenant_id"]
    )
    op.create_index(
        "ix_journey_refs_contact",
        "journey_ref_codes",
        ["tenant_id", "contact_id"],
    )

    # --- journey_events ---
    op.create_table(
        "journey_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(50), nullable=False),
        sa.Column("contact_id", sa.Integer(), nullable=True),
        sa.Column("event", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("page_path", sa.String(500), nullable=True),
        sa.Column(
            "source_site",
            sa.String(100),
            nullable=False,
            server_default="go4.energy",
        ),
        sa.Column("utm_source", sa.String(100), nullable=True),
        sa.Column("utm_medium", sa.String(100), nullable=True),
        sa.Column("utm_campaign", sa.String(100), nullable=True),
        sa.Column("ref_code", sa.String(20), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(
            ["contact_id"], ["contacts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_journey_events_contact",
        "journey_events",
        ["tenant_id", "contact_id"],
    )
    op.create_index(
        "ix_journey_events_time", "journey_events", ["created_at"]
    )
    op.create_index(
        "ix_journey_events_event", "journey_events", ["event"]
    )


def downgrade() -> None:
    """Remove journey tables and contact extensions."""
    op.drop_table("journey_events")
    op.drop_table("journey_ref_codes")
    op.drop_table("journey_campaigns")

    op.drop_index("ix_contacts_tracking_hash", table_name="contacts")
    op.drop_column("contacts", "odoo_id")
    op.drop_column("contacts", "journey_status")
    op.drop_column("contacts", "tracking_hash")
