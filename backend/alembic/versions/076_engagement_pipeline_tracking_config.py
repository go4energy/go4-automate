"""Engagement: per-pipeline tracking config (auto-hash + UTM defaults).

Adds a JSONB column to ``engagement_pipelines`` so each pipeline can carry:
- ``auto_create_tracking_hash`` (bool): on enrollment, ensure the contact has a
  customer-journey tracking hash (generated via ``app.contacts.utils``).
- ``utm_source`` / ``utm_medium`` / ``utm_campaign`` / ``utm_term`` /
  ``utm_content``: defaults injected into outbound URLs (letter, email, …).
- ``custom_params``: free-form key/value pairs the brain may use as
  template variables when generating links.

We use JSONB rather than separate columns so we don't need another
migration when adding a new attribution dimension.

Revision ID: 076
Revises: 075
Create Date: 2026-04-29
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "076"
down_revision = "075"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "engagement_pipelines",
        sa.Column(
            "tracking_config",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("engagement_pipelines", "tracking_config")
