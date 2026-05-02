"""Email reply matching + sequence stop-on-reply + template design JSON.

Three orthogonal additions for the cold-outreach flow:

1. ``email_recipients.message_id`` — RFC822 Message-ID header value we set
   on outbound mails so we can match replies via the In-Reply-To /
   References headers. Distinct from ``provider_message_id`` which stores
   the value the provider returns after API submission.

2. ``email_sequence_enrollments.stopped_on_reply_at`` and
   ``stopped_reason`` — when a lead replies (or unsubscribes), the worker
   skips further sequence steps. Reason is one of: reply, unsubscribe,
   bounce, manual.

3. ``email_templates.design_json`` — visual editor (react-email-editor)
   stores its design state here so users can re-edit templates. The
   versioned HTML output stays in ``html_content`` and is what we send.

Revision ID: 078
Revises: 077
Create Date: 2026-04-30
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "078"
down_revision: str | None = "077"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "email_recipients",
        sa.Column("message_id", sa.String(length=200), nullable=True),
    )
    op.create_index(
        "ix_email_recipients_message_id",
        "email_recipients",
        ["message_id"],
        unique=False,
    )

    op.add_column(
        "email_sequence_enrollments",
        sa.Column("stopped_on_reply_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "email_sequence_enrollments",
        sa.Column("stopped_reason", sa.String(length=50), nullable=True),
    )

    op.add_column(
        "email_templates",
        sa.Column("design_json", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("email_templates", "design_json")
    op.drop_column("email_sequence_enrollments", "stopped_reason")
    op.drop_column("email_sequence_enrollments", "stopped_on_reply_at")
    op.drop_index(
        "ix_email_recipients_message_id", table_name="email_recipients"
    )
    op.drop_column("email_recipients", "message_id")
