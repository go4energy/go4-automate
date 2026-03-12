"""Rename distributor tables to campaigns.

Revision ID: 024_rename_distributor
Revises: 023_crm_pipelines_deals
Create Date: 2026-02-25 22:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "024"
down_revision: str | None = "023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Rename tables
    op.rename_table("distributor_campaigns", "campaigns")
    op.rename_table("distributor_performances", "campaign_performances")
    op.rename_table("distributor_campaign_configs", "campaign_configs")
    op.rename_table("distributor_conversions", "campaign_conversions")

    # Rename indexes for campaigns table
    op.execute(
        "ALTER INDEX IF EXISTS ix_distributor_campaigns_tenant_status "
        "RENAME TO ix_campaigns_tenant_status"
    )

    # Rename indexes for campaign_performances table
    op.execute(
        "ALTER INDEX IF EXISTS ix_distributor_performance_tenant_date "
        "RENAME TO ix_campaign_performance_tenant_date"
    )

    # Rename indexes for campaign_configs table
    op.execute(
        "ALTER INDEX IF EXISTS ix_distributor_campaign_configs_tenant "
        "RENAME TO ix_campaign_configs_tenant"
    )

    # Rename indexes for campaign_conversions table
    op.execute(
        "ALTER INDEX IF EXISTS ix_dist_conv_tenant_event "
        "RENAME TO ix_campaign_conv_tenant_event"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_dist_conv_time "
        "RENAME TO ix_campaign_conv_time"
    )

    # Note: ad_campaign_id column name stays the same, FK reference updated via table rename


def downgrade() -> None:
    # Rename tables back
    op.rename_table("campaigns", "distributor_campaigns")
    op.rename_table("campaign_performances", "distributor_performances")
    op.rename_table("campaign_configs", "distributor_campaign_configs")
    op.rename_table("campaign_conversions", "distributor_conversions")

    # Rename indexes back
    op.execute(
        "ALTER INDEX IF EXISTS ix_campaigns_tenant_status "
        "RENAME TO ix_distributor_campaigns_tenant_status"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_campaign_performance_tenant_date "
        "RENAME TO ix_distributor_performance_tenant_date"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_campaign_configs_tenant "
        "RENAME TO ix_distributor_campaign_configs_tenant"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_campaign_conv_tenant_event "
        "RENAME TO ix_dist_conv_tenant_event"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_campaign_conv_time "
        "RENAME TO ix_dist_conv_time"
    )
