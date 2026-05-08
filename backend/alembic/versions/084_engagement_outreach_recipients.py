"""Engagement-driven outreach: per-recipient tracking + structured Brain output.

Adds the columns we need so the Brain → Render → Send → Reply-Match loop can
work end-to-end:

- ``email_recipients.campaign_id`` becomes nullable (engagement uses 1-to-1
  outreach, no campaign).
- ``email_recipients.pending_action_id`` links a sent mail to the Brain
  action that triggered it (for re-render, history, attribution).
- ``email_recipients.subject_rendered`` keeps the final subject as it
  actually went out (the canonical record after templating).
- ``email_recipients.personalized_inputs`` stores the Brain-generated
  pieces (e.g. ``{"llm_subject": "...", "llm_body": "..."}``) so we can
  re-render the body later for the contact-detail preview without
  re-calling the LLM.
- ``engagement_pipelines.bulk_brain_status`` is a small JSONB blob the
  bulk-Brain-runner writes progress into so the UI can poll a counter.

Revision ID: 084
Revises: 083
Create Date: 2026-05-03
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "084"
down_revision: str | None = "083"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Allow null campaign_id so engagement-driven outreach can write here too.
    op.alter_column(
        "email_recipients",
        "campaign_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.add_column(
        "email_recipients",
        sa.Column(
            "pending_action_id",
            sa.Integer(),
            sa.ForeignKey("pending_actions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "email_recipients",
        sa.Column("subject_rendered", sa.Text(), nullable=True),
    )
    op.add_column(
        "email_recipients",
        sa.Column("personalized_inputs", JSONB(), nullable=True),
    )
    op.create_index(
        "ix_email_recipients_pending_action",
        "email_recipients",
        ["pending_action_id"],
    )

    op.add_column(
        "engagement_pipelines",
        sa.Column("bulk_brain_status", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("engagement_pipelines", "bulk_brain_status")
    op.drop_index(
        "ix_email_recipients_pending_action", table_name="email_recipients"
    )
    op.drop_column("email_recipients", "personalized_inputs")
    op.drop_column("email_recipients", "subject_rendered")
    op.drop_column("email_recipients", "pending_action_id")
    op.alter_column(
        "email_recipients",
        "campaign_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
