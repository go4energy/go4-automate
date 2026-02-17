"""Ad management pipeline - extend ad_performances, add campaign configs and conversion events.

Revision ID: 004
Revises: 003
Create Date: 2026-02-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Extend ad_performances with new fields
    op.add_column(
        "ad_performances",
        sa.Column("campaign_name", sa.String(200), nullable=True),
    )
    op.add_column(
        "ad_performances",
        sa.Column("adset_id", sa.String(100), nullable=True),
    )
    op.add_column(
        "ad_performances",
        sa.Column("adset_name", sa.String(200), nullable=True),
    )
    op.add_column(
        "ad_performances",
        sa.Column("ad_id", sa.String(100), nullable=True),
    )
    op.add_column(
        "ad_performances",
        sa.Column("ad_name", sa.String(200), nullable=True),
    )
    op.add_column(
        "ad_performances",
        sa.Column("conversions", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "ad_performances",
        sa.Column(
            "conversion_value",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "ad_performances",
        sa.Column("cpc", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "ad_performances",
        sa.Column("ctr", sa.Numeric(5, 4), nullable=True),
    )
    op.add_column(
        "ad_performances",
        sa.Column("frequency", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "ad_performances",
        sa.Column("reach", sa.Integer(), nullable=True),
    )
    op.add_column(
        "ad_performances",
        sa.Column("budget_applied", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "ad_performances",
        sa.Column(
            "weather_boosted",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "ad_performances",
        sa.Column("optimization_action", sa.String(50), nullable=True),
    )

    # Create ad_campaign_configs table
    op.create_table(
        "ad_campaign_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column("campaign_id", sa.String(100), nullable=False),
        sa.Column("campaign_name", sa.String(200), nullable=True),
        sa.Column("platform", sa.String(30), nullable=False, server_default="'meta'"),
        sa.Column("status", sa.String(20), nullable=False, server_default="'active'"),
        sa.Column("target_cpl", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_cpl", sa.Numeric(10, 2), nullable=True),
        sa.Column("daily_budget_min", sa.Numeric(10, 2), nullable=True),
        sa.Column("daily_budget_max", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "weather_boost_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "weather_boost_factor",
            sa.Numeric(3, 2),
            nullable=False,
            server_default="1.5",
        ),
        sa.Column(
            "auto_optimize",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "optimization_rules",
            postgresql.JSONB(),
            nullable=True,
            server_default="'{}'",
        ),
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
        "ix_ad_campaign_configs_tenant",
        "ad_campaign_configs",
        ["tenant_id", "campaign_id"],
    )

    # Create conversion_events table
    op.create_table(
        "conversion_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column("event_name", sa.String(50), nullable=False),
        sa.Column("event_time", sa.DateTime(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("fbc", sa.String(200), nullable=True),
        sa.Column("fbp", sa.String(200), nullable=True),
        sa.Column("email_hash", sa.String(64), nullable=True),
        sa.Column("phone_hash", sa.String(64), nullable=True),
        sa.Column("custom_data", postgresql.JSONB(), nullable=True),
        sa.Column(
            "sent_to_meta",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("meta_response", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_conv_tenant_event",
        "conversion_events",
        ["tenant_id", "event_name"],
    )
    op.create_index(
        "ix_conv_time",
        "conversion_events",
        ["event_time"],
    )


def downgrade() -> None:
    op.drop_table("conversion_events")
    op.drop_table("ad_campaign_configs")

    # Remove extended fields from ad_performances
    for col in [
        "optimization_action",
        "weather_boosted",
        "budget_applied",
        "reach",
        "frequency",
        "ctr",
        "cpc",
        "conversion_value",
        "conversions",
        "ad_name",
        "ad_id",
        "adset_name",
        "adset_id",
        "campaign_name",
    ]:
        op.drop_column("ad_performances", col)
