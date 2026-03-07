"""Website tracking links for cross-channel attribution.

Revision ID: 043_tracking_links
Revises: 042_ab_testing
Create Date: 2024-03-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision: str = "043"
down_revision: Union[str, None] = "042"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tracking Links table
    op.create_table(
        "tracking_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "contact_id",
            sa.Integer(),
            sa.ForeignKey("contacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pipeline_id",
            sa.Integer(),
            sa.ForeignKey("engagement_pipelines.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "enrollment_id",
            sa.Integer(),
            sa.ForeignKey("pipeline_enrollments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Link configuration
        sa.Column("token", sa.String(100), nullable=False, unique=True),  # Encrypted/short token
        sa.Column("target_url", sa.String(2000), nullable=False),  # Destination URL
        sa.Column("short_code", sa.String(20), nullable=True),  # Optional short code
        # UTM parameters
        sa.Column("utm_source", sa.String(100), nullable=True),  # linkedin, email, whatsapp, etc.
        sa.Column("utm_medium", sa.String(100), nullable=True),  # message, campaign, broadcast
        sa.Column("utm_campaign", sa.String(200), nullable=True),  # Pipeline slug or custom
        sa.Column("utm_content", sa.String(200), nullable=True),  # A/B variant, etc.
        sa.Column("utm_term", sa.String(200), nullable=True),  # Additional tracking
        # Statistics
        sa.Column("click_count", sa.Integer(), nullable=False, default=0),
        sa.Column("first_click_at", sa.DateTime(), nullable=True),
        sa.Column("last_click_at", sa.DateTime(), nullable=True),
        # Lifecycle
        sa.Column("expires_at", sa.DateTime(), nullable=True),  # Optional expiration
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Website Events table (for tracking pixel events)
    op.create_table(
        "tracking_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tracking_link_id",
            sa.Integer(),
            sa.ForeignKey("tracking_links.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "contact_id",
            sa.Integer(),
            sa.ForeignKey("contacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Event data
        sa.Column("event_type", sa.String(100), nullable=False),  # page_view, scroll_50, form_submit, etc.
        sa.Column("url", sa.String(2000), nullable=True),
        sa.Column("referrer", sa.String(2000), nullable=True),
        # UTM data (captured at event time)
        sa.Column("utm_source", sa.String(100), nullable=True),
        sa.Column("utm_medium", sa.String(100), nullable=True),
        sa.Column("utm_campaign", sa.String(200), nullable=True),
        sa.Column("utm_content", sa.String(200), nullable=True),
        # Client info
        sa.Column("ip_address", sa.String(45), nullable=True),  # IPv6 compatible
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("device_type", sa.String(50), nullable=True),  # desktop, mobile, tablet
        # Additional data
        sa.Column("metadata_", postgresql.JSONB(), nullable=True),
        # Timestamps
        sa.Column("event_time", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=sa.func.now()),
    )

    # Attribution records (for conversion tracking)
    op.create_table(
        "attribution_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "contact_id",
            sa.Integer(),
            sa.ForeignKey("contacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pipeline_id",
            sa.Integer(),
            sa.ForeignKey("engagement_pipelines.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "enrollment_id",
            sa.Integer(),
            sa.ForeignKey("pipeline_enrollments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Attribution data
        sa.Column("conversion_type", sa.String(100), nullable=False),  # lead, demo, sale, etc.
        sa.Column("conversion_value", sa.Numeric(12, 2), nullable=True),  # Monetary value
        # First touch attribution
        sa.Column("first_touch_channel", sa.String(100), nullable=True),
        sa.Column("first_touch_source", sa.String(200), nullable=True),
        sa.Column("first_touch_at", sa.DateTime(), nullable=True),
        # Last touch attribution
        sa.Column("last_touch_channel", sa.String(100), nullable=True),
        sa.Column("last_touch_source", sa.String(200), nullable=True),
        sa.Column("last_touch_at", sa.DateTime(), nullable=True),
        # Full journey (all touchpoints)
        sa.Column("touchpoints", postgresql.JSONB(), nullable=True),  # Array of all touches
        sa.Column("touchpoint_count", sa.Integer(), nullable=False, default=0),
        # Timestamps
        sa.Column("converted_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=sa.func.now()),
    )

    # Create indexes
    op.create_index("ix_tracking_links_tenant", "tracking_links", ["tenant_id"])
    op.create_index("ix_tracking_links_contact", "tracking_links", ["contact_id"])
    op.create_index("ix_tracking_links_token", "tracking_links", ["token"], unique=True)
    op.create_index("ix_tracking_links_short_code", "tracking_links", ["short_code"])
    op.create_index("ix_tracking_links_pipeline", "tracking_links", ["pipeline_id"])

    op.create_index("ix_tracking_events_tenant", "tracking_events", ["tenant_id"])
    op.create_index("ix_tracking_events_link", "tracking_events", ["tracking_link_id"])
    op.create_index("ix_tracking_events_contact", "tracking_events", ["contact_id"])
    op.create_index("ix_tracking_events_time", "tracking_events", ["tenant_id", "event_time"])

    op.create_index("ix_attribution_records_tenant", "attribution_records", ["tenant_id"])
    op.create_index("ix_attribution_records_contact", "attribution_records", ["contact_id"])
    op.create_index("ix_attribution_records_pipeline", "attribution_records", ["pipeline_id"])
    op.create_index("ix_attribution_records_converted", "attribution_records", ["tenant_id", "converted_at"])


def downgrade() -> None:
    op.drop_index("ix_attribution_records_converted", table_name="attribution_records")
    op.drop_index("ix_attribution_records_pipeline", table_name="attribution_records")
    op.drop_index("ix_attribution_records_contact", table_name="attribution_records")
    op.drop_index("ix_attribution_records_tenant", table_name="attribution_records")

    op.drop_index("ix_tracking_events_time", table_name="tracking_events")
    op.drop_index("ix_tracking_events_contact", table_name="tracking_events")
    op.drop_index("ix_tracking_events_link", table_name="tracking_events")
    op.drop_index("ix_tracking_events_tenant", table_name="tracking_events")

    op.drop_index("ix_tracking_links_pipeline", table_name="tracking_links")
    op.drop_index("ix_tracking_links_short_code", table_name="tracking_links")
    op.drop_index("ix_tracking_links_token", table_name="tracking_links")
    op.drop_index("ix_tracking_links_contact", table_name="tracking_links")
    op.drop_index("ix_tracking_links_tenant", table_name="tracking_links")

    op.drop_table("attribution_records")
    op.drop_table("tracking_events")
    op.drop_table("tracking_links")
