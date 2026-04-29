"""Contact ↔ Leadgen-Place FK so the engagement brain has live access to
LLM insights, impressum and place data without copying them.

Adds ``contacts.leadgen_place_id`` (nullable) referencing
``leadgen_places(id)`` ON DELETE SET NULL. Backfills existing contacts
that came out of a leadgen handoff by reverse-mapping
``leadgen_places.contact_id`` (the existing forward link).

After this migration the brain can do::

    SELECT i.personalization_hook, i.business_summary, p.address_city, ...
    FROM contacts c
    LEFT JOIN leadgen_places p ON c.leadgen_place_id = p.id
    LEFT JOIN leadgen_llm_insights i ON i.place_id = p.id
    WHERE c.id = :contact_id;

Revision ID: 077
Revises: 076
Create Date: 2026-04-29
"""

import sqlalchemy as sa

from alembic import op

revision = "077"
down_revision = "076"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contacts",
        sa.Column(
            "leadgen_place_id",
            sa.Integer,
            sa.ForeignKey("leadgen_places.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_contacts_leadgen_place",
        "contacts",
        ["leadgen_place_id"],
        postgresql_where=sa.text("leadgen_place_id IS NOT NULL"),
    )

    # Backfill: every leadgen_place that already points to a contact
    # gets the reverse link populated. Keeps idempotency — re-running
    # the migration is a no-op because the WHERE filters already-set rows.
    op.execute(
        """
        UPDATE contacts c
        SET leadgen_place_id = p.id
        FROM leadgen_places p
        WHERE p.contact_id = c.id
          AND c.leadgen_place_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_contacts_leadgen_place", table_name="contacts")
    op.drop_column("contacts", "leadgen_place_id")
