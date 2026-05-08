"""Auto-Enrollment-Filter + Forward-Lead-Audit + Enrollment-Stop-Reason.

Drei Erweiterungen für das generische Tag-basierte Auto-Enrollment:

1. ``engagement_pipelines.auto_enroll_filter`` (JSONB, nullable) — Filter-Spec
   ``{tags_any, tags_all, tags_none, custom_fields}``. NULL = manuell only.
2. ``contacts.source_contact_id`` (FK contacts) — Forward-Audit, zeigt vom
   Empfänger (Meier) auf den ursprünglichen Cold-Mail-Adressaten (Müller).
3. ``pipeline_enrollments.stopped_reason`` — strukturierter Stop-Grund (z.B.
   ``forwarded_to_colleague``, ``converted_via_signup``). ``source_context``
   existiert bereits seit Migration 039.

Revision ID: 088
Revises: 087
Create Date: 2026-05-08
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "088"
down_revision: str | None = "087"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "engagement_pipelines",
        sa.Column("auto_enroll_filter", JSONB, nullable=True),
    )
    op.create_index(
        "ix_engagement_pipelines_auto_enroll",
        "engagement_pipelines",
        ["auto_enroll_filter"],
        postgresql_using="gin",
        postgresql_where=sa.text("auto_enroll_filter IS NOT NULL"),
    )

    op.add_column(
        "contacts",
        sa.Column(
            "source_contact_id",
            sa.Integer(),
            sa.ForeignKey("contacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_contacts_source_contact",
        "contacts",
        ["source_contact_id"],
    )

    op.add_column(
        "pipeline_enrollments",
        sa.Column("stopped_reason", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pipeline_enrollments", "stopped_reason")
    op.drop_index("ix_contacts_source_contact", table_name="contacts")
    op.drop_column("contacts", "source_contact_id")
    op.drop_index(
        "ix_engagement_pipelines_auto_enroll",
        table_name="engagement_pipelines",
    )
    op.drop_column("engagement_pipelines", "auto_enroll_filter")
